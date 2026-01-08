import json, os, ast
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union
from sqlalchemy import create_engine, MetaData, Table, Column, String, Integer, select, text
from sqlalchemy.engine import Engine
from llama_index.core import SQLDatabase
from utils import read_json, write_json, save_raw_text, examples_to_str
from m_schema import MSchema
from config import MSchemaConfig


class SchemaEngine(SQLDatabase):
    def __init__(self, engine: Engine, schema: Optional[str] = None, metadata: Optional[MetaData] = None,
                 ignore_tables: Optional[List[str]] = None, include_tables: Optional[List[str]] = None,
                 sample_rows_in_table_info: int = 3, indexes_in_table_info: bool = False,
                 custom_table_info: Optional[dict] = None, 
                 view_support: bool = False, max_string_length: int = 300,                 
                 mschema: Optional[MSchema] = None, db_name: Optional[str] = '',
                 skip_examples: bool = False):
        super().__init__(engine, schema, metadata, ignore_tables, include_tables, sample_rows_in_table_info,
                         indexes_in_table_info, custom_table_info, view_support, max_string_length)
        
        self._db_name = db_name
        self._skip_examples = skip_examples  # Skip fetching example values for faster execution
        # Dictionary to store table names and their corresponding schema
        self._tables_schemas: Dict[str, str] = {}        # For MySQL and similar databases, if no schema is specified but db_name is provided,
        # use db_name as the schema to avoid getting tables from all databases
        if schema is None and db_name:
            if self._engine.dialect.name == 'mysql':
                schema = db_name
            elif self._engine.dialect.name == 'postgresql':
                # For PostgreSQL, use 'public' as default schema
                schema = 'public'
            elif self._engine.dialect.name == 'clickhouse':
                # For ClickHouse, use db_name as the database/schema to filter tables
                schema = db_name

        # If a schema is specified, filter by that schema and store that value for every table.
        if schema:
            self._usable_tables = [
                table_name for table_name in self._usable_tables
                if self._inspector.has_table(table_name, schema)
            ]
            for table_name in self._usable_tables:
                self._tables_schemas[table_name] = schema
        else:
            all_tables = []
            # Iterate through all available schemas, but filter by db_name for ClickHouse
            for s in self.get_schema_names():
                # For ClickHouse, only get tables from the specified database
                if self._engine.dialect.name == 'clickhouse' and db_name and s != db_name:
                    continue
                tables = self._inspector.get_table_names(schema=s)
                all_tables.extend(tables)
                for table in tables:
                    self._tables_schemas[table] = s
            self._usable_tables = all_tables

        self._dialect = engine.dialect.name
        if mschema is not None:
            self._mschema = mschema
        else:
            self._mschema = MSchema(db_id=db_name, schema=schema)
            self.init_mschema()

    @property
    def mschema(self) -> MSchema:
        """Return M-Schema"""
        return self._mschema

    def get_pk_constraint(self, table_name: str) -> List:
        """Get primary key columns for a table. Returns empty list if no primary keys exist."""
        try:
            pk_constraint = self._inspector.get_pk_constraint(table_name, self._tables_schemas[table_name])
            if pk_constraint and 'constrained_columns' in pk_constraint:
                return pk_constraint['constrained_columns']
            return []
        except (KeyError, TypeError, Exception):
            # ClickHouse and some databases may not support primary keys or return different structure
            return []

    def get_table_comment(self, table_name: str):
        try:
            return self._inspector.get_table_comment(table_name, self._tables_schemas[table_name])['text']
        except:    # sqlite does not support comments
            return ''

    def default_schema_name(self) -> Optional[str]:
        return self._inspector.default_schema_name

    def get_schema_names(self) -> List[str]:
        return self._inspector.get_schema_names()

    def get_foreign_keys(self, table_name: str):
        return self._inspector.get_foreign_keys(table_name, self._tables_schemas[table_name])

    def get_unique_constraints(self, table_name: str):
        return self._inspector.get_unique_constraints(table_name, self._tables_schemas[table_name])

    def fectch_distinct_values(self, table_name: str, column_name: str, max_num: int = 5):
        """Fetch distinct values for a column. Uses raw SQL to avoid SQLAlchemy type issues."""
        values = []
        try:
            schema_name = self._tables_schemas.get(table_name, '')
            # Use raw SQL query instead of SQLAlchemy Table reflection to avoid type issues
            # This works better with ClickHouse's custom types
            if schema_name and schema_name != self._db_name:
                full_table_name = f"{schema_name}.{table_name}"
            else:
                full_table_name = table_name
            
            # Escape column and table names for safety
            # Use SAMPLE coefficient from config for faster query execution on large tables
            sample_coeff = MSchemaConfig.SAMPLE_COEFFICIENT
            query = text(f"SELECT DISTINCT `{column_name}` FROM `{full_table_name}` SAMPLE {sample_coeff} LIMIT {max_num}")
            
            with self._engine.connect() as connection:
                result = connection.execute(query)
                distinct_values = result.fetchall()
                for value in distinct_values:
                    if value[0] is not None and value[0] != '':
                        values.append(value[0])
        except Exception as e:
            # If there's any error (type issues, permission, etc.), return empty list
            # This is expected for some ClickHouse types or large tables
            return []
        return values

    def get_table_row_count(self, table_name: str) -> int:
        """Get the number of rows in a table from system.tables."""
        try:
            schema_name = self._tables_schemas.get(table_name, '')
            db_name = schema_name if schema_name else self._db_name
            
            if not db_name:
                return 0
                
            query = text(f"SELECT rows FROM system.tables WHERE database = '{db_name}' AND name = '{table_name}'")
            
            with self._engine.connect() as connection:
                result = connection.execute(query)
                row = result.fetchone()
                if row and row[0] is not None:
                    return int(row[0])
        except Exception as e:
            # If we can't get row count, return 0 (will skip examples as a safety measure)
            pass
        return 0

    def fectch_distinct_values_batch(self, table_name: str, column_names: List[str], max_num: int = 5) -> Dict[str, List]:
        """Fetch distinct values for multiple columns at once using groupUniqArray. More efficient for ClickHouse."""
        results = {col: [] for col in column_names}
        
        if not column_names or (hasattr(self, '_skip_examples') and self._skip_examples):
            return results
        
        # Check table size - skip examples for huge tables (threshold from config)
        table_rows = self.get_table_row_count(table_name)
        if table_rows > MSchemaConfig.MAX_TABLE_ROWS_FOR_EXAMPLES:
            print(f"  Skipping examples for {table_name} (too large: {table_rows:,} rows)")
            return results
            
        try:
            schema_name = self._tables_schemas.get(table_name, '')
            if schema_name and schema_name != self._db_name:
                full_table_name = f"{schema_name}.{table_name}"
            else:
                full_table_name = table_name
            
            # Build groupUniqArray query for all columns at once
            # Format: SELECT groupUniqArray(5)(col1) AS col1_vals, groupUniqArray(5)(col2) AS col2_vals, ...
            select_parts = []
            for col in column_names:
                select_parts.append(f"groupUniqArray({max_num})(`{col}`) AS `{col}_vals`")
            
            # Try with SAMPLE first (faster for large tables)
            # If SAMPLE is not supported (e.g., views), fall back to query without SAMPLE
            sample_coeff = MSchemaConfig.SAMPLE_COEFFICIENT
            query_str_with_sample = f"SELECT {', '.join(select_parts)} FROM `{full_table_name}` SAMPLE {sample_coeff}"
            query_str_without_sample = f"SELECT {', '.join(select_parts)} FROM `{full_table_name}`"
            
            def extract_values_from_row(row):
                """Helper function to extract values from query result row."""
                
                if row:
                    for i, col in enumerate(column_names):
                        col_values = row[i]  # groupUniqArray returns an array
                        
                        # Handle case where ClickHouse returns array as actual list/tuple
                        if col_values and isinstance(col_values, (list, tuple)):
                            # Filter out None and empty strings, convert to strings
                            values = [str(v) for v in col_values if v is not None and str(v) != '']
                            results[col] = values[:max_num]  # Limit to max_num
                        # Handle case where ClickHouse driver returns array as string representation
                        elif col_values is not None and isinstance(col_values, str):
                            try:
                                # Try parsing as JSON array first (e.g., '["2023","2021"]')
                                if col_values.strip().startswith('['):
                                    # Try JSON parsing (uses double quotes)
                                    try:
                                        parsed = json.loads(col_values)
                                        if isinstance(parsed, list):
                                            values = [str(v) for v in parsed if v is not None and str(v) != '']
                                            results[col] = values[:max_num]
                                        else:
                                            results[col] = [str(parsed)][:max_num] if str(parsed) != '' else []
                                    except json.JSONDecodeError:
                                        # Try ast.literal_eval for Python list representation (e.g., "['2023','2021']")
                                        try:
                                            parsed = ast.literal_eval(col_values)
                                            if isinstance(parsed, (list, tuple)):
                                                values = [str(v) for v in parsed if v is not None and str(v) != '']
                                                results[col] = values[:max_num]
                                            else:
                                                results[col] = [str(parsed)][:max_num] if str(parsed) != '' else []
                                        except (ValueError, SyntaxError):
                                            # If parsing fails, treat as single string value
                                            if col_values.strip() != '':
                                                results[col] = [col_values.strip()][:max_num]
                                else:
                                    # Single string value
                                    if col_values.strip() != '':
                                        results[col] = [col_values.strip()][:max_num]
                            except Exception:
                                # Fallback: treat as single value
                                if str(col_values).strip() != '':
                                    results[col] = [str(col_values).strip()][:max_num]
                        # Handle other non-string, non-list types
                        elif col_values is not None:
                            try:
                                if str(col_values) != '':
                                    results[col] = [str(col_values)][:max_num]
                            except:
                                pass
            
            # Try with SAMPLE first
            try:
                with self._engine.connect() as connection:
                    result = connection.execute(text(query_str_with_sample))
                    row = result.fetchone()
                    extract_values_from_row(row)
            except Exception as sample_error:
                # If SAMPLE is not supported (e.g., for views or certain table engines), try without SAMPLE
                error_msg = str(sample_error)
                if 'SAMPLING_NOT_SUPPORTED' in error_msg or 'doesn\'t support sampling' in error_msg.lower() or 'SAMPLING' in error_msg:
                    print(f"    Table doesn't support SAMPLE, trying without SAMPLE...")
                    try:
                        with self._engine.connect() as connection:
                            result = connection.execute(text(query_str_without_sample))
                            row = result.fetchone()
                            extract_values_from_row(row)
                    except Exception as e2:
                        print(f"    Error fetching examples without SAMPLE: {e2}")
                        raise e2
                else:
                    # Re-raise if it's a different error
                    raise sample_error
        except Exception as e:
            # If there's any other error, return empty lists for all columns
            # This is expected for some ClickHouse types or large tables
            print(f"  Warning: Could not fetch examples for table {table_name}: {e}")
            pass
        return results

    def init_mschema(self):
        print(f"Debug: Database dialect = {self._engine.dialect.name}")
        print(f"Debug: DB name = {self._db_name}")
        print(f"Debug: Available schemas = {self.get_schema_names()}")
        print(f"Debug: Usable tables = {self._usable_tables}")
        print(f"Debug: Tables schemas mapping = {self._tables_schemas}")
        
        # Check if deals_history_duration is in the list (for debugging)
        if 'deals_history_duration' in self._usable_tables:
            print(f"Debug: 'deals_history_duration' found in usable_tables (schema: {self._tables_schemas.get('deals_history_duration', 'unknown')})")
        else:
            print(f"Debug: 'deals_history_duration' NOT in usable_tables")
        
        for table_name in self._usable_tables:
            table_comment = self.get_table_comment(table_name)
            table_comment = '' if table_comment is None else table_comment.strip()            # For MySQL, avoid duplicate schema name in table identifier
            # For PostgreSQL, include schema name if it's not 'public'
            schema_name = self._tables_schemas[table_name]
            if self._engine.dialect.name == 'mysql' and schema_name == self._db_name:
                table_with_schema = table_name
            elif self._engine.dialect.name == 'postgresql' and schema_name == 'public':
                table_with_schema = table_name
            else:
                table_with_schema = schema_name + '.' + table_name
            self._mschema.add_table(table_with_schema, fields={}, comment=table_comment)
            pks = self.get_pk_constraint(table_name)

            fks = self.get_foreign_keys(table_name)
            for fk in fks:
                referred_schema = fk['referred_schema']
                for c, r in zip(fk['constrained_columns'], fk['referred_columns']):
                    self._mschema.add_foreign_key(table_with_schema, c, referred_schema, fk['referred_table'], r)

            try:
                fields = self._inspector.get_columns(table_name, schema=self._tables_schemas[table_name])
            except Exception as e:
                print(f"Warning: Could not get columns for table {table_name}: {e}")
                continue  # Skip this table if we can't get its columns
            
            # Fetch distinct values for all columns at once using groupUniqArray (more efficient)
            # First check table size - skip examples for huge tables (> 10 million rows)
            column_names = [field['name'] for field in fields]
            examples_dict = {}
            if not (hasattr(self, '_skip_examples') and self._skip_examples):
                # Check table row count before fetching examples
                table_rows = self.get_table_row_count(table_name)
                if table_rows > MSchemaConfig.MAX_TABLE_ROWS_FOR_EXAMPLES:
                    print(f"  Skipping examples for table '{table_name}' (too large: {table_rows:,} rows > {MSchemaConfig.MAX_TABLE_ROWS_FOR_EXAMPLES:,} threshold)")
                    examples_dict = {}
                else:
                    try:
                        print(f"  Fetching examples for table '{table_name}' ({len(column_names)} columns)...")
                        examples_dict = self.fectch_distinct_values_batch(table_name, column_names, MSchemaConfig.MAX_EXAMPLES_PER_COLUMN)
                        # Count how many columns got examples
                        cols_with_examples = sum(1 for v in examples_dict.values() if len(v) > 0)
                        if cols_with_examples > 0:
                            print(f"    ✓ Got examples for {cols_with_examples}/{len(column_names)} columns")
                        else:
                            print(f"    ⚠ No examples retrieved for any columns")
                    except Exception as e:
                        # If batch fetch fails, fall back to empty examples
                        print(f"    ✗ Error fetching examples: {e}")
                        import traceback
                        traceback.print_exc()
                        examples_dict = {}
            
            for field in fields:
                try:
                    # Handle cases where field type might be None or unsupported
                    field_type = f"{field['type']!s}" if field.get('type') is not None else "UNKNOWN"
                    field_name = field['name']
                    primary_key = field_name in pks
                    field_comment = field.get("comment", None)
                    field_comment = "" if field_comment is None else field_comment.strip()
                    autoincrement = field.get('autoincrement', False)
                    default = field.get('default', None)
                    if default is not None:
                        default = f'{default}'

                    # Get examples from batch fetch (if available) or use empty list
                    if field_name in examples_dict:
                        examples = examples_dict[field_name]
                    else:
                        examples = []
                    examples = examples_to_str(examples)

                    self._mschema.add_field(
                        table_with_schema, field_name, field_type=field_type, primary_key=primary_key,
                        nullable=field.get('nullable', True), default=default, autoincrement=autoincrement,
                        comment=field_comment, examples=examples
                    )
                except Exception as e:
                    print(f"Warning: Error processing field '{field.get('name', 'unknown')}' in table {table_name}: {e}")
                    continue  # Skip this field if there's an error
