"""
Analysis Script for M-Schema Embedding Data

This script analyzes what data from the M-Schema gets embedded into vector
embeddings, what gets stored as metadata, and what data is completely excluded.
It helps understand the embedding strategy and data flow in the Schema Linking Agent.

The current implementation includes:
- Tables: table_name + table_description + foreign key relationships
- Columns: table_name + column_name + type + column_description + all examples
"""

import json
from typing import Dict, List, Optional


def get_related_tables_via_fk(table_name: str, mschema: Dict) -> List[str]:
    """
    Extract related tables via foreign key relationships.
    
    This function EXACTLY matches the logic in SchemaEmbedder.get_related_tables_via_fk().
    Analyzes the M-Schema foreign keys to find all tables that are related
    to the given table through foreign key relationships. This includes both
    tables that reference this table and tables that this table references.
    
    Note: The embedder uses dict format with .get() methods, so this function
    matches that exact behavior, even if the actual data might be in list format.
    
    Args:
        table_name: Name of the table to find related tables for.
        mschema: M-Schema dictionary containing foreign_keys list.
                Foreign keys are expected in dict format with keys like:
                source_table, target_table, table, from_table, referenced_table, to_table
    
    Returns:
        Sorted list of unique table names that are related via foreign keys.
        Returns empty list if no foreign keys exist or table has no relationships.
    
    Example:
        >>> schema = {"foreign_keys": [{"source_table": "table1", "target_table": "table2"}]}
        >>> related = get_related_tables_via_fk("table1", schema)
        >>> "table2" in related
        True
    """
    foreign_keys = mschema.get('foreign_keys', [])
    related_tables = set()
    
    for fk in foreign_keys:
        # Handle different FK formats - EXACTLY matching schema_embedder.py logic
        # Note: This uses .get() which works for dict format
        # If fk is a list, this will fail, but we match the embedder's behavior
        source_table = fk.get('source_table') or fk.get('table') or fk.get('from_table')
        target_table = fk.get('target_table') or fk.get('referenced_table') or fk.get('to_table')
        
        if source_table == table_name and target_table:
            related_tables.add(target_table)
        elif target_table == table_name and source_table:
            related_tables.add(source_table)
    
    return sorted(list(related_tables))


def extract_embeddable_text(
    table_name: str,
    table_data: Dict,
    column_data: Optional[Dict] = None,
    mschema: Optional[Dict] = None
) -> str:
    """
    Extract text representation for embedding from table or column data.
    
    Creates a text string that represents a table or column for embedding.
    This matches the logic in SchemaEmbedder.extract_embeddable_text().
    
    For tables: includes table name, description, and foreign key relationships.
    For columns: includes table name, column name, type, description, and all examples.
    
    Args:
        table_name: Full name of the table (e.g., "schema.table_name").
        table_data: Dictionary containing table information with keys:
                  - "table_description": str - Description of the table
                  - "fields": Dict - Dictionary of column definitions
        column_data: Optional dictionary containing column information with keys:
                    - "type": str - Column data type
                    - "column_description": str - Description of the column
                    - "examples": List - List of example values
                   If None, extracts table-level text. Default is None.
        mschema: Optional M-Schema dictionary for accessing foreign keys.
                Required for table-level FK information. Default is None.
    
    Returns:
        String representation suitable for embedding.
        Format for tables: "table_name: table_description. Related to: [table1, table2] via foreign keys"
        Format for columns: "table_name.column_name (type): column_description. Examples: [val1, val2, val3]"
    
    Example:
        >>> table_data = {"table_description": "Revenue data", "fields": {...}}
        >>> text = extract_embeddable_text("revenue", table_data, mschema=schema)
        >>> "revenue" in text.lower()
        True
    """
    if column_data is None:
        # Table-level text with foreign keys
        table_desc = table_data.get('table_description', '')
        base_text = f"{table_name}: {table_desc}"
        
        # Add foreign key information if available
        if mschema:
            related_tables = get_related_tables_via_fk(table_name, mschema)
            if related_tables:
                fk_text = f" Related to: {', '.join(related_tables)} via foreign keys"
                return f"{base_text}.{fk_text}"
        
        return base_text
    else:
        # Column-level text with examples
        column_name = list(column_data.keys())[0] if isinstance(column_data, dict) else None
        if column_name:
            col_info = column_data[column_name] if isinstance(column_data, dict) else column_data
            col_type = col_info.get('type', '')
            col_desc = col_info.get('column_description', '')
            base_text = f"{table_name}.{column_name} ({col_type}): {col_desc}"
            
            # Add examples if available
            examples = col_info.get('examples', [])
            if examples:
                # Include all examples (no restriction)
                examples_str = ', '.join(str(ex) for ex in examples)
                return f"{base_text}. Examples: [{examples_str}]"
            
            return base_text
        else:
            # Fallback
            col_type = column_data.get('type', '')
            col_desc = column_data.get('column_description', '')
            base_text = f"{table_name} ({col_type}): {col_desc}"
            
            # Add examples if available
            examples = column_data.get('examples', [])
            if examples:
                examples_str = ', '.join(str(ex) for ex in examples)
                return f"{base_text}. Examples: [{examples_str}]"
            
            return base_text


def analyze_embedding_data():
    """
    Analyze what data from M-Schema gets embedded and what's left out.
    
    This function performs a comprehensive analysis of the embedding strategy:
    1. Shows what M-Schema data gets embedded into vector embeddings
    2. Shows what data is stored as metadata (but not embedded)
    3. Shows what data is completely excluded
    4. Provides examples from the actual schema
    5. Displays the embedding structure
    
    The analysis helps understand:
    - What information is available for semantic search
    - What metadata is available for filtering/display
    - What data is lost in the embedding process
    
    Args:
        None (uses hardcoded schema path: "./cisco_stage_app_modified_m_schema.json")
    
    Returns:
        None (prints analysis to console)
    
    Raises:
        FileNotFoundError: If the schema file doesn't exist.
        json.JSONDecodeError: If the schema file is invalid JSON.
    
    Example:
        >>> analyze_embedding_data()
        ================================================================================
        M-Schema Embedding Data Analysis
        ================================================================================
        ...
    """
    print("=" * 80)
    print("M-Schema Embedding Data Analysis")
    print("=" * 80)
    
    # Load schema
    schema_path = "./cisco_stage_app_modified_m_schema.json"
    with open(schema_path, 'r', encoding='utf-8') as f:
        mschema = json.load(f)
    
    # Get first table as example
    tables = mschema.get('tables', {})
    if not tables:
        print("No tables found in schema")
        return
    
    first_table_name = list(tables.keys())[0]
    first_table_data = tables[first_table_name]
    
    print(f"\n📊 Example Table: {first_table_name}")
    print("-" * 80)
    
    # Show what's in M-Schema for table
    print("\n1️⃣  M-SCHEMA TABLE DATA (Full Structure):")
    print(f"   - table_description: {first_table_data.get('table_description', 'N/A')}")
    print(f"   - examples: {first_table_data.get('examples', [])}")
    print(f"   - fields: {len(first_table_data.get('fields', {}))} columns")
    
    # Show what gets embedded for table
    table_text = extract_embeddable_text(first_table_name, first_table_data, mschema=mschema)
    print(f"\n2️⃣  TABLE EMBEDDING TEXT (What gets embedded):")
    print(f"   '{table_text}'")
    
    # Check if foreign keys are included
    related_tables = get_related_tables_via_fk(first_table_name, mschema)
    if related_tables:
        print(f"\n   ✅ INCLUDED: table_name, table_description, foreign key relationships")
        print(f"      Foreign keys: {', '.join(related_tables)}")
    else:
        print(f"\n   ✅ INCLUDED: table_name, table_description")
        print(f"   ℹ️  No foreign key relationships for this table")
    print(f"   ❌ EXCLUDED: examples, fields (columns)")
    
    # Show first column
    fields = first_table_data.get('fields', {})
    if fields:
        first_column_name = list(fields.keys())[0]
        first_column_data = fields[first_column_name]
        
        print(f"\n\n📊 Example Column: {first_table_name}.{first_column_name}")
        print("-" * 80)
        
        # Show what's in M-Schema for column
        print("\n1️⃣  M-SCHEMA COLUMN DATA (Full Structure):")
        print(f"   - type: {first_column_data.get('type', 'N/A')}")
        print(f"   - primary_key: {first_column_data.get('primary_key', False)}")
        print(f"   - nullable: {first_column_data.get('nullable', False)}")
        print(f"   - default: {first_column_data.get('default', 'N/A')}")
        print(f"   - autoincrement: {first_column_data.get('autoincrement', False)}")
        print(f"   - examples: {first_column_data.get('examples', [])}")
        print(f"   - column_description: {first_column_data.get('column_description', 'N/A')}")
        
        # Show what gets embedded for column
        column_text = extract_embeddable_text(
            first_table_name,
            first_table_data,
            column_data={first_column_name: first_column_data},
            mschema=mschema
        )
        print(f"\n2️⃣  COLUMN EMBEDDING TEXT (What gets embedded):")
        print(f"   '{column_text}'")
        
        # Check if examples are included
        examples = first_column_data.get('examples', [])
        if examples:
            print(f"\n   ✅ INCLUDED: table_name, column_name, type, column_description, ALL examples")
            print(f"      Examples count: {len(examples)}")
            print(f"      Example values: {examples[:3]}{'...' if len(examples) > 3 else ''}")
        else:
            print(f"\n   ✅ INCLUDED: table_name, column_name, type, column_description")
            print(f"   ℹ️  No examples available for this column")
        
        print(f"\n3️⃣  COLUMN METADATA (Stored separately, NOT embedded):")
        print(f"   ✅ Stored in metadata: table_name, column_name, type, column_description, primary_key")
        print(f"   ❌ NOT stored anywhere: nullable, default, autoincrement")
        print(f"   ℹ️  Examples: Embedded in text (not separate metadata)")
    
    # Show embedding structure (without actually generating embeddings)
    print(f"\n\n" + "=" * 80)
    print("EMBEDDING STRUCTURE (Example)")
    print("=" * 80)
    
    # Count tables and columns
    total_tables = len(tables)
    total_columns = sum(len(t.get('fields', {})) for t in tables.values())
    
    print(f"\n📦 TABLE EMBEDDING STRUCTURE:")
    print(f"   - embedding: List[1024 floats] (vector from gte-large-en-v1.5)")
    print(f"   - element_type: 'table'")
    print(f"   - table_name: '{first_table_name}'")
    print(f"   - column_name: null")
    print(f"   - description: '{first_table_data.get('table_description', '')[:50]}...'")
    print(f"   - metadata: {{")
    print(f"       'table_name': '{first_table_name}',")
    print(f"       'table_description': '{first_table_data.get('table_description', '')[:50]}...'")
    print(f"     }}")
    
    if fields:
        first_col_name = list(fields.keys())[0]
        first_col_data = fields[first_col_name]
        print(f"\n📦 COLUMN EMBEDDING STRUCTURE:")
        print(f"   - embedding: List[1024 floats] (vector from gte-large-en-v1.5)")
        print(f"   - element_type: 'column'")
        print(f"   - table_name: '{first_table_name}'")
        print(f"   - column_name: '{first_col_name}'")
        print(f"   - description: '{first_col_data.get('column_description', '')[:50]}...'")
        print(f"   - metadata: {{")
        print(f"       'table_name': '{first_table_name}',")
        print(f"       'column_name': '{first_col_name}',")
        print(f"       'type': '{first_col_data.get('type', '')}',")
        print(f"       'column_description': '{first_col_data.get('column_description', '')[:50]}...',")
        print(f"       'primary_key': {first_col_data.get('primary_key', False)}")
        print(f"     }}")
    
    # Summary
    print(f"\n\n" + "=" * 80)
    print("SUMMARY: What Gets Embedded vs Left Out")
    print("=" * 80)
    
    print(f"\n✅ EMBEDDED (in embedding text - used for semantic search):")
    print(f"   Tables: table_name + table_description + foreign key relationships")
    print(f"   Columns: table_name + column_name + type + column_description + ALL examples")
    print(f"   Note: Foreign keys help find related tables, examples help match column values")
    
    print(f"\n✅ STORED IN METADATA (not embedded, but available for filtering/display):")
    print(f"   Tables: table_name, table_description")
    print(f"   Columns: table_name, column_name, type, column_description, primary_key")
    print(f"   Note: Metadata is used for filtering results and displaying information")
    
    print(f"\n❌ NOT STORED ANYWHERE (completely excluded from embeddings and metadata):")
    print(f"   Tables: examples (table-level examples)")
    print(f"   Columns: nullable, default, autoincrement")
    print(f"   Schema-level: db_id, schema name, foreign_keys structure (but FK relationships ARE embedded)")
    print(f"   Note: These fields are not used in semantic search or filtering")
    
    print(f"\n📊 STATISTICS:")
    print(f"   Total tables: {total_tables}")
    print(f"   Total columns: {total_columns}")
    print(f"   Total embeddings (if generated): {total_tables + total_columns}")
    print(f"   Table embeddings: {total_tables}")
    print(f"   Column embeddings: {total_columns}")

if __name__ == "__main__":
    analyze_embedding_data()

