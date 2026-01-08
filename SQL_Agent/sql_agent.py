"""
SQL Agent Module

Generates valid SQL queries from structured query plans using LLM-based generation.
Based on SQL-of-Thought framework, this agent converts executable query plans into
syntactically and logically correct SQL code for database execution.
"""

import os
import json
from typing import Dict, Optional, Tuple
from groq import Groq
from config import SQLAgentConfig
from sql_formatter import format_pretty, format_compact, format_none


class SQLAgent:
    """
    Agent that generates SQL queries from query plans.
    
    Uses Groq API (LLM-based) to convert structured query plans into executable
    SQL queries. Supports ClickHouse dialect, configurable formatting, optional
    validation, and fallback generation for error recovery.
    
    Attributes:
        client: Groq API client instance
        config: SQLAgentConfig instance with configuration settings
        model: Model name to use for SQL generation
        temperature: Temperature setting for generation
        max_tokens: Maximum tokens for response
    
    Example:
        >>> from config import SQLAgentConfig
        >>> config = SQLAgentConfig(temperature=0.1)
        >>> agent = SQLAgent(config)
        >>> plan = agent.load_query_plan("query_plan_query_1.json")
        >>> sql = agent.generate_sql(plan)
        >>> "SELECT" in sql
        True
    """
    
    def __init__(self, config: Optional[SQLAgentConfig] = None):
        """
        Initialize the SQL Agent.
        
        Sets up the Groq API client and validates configuration. Checks for
        required environment variables and initializes the agent with the
        provided or default configuration.
        
        Args:
            config: Optional SQLAgentConfig instance. If None, uses default
                   configuration. Default is None.
        
        Raises:
            ValueError: If GROQ_API_KEY is not set in environment.
        
        Example:
            >>> from config import SQLAgentConfig
            >>> config = SQLAgentConfig(temperature=0.2)
            >>> agent = SQLAgent(config)
            >>> agent.model
            'openai/gpt-oss-120b'
        """
        # Check for API key
        if "GROQ_API_KEY" not in os.environ:
            raise ValueError(
                "GROQ_API_KEY environment variable is not set. "
                "Please set it using: export GROQ_API_KEY='your-api-key'"
            )
        
        self.client = Groq()
        self.config = config or SQLAgentConfig()
        self.model = self.config.model
        self.temperature = self.config.temperature
        self.max_tokens = self.config.max_tokens
        self._schema_cache = {}  # Cache for loaded schemas
    
    def load_query_plan(self, plan_path: str) -> Dict:
        """
        Load query plan from a JSON file.
        
        Reads and parses a query plan JSON file created by the Query Plan Agent.
        Validates the structure to ensure it contains required fields (execution_steps,
        select_columns, from_table, joins). Returns the complete dictionary.
        
        Args:
            plan_path: Path to the query plan JSON file. Can be relative or absolute.
                      If relative, will be resolved relative to the query_plans_dir
                      from config.
        
        Returns:
            Dictionary containing the query plan with structure:
            {
                "query": str - The original user query
                "execution_steps": List[Dict] - Ordered execution steps
                "select_columns": List[Dict] - Columns to select
                "from_table": str - Base table name
                "joins": List[Dict] - Join operations
                "where_conditions": Dict or None - Filter conditions
                "group_by": List[str] or None - Grouping columns
                "having_conditions": Dict or None - Aggregate filters
                "order_by": List[Dict] or None - Sorting requirements
                "subqueries": List[Dict] - Nested queries
                "complexity_indicators": Dict - Complexity metadata
            }
        
        Raises:
            FileNotFoundError: If the query plan file does not exist.
            ValueError: If the file is not valid JSON or missing required fields.
            json.JSONDecodeError: If JSON parsing fails.
        
        Example:
            >>> agent = SQLAgent()
            >>> plan = agent.load_query_plan("query_plan_query_1.json")
            >>> "execution_steps" in plan
            True
            >>> "select_columns" in plan
            True
        """
        # Resolve path
        if not os.path.isabs(plan_path):
            full_path = os.path.join(self.config.query_plans_dir, plan_path)
        else:
            full_path = plan_path
        
        # Check if file exists
        if not os.path.exists(full_path):
            raise FileNotFoundError(
                f"Query plan file not found: {full_path}\n"
                f"Make sure the Query Plan Agent has generated results first."
            )
        
        # Load and parse JSON
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Invalid JSON in query plan file: {full_path}\n"
                f"Error: {str(e)}"
            )
        
        # Validate structure
        required_fields = ["execution_steps", "select_columns", "from_table", "joins"]
        for field in required_fields:
            if field not in data:
                raise ValueError(
                    f"Query plan file missing required field '{field}': {full_path}"
                )
        
        return data
    
    def load_filtered_schema(self, query_index: int) -> Optional[Dict]:
        """
        Load filtered schema for a specific query.
        
        Attempts to load the filtered schema from Schema Linking Agent results
        that corresponds to the query index. Falls back to full schema if filtered
        schema is not found.
        
        Args:
            query_index: Index of the query (1-based) to load schema for.
        
        Returns:
            Dictionary containing the filtered or full schema, or None if not found.
        
        Example:
            >>> schema = agent.load_filtered_schema(1)
            >>> "tables" in schema
            True
        """
        # Check cache first
        if query_index in self._schema_cache:
            return self._schema_cache[query_index]
        
        # Try to load filtered schema first
        filtered_schema_path = os.path.join(
            self.config.filtered_schema_dir,
            f"filtered_schema_query_{query_index}.json"
        )
        
        if os.path.exists(filtered_schema_path):
            try:
                with open(filtered_schema_path, 'r', encoding='utf-8') as f:
                    schema = json.load(f)
                    self._schema_cache[query_index] = schema
                    return schema
            except (json.JSONDecodeError, IOError):
                pass
        
        # Fallback to full schema
        if self.config.full_schema_path and os.path.exists(self.config.full_schema_path):
            try:
                with open(self.config.full_schema_path, 'r', encoding='utf-8') as f:
                    schema = json.load(f)
                    self._schema_cache[query_index] = schema
                    return schema
            except (json.JSONDecodeError, IOError):
                pass
        
        return None
    
    def _format_schema_for_prompt(self, schema: Dict) -> str:
        """
        Format schema for inclusion in LLM prompt.
        
        Extracts and formats table and column information from the schema
        in a concise format suitable for LLM prompts.
        
        Args:
            schema: Dictionary containing the M-Schema structure.
        
        Returns:
            String containing formatted schema information.
        
        Example:
            >>> schema = {"tables": {...}, ...}
            >>> formatted = agent._format_schema_for_prompt(schema)
            >>> "metrics" in formatted
            True
        """
        if not schema:
            return ""
        
        lines = ["Database Schema (use these EXACT column names):"]
        lines.append("=" * 80)
        
        tables = schema.get("tables", {})
        for table_name, table_info in tables.items():
            lines.append(f"\nTable: {table_name}")
            if table_info.get("table_description"):
                lines.append(f"  Description: {table_info['table_description']}")
            
            fields = table_info.get("fields", {})
            if fields:
                lines.append("  Columns:")
                for col_name, col_info in fields.items():
                    col_type = col_info.get("type", "")
                    col_desc = col_info.get("column_description", "")
                    lines.append(f"    - {col_name} ({col_type})")
                    if col_desc:
                        lines.append(f"      {col_desc}")
        
        return "\n".join(lines)
    
    def _build_sql_prompt(
        self,
        query_plan: Dict,
        user_query: Optional[str] = None,
        schema: Optional[Dict] = None
    ) -> Tuple[str, str]:
        """
        Build prompt for LLM-based SQL generation.
        
        Creates a comprehensive prompt that guides the LLM to generate valid SQL
        from the query plan. The prompt includes the full query plan structure,
        user query context, ClickHouse dialect requirements, and output format
        specifications.
        
        Args:
            query_plan: Dictionary containing the query plan with execution steps,
                      select columns, joins, and other SQL components.
            user_query: Optional original user query for context. If None, uses
                       query from query_plan if available. Default is None.
        
        Returns:
            Tuple of (system_prompt, user_prompt) strings:
            - system_prompt: System message defining the agent's role and task
            - user_prompt: User message with query plan and instructions
        
        Example:
            >>> plan = {"execution_steps": [...], "select_columns": [...], ...}
            >>> sys_prompt, user_prompt = agent._build_sql_prompt(plan)
            >>> "ClickHouse" in sys_prompt
            True
        """
        system_prompt = """You are a SQL expert specializing in ClickHouse database queries.

Your task is to generate valid, executable SQL queries from structured query plans.
The query plan provides a detailed breakdown of the SQL structure including:
- Execution steps (table identification, joins, aggregations)
- SELECT columns with table mappings
- JOIN operations with conditions
- WHERE, GROUP BY, HAVING, ORDER BY clauses
- Subqueries if present

CRITICAL: You will be provided with the actual database schema. You MUST use the EXACT column names from the schema.
If the query plan mentions a column name that doesn't exist in the schema, you must find the correct column name
by matching the semantic meaning (e.g., "revenue_amount" might map to "won_amount" or "qtd" based on context).

Requirements:
1. Generate ONLY the SQL query - no markdown code blocks, no explanations, no comments
2. Use proper ClickHouse SQL syntax
3. Follow the query plan structure exactly
4. Use EXACT column names from the provided schema - do NOT use column names from the query plan if they don't match the schema
5. Map query plan column references to actual schema column names based on semantic meaning
6. Handle all clauses: SELECT, FROM, JOIN, WHERE, GROUP BY, HAVING, ORDER BY
7. Support advanced subqueries: CTEs (WITH clauses), nested subqueries, correlated subqueries
8. Handle both string and structured formats for WHERE/HAVING/ORDER BY conditions
9. Use proper table and column references with schema prefixes if needed
10. Ensure SQL is syntactically correct and ready for execution

Output format: Plain SQL string only, no markdown, no code blocks."""
        
        # Get user query
        if not user_query:
            user_query = query_plan.get("query", "")
        
        # Format query plan for prompt
        plan_json = json.dumps(query_plan, indent=2)
        
        # Format schema for prompt
        schema_text = ""
        if schema:
            schema_text = self._format_schema_for_prompt(schema)
        
        user_prompt = f"""User Query: {user_query}

{schema_text}

Query Plan:
{plan_json}

Generate a valid ClickHouse SQL query that follows this query plan exactly.

CRITICAL INSTRUCTIONS:
- Use ONLY the column names from the Database Schema above
- If the query plan references a column that doesn't exist in the schema, find the semantically equivalent column
- For example: if query plan says "revenue_amount" but schema has "won_amount", use "won_amount"
- If query plan says "conversion_rate" but schema has "cc_percent", use "cc_percent"
- Match column names based on their descriptions and semantic meaning

Important:
- Output ONLY the SQL query, nothing else
- No markdown code blocks (no ```sql or ```)
- No explanations or comments
- Use ClickHouse-specific syntax
- Handle all execution steps in order
- Include all SELECT columns with proper aliases
- Add all JOINs with correct conditions
- Apply WHERE, GROUP BY, HAVING, ORDER BY as specified
- Support subqueries if present in the plan

SQL Query:"""
        
        return system_prompt, user_prompt
    
    def _generate_fallback_sql(self, query_plan: Dict) -> str:
        """
        Generate simpler SQL when primary LLM generation fails.
        
        Creates a basic, rule-based SQL query from the query plan when the
        primary LLM-based generation fails. Extracts essential elements and
        constructs minimal valid SQL with basic structure only.
        
        Args:
            query_plan: Dictionary containing the query plan with execution steps,
                      select columns, joins, and other SQL components.
        
        Returns:
            String containing a basic SQL query that follows the minimal structure
            from the query plan. May not include all advanced features.
        
        Example:
            >>> plan = {
            ...     "select_columns": [{"column": "SUM(revenue)", "alias": "total"}],
            ...     "from_table": "metrics",
            ...     "group_by": ["region"]
            ... }
            >>> sql = agent._generate_fallback_sql(plan)
            >>> "SELECT" in sql
            True
        """
        # Extract SELECT columns
        select_parts = []
        for col in query_plan.get("select_columns", []):
            col_expr = col.get("column", "")
            alias = col.get("alias")
            if alias:
                select_parts.append(f"{col_expr} AS {alias}")
            else:
                select_parts.append(col_expr)
        
        if not select_parts:
            select_parts = ["*"]
        
        select_clause = ", ".join(select_parts)
        
        # Extract FROM table
        from_table = query_plan.get("from_table", "")
        if not from_table:
            raise ValueError("Query plan missing 'from_table' field")
        
        # Build FROM clause
        from_clause = f"FROM {from_table}"
        
        # Extract JOINs
        join_clauses = []
        for join in query_plan.get("joins", []):
            join_type = join.get("type", "INNER JOIN")
            join_table = join.get("table", "")
            condition = join.get("condition", {})
            
            if join_table and condition:
                left = condition.get("left", "")
                operator = condition.get("operator", "=")
                right = condition.get("right", "")
                
                if left and right:
                    join_clauses.append(
                        f"{join_type} {join_table} ON {left} {operator} {right}"
                    )
        
        # Build WHERE clause
        where_clause = ""
        where_conditions = query_plan.get("where_conditions")
        if where_conditions:
            if isinstance(where_conditions, str):
                where_clause = f"WHERE {where_conditions}"
            elif isinstance(where_conditions, dict):
                # Handle structured format
                conditions = where_conditions.get("conditions", [])
                if conditions:
                    where_parts = []
                    for cond in conditions:
                        if isinstance(cond, dict):
                            left = cond.get("left", "")
                            operator = cond.get("operator", "=")
                            right = cond.get("right", "")
                            if left and right:
                                where_parts.append(f"{left} {operator} {right}")
                        elif isinstance(cond, str):
                            where_parts.append(cond)
                    if where_parts:
                        where_clause = f"WHERE {' AND '.join(where_parts)}"
        
        # Build GROUP BY clause
        group_by_clause = ""
        group_by = query_plan.get("group_by")
        if group_by:
            if isinstance(group_by, list):
                group_by_clause = f"GROUP BY {', '.join(group_by)}"
            elif isinstance(group_by, str):
                group_by_clause = f"GROUP BY {group_by}"
        
        # Build HAVING clause
        having_clause = ""
        having_conditions = query_plan.get("having_conditions")
        if having_conditions:
            if isinstance(having_conditions, str):
                having_clause = f"HAVING {having_conditions}"
            elif isinstance(having_conditions, dict):
                # Handle structured format
                conditions = having_conditions.get("conditions", [])
                if conditions:
                    having_parts = []
                    for cond in conditions:
                        if isinstance(cond, dict):
                            left = cond.get("left", "")
                            operator = cond.get("operator", "=")
                            right = cond.get("right", "")
                            if left and right:
                                having_parts.append(f"{left} {operator} {right}")
                        elif isinstance(cond, str):
                            having_parts.append(cond)
                    if having_parts:
                        having_clause = f"HAVING {' AND '.join(having_parts)}"
        
        # Build ORDER BY clause
        order_by_clause = ""
        order_by = query_plan.get("order_by")
        if order_by:
            if isinstance(order_by, list):
                order_parts = []
                for item in order_by:
                    if isinstance(item, dict):
                        column = item.get("column", "")
                        direction = item.get("direction", "ASC")
                        order_parts.append(f"{column} {direction}")
                    elif isinstance(item, str):
                        order_parts.append(item)
                if order_parts:
                    order_by_clause = f"ORDER BY {', '.join(order_parts)}"
            elif isinstance(order_by, str):
                order_by_clause = f"ORDER BY {order_by}"
        
        # Construct SQL
        sql_parts = [
            f"SELECT {select_clause}",
            from_clause
        ]
        
        sql_parts.extend(join_clauses)
        
        if where_clause:
            sql_parts.append(where_clause)
        
        if group_by_clause:
            sql_parts.append(group_by_clause)
        
        if having_clause:
            sql_parts.append(having_clause)
        
        if order_by_clause:
            sql_parts.append(order_by_clause)
        
        return " ".join(sql_parts)
    
    def format_sql(self, sql: str, format_type: Optional[str] = None) -> str:
        """
        Format SQL based on configuration.
        
        Applies formatting to the SQL string based on the specified format type.
        Supports pretty-printing (indented, multi-line), compact (single line),
        or no formatting (pass-through).
        
        Args:
            sql: Raw SQL string to format.
            format_type: Format type to apply. Options:
                        - "pretty": Indented, multi-line format
                        - "compact": Single line, minimal whitespace
                        - "none": No formatting changes
                        If None, uses format from config. Default is None.
        
        Returns:
            Formatted SQL string according to the specified format type.
        
        Example:
            >>> sql = "SELECT * FROM table WHERE id=1"
            >>> formatted = agent.format_sql(sql, "pretty")
            >>> "SELECT" in formatted
            True
        """
        if format_type is None:
            format_type = self.config.sql_format
        
        if format_type == "pretty":
            return format_pretty(sql)
        elif format_type == "compact":
            return format_compact(sql)
        else:  # "none"
            return format_none(sql)
    
    def validate_sql(
        self,
        sql: str,
        dialect: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate SQL syntax (optional).
        
        Performs optional SQL syntax validation using a SQL parser. Returns
        validation result and error message if validation fails. This is
        configurable and disabled by default.
        
        Args:
            sql: SQL string to validate.
            dialect: Database dialect for validation. If None, uses dialect
                    from config. Default is None.
        
        Returns:
            Tuple of (is_valid, error_message):
            - is_valid: bool - True if SQL is valid, False otherwise
            - error_message: Optional[str] - Error message if validation fails,
                             None if valid
        
        Example:
            >>> sql = "SELECT * FROM table"
            >>> is_valid, error = agent.validate_sql(sql)
            >>> isinstance(is_valid, bool)
            True
        """
        if not self.config.enable_validation:
            return True, None
        
        if dialect is None:
            dialect = self.config.database_dialect
        
        try:
            from sql_validator import validate_sql_syntax
            return validate_sql_syntax(sql, dialect)
        except ImportError:
            # If validator module not available, skip validation
            return True, None
        except Exception as e:
            return False, str(e)
    
    def execute_sql(
        self,
        sql: str,
        connection_string: Optional[str] = None
    ) -> Dict:
        """
        Execute SQL against database (optional).
        
        Optionally executes the generated SQL against the target database to
        test if it runs successfully. Returns execution results or error information.
        This is configurable and disabled by default.
        
        Args:
            sql: SQL string to execute.
            connection_string: Database connection string. If None, uses connection
                             string from config. Default is None.
        
        Returns:
            Dictionary containing execution results:
            {
                "success": bool - Whether execution succeeded
                "error": Optional[str] - Error message if execution failed
                "row_count": Optional[int] - Number of rows returned
                "execution_time": Optional[float] - Execution time in seconds
            }
        
        Example:
            >>> sql = "SELECT 1"
            >>> result = agent.execute_sql(sql)
            >>> "success" in result
            True
        """
        if not self.config.enable_execution:
            return {
                "success": None,
                "error": "Execution disabled in config",
                "row_count": None,
                "execution_time": None
            }
        
        if connection_string is None:
            connection_string = self.config.db_connection_string
        
        if not connection_string:
            return {
                "success": False,
                "error": "No database connection string provided",
                "row_count": None,
                "execution_time": None
            }
        
        try:
            # #region agent log
            import json, os
            with open('/Users/srivalli/Desktop/workspace/SQL-Generator-Agentic/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"post-fix","hypothesisId":"A","location":"sql_agent.py:525","message":"Attempting db_executor import","data":{"enable_execution":self.config.enable_execution,"has_connection_string":bool(connection_string)},"timestamp":int(__import__('time').time()*1000)}) + '\n')
            # #endregion
            from db_executor import execute_query
            # #region agent log
            with open('/Users/srivalli/Desktop/workspace/SQL-Generator-Agentic/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"post-fix","hypothesisId":"A","location":"sql_agent.py:526","message":"db_executor import successful","data":{},"timestamp":int(__import__('time').time()*1000)}) + '\n')
            # #endregion
            return execute_query(
                sql,
                connection_string,
                self.config.database_dialect
            )
        except ImportError as import_err:
            # #region agent log
            import json, os, sys, traceback
            with open('/Users/srivalli/Desktop/workspace/SQL-Generator-Agentic/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"post-fix","hypothesisId":"B","location":"sql_agent.py:531","message":"ImportError caught","data":{"error_msg":str(import_err),"error_type":type(import_err).__name__},"timestamp":int(__import__('time').time()*1000)}) + '\n')
            # #endregion
            # Check if it's a missing dependency issue
            error_msg = str(import_err)
            if "sqlalchemy" in error_msg.lower():
                helpful_msg = (
                    f"SQLAlchemy not installed. "
                    f"Please install: pip install sqlalchemy\n"
                    f"Original error: {error_msg}"
                )
            elif "clickhouse" in error_msg.lower() and ("plugin" in error_msg.lower() or "dialect" in error_msg.lower()):
                helpful_msg = (
                    f"ClickHouse SQLAlchemy dialect not found. "
                    f"Please install: pip install clickhouse-sqlalchemy\n"
                    f"Original error: {error_msg}"
                )
            else:
                helpful_msg = (
                    f"Database executor dependencies not installed. "
                    f"Please install requirements: pip install -r requirements.txt\n"
                    f"Original error: {error_msg}"
                )
            
            return {
                "success": False,
                "error": helpful_msg,
                "row_count": None,
                "execution_time": None
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "row_count": None,
                "execution_time": None
            }
    
    def generate_sql(
        self,
        query_plan: Dict,
        user_query: Optional[str] = None,
        query_index: Optional[int] = None
    ) -> str:
        """
        Generate SQL query from query plan.
        
        Main method that takes a query plan and generates a valid SQL query
        using LLM-based generation. Falls back to simpler SQL if primary
        generation fails. Applies formatting based on configuration.
        
        Args:
            query_plan: Dictionary containing the query plan with execution steps,
                      select columns, joins, and other SQL components.
            user_query: Optional original user query for context. If None, uses
                       query from query_plan if available. Default is None.
            query_index: Optional query index (1-based) to load corresponding
                        filtered schema. If None, attempts to extract from query_plan
                        or uses full schema. Default is None.
        
        Returns:
            String containing the generated SQL query, formatted according to
            configuration (pretty, compact, or none).
        
        Raises:
            ValueError: If query plan is invalid.
            Exception: If SQL generation fails and fallback is disabled or fails.
        
        Example:
            >>> agent = SQLAgent()
            >>> plan = {
            ...     "select_columns": [{"column": "SUM(revenue)", "alias": "total"}],
            ...     "from_table": "metrics",
            ...     "joins": [],
            ...     "execution_steps": []
            ... }
            >>> sql = agent.generate_sql(plan, query_index=1)
            >>> "SELECT" in sql
            True
        """
        # Validate query plan
        required_fields = ["execution_steps", "select_columns", "from_table", "joins"]
        for field in required_fields:
            if field not in query_plan:
                raise ValueError(f"Query plan missing required field: {field}")
        
        # Get user query
        if not user_query:
            user_query = query_plan.get("query", "")
        
        # Load schema if query_index is provided
        schema = None
        if query_index is not None:
            schema = self.load_filtered_schema(query_index)
        
        # Build prompt with schema
        system_prompt, user_prompt = self._build_sql_prompt(query_plan, user_query, schema)
        
        # Call Groq API
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith("```sql"):
                response_text = response_text[6:]
            elif response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            # Format SQL
            sql = self.format_sql(response_text)
            
            return sql
        
        except Exception as e:
            # Attempt fallback if enabled
            if self.config.enable_fallback:
                try:
                    fallback_sql = self._generate_fallback_sql(query_plan)
                    formatted_sql = self.format_sql(fallback_sql)
                    print(f"⚠ Warning: Primary SQL generation failed, using fallback: {str(e)}")
                    return formatted_sql
                except Exception as fallback_error:
                    raise Exception(
                        f"SQL generation failed and fallback also failed.\n"
                        f"Primary error: {str(e)}\n"
                        f"Fallback error: {str(fallback_error)}"
                    ) from e
            else:
                raise Exception(
                    f"Failed to generate SQL: {str(e)}\n"
                    f"Query: {user_query[:100] if user_query else 'N/A'}"
                ) from e

