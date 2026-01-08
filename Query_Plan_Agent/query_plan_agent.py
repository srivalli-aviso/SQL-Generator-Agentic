"""
Query Plan Agent Module

Generates executable query plans from clause-wise subproblems using Chain of Thought
reasoning. Based on SQL-of-Thought framework, this agent creates structured, step-by-step
execution plans that guide SQL generation.
"""

import os
import json
from typing import Dict, List, Optional, Tuple
from groq import Groq
from config import QueryPlanConfig


class QueryPlanAgent:
    """
    Agent that generates executable query plans from subproblems.
    
    Uses Chain of Thought (CoT) reasoning internally to analyze subproblems and
    create structured query plans with join order, column mappings, and aggregation
    logic. The CoT reasoning is internal and not included in the output.
    
    Attributes:
        client: Groq API client instance
        config: QueryPlanConfig instance with configuration settings
        model: Model name to use for plan generation
        temperature: Temperature setting for generation
        max_tokens: Maximum tokens for response
    
    Example:
        >>> from config import QueryPlanConfig
        >>> config = QueryPlanConfig(temperature=0.1)
        >>> agent = QueryPlanAgent(config)
        >>> subproblems = agent.load_subproblems("subproblems_query_1.json")
        >>> plan = agent.generate_query_plan(
        ...     user_query=subproblems["query"],
        ...     subproblems=subproblems["subproblems"]
        ... )
        >>> "execution_steps" in plan
        True
    """
    
    def __init__(self, config: Optional[QueryPlanConfig] = None):
        """
        Initialize the Query Plan Agent.
        
        Sets up the Groq API client and validates configuration. Checks for
        required environment variables and initializes the agent with the
        provided or default configuration.
        
        Args:
            config: Optional QueryPlanConfig instance. If None, uses default
                   configuration. Default is None.
        
        Raises:
            ValueError: If GROQ_API_KEY is not set in environment.
        
        Example:
            >>> from config import QueryPlanConfig
            >>> config = QueryPlanConfig(temperature=0.2)
            >>> agent = QueryPlanAgent(config)
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
        self.config = config or QueryPlanConfig()
        self.model = self.config.model
        self.temperature = self.config.temperature
        self.max_tokens = self.config.max_tokens
    
    def load_subproblems(self, subproblems_path: str) -> Dict:
        """
        Load subproblems from a JSON file.
        
        Reads and parses a subproblems JSON file created by the Subproblem Agent.
        Validates the structure to ensure it contains required fields (query and
        subproblems). Returns the complete dictionary including query and subproblems.
        
        Args:
            subproblems_path: Path to the subproblems JSON file. Can be relative
                            or absolute. If relative, will be resolved relative to
                            the subproblems_dir from config.
        
        Returns:
            Dictionary containing:
            {
                "query": str - The original user query
                "subproblems": Dict - Subproblems dictionary with clause-wise breakdown
                "filtered_schema_stats": Dict - Optional statistics (if present)
            }
        
        Raises:
            FileNotFoundError: If the subproblems file does not exist.
            ValueError: If the file is not valid JSON or missing required fields.
            json.JSONDecodeError: If JSON parsing fails.
        
        Example:
            >>> agent = QueryPlanAgent()
            >>> subproblems = agent.load_subproblems("subproblems_query_1.json")
            >>> "query" in subproblems
            True
            >>> "subproblems" in subproblems
            True
        """
        # Resolve path
        if not os.path.isabs(subproblems_path):
            full_path = os.path.join(self.config.subproblems_dir, subproblems_path)
        else:
            full_path = subproblems_path
        
        # Check if file exists
        if not os.path.exists(full_path):
            raise FileNotFoundError(
                f"Subproblems file not found: {full_path}\n"
                f"Make sure the Subproblem Agent has generated results first."
            )
        
        # Load and parse JSON
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Invalid JSON in subproblems file: {full_path}\n"
                f"Error: {str(e)}"
            )
        
        # Validate structure
        if "query" not in data:
            raise ValueError(
                f"Subproblems file missing 'query' field: {full_path}"
            )
        
        if "subproblems" not in data:
            raise ValueError(
                f"Subproblems file missing 'subproblems' field: {full_path}"
            )
        
        # Validate subproblems structure
        subproblems = data["subproblems"]
        required_keys = ["SELECT", "FROM"]
        for key in required_keys:
            if key not in subproblems:
                raise ValueError(
                    f"Subproblems missing required key '{key}' in: {full_path}"
                )
        
        return data
    
    def _format_schema_for_prompt(self, schema: Dict) -> str:
        """
        Format schema dictionary into a readable string for the prompt.
        
        Converts the schema dictionary (full or filtered) into a structured
        text representation that can be included in the LLM prompt. Includes
        table names, column names, types, and descriptions.
        
        Args:
            schema: Schema dictionary with structure:
                   {
                       "tables": Dict - Dictionary of tables
                       "db_id": str - Database identifier (optional)
                       "schema": str - Schema name (optional)
                   }
        
        Returns:
            Formatted string representation of the schema with tables,
            columns, types, and descriptions.
        
        Example:
            >>> schema = {"tables": {"table1": {"fields": {...}}}}
            >>> formatted = agent._format_schema_for_prompt(schema)
            >>> "table1" in formatted
            True
        """
        schema_text = []
        tables = schema.get('tables', {})
        
        for table_name, table_data in tables.items():
            schema_text.append(f"\nTable: {table_name}")
            if table_data.get('table_description'):
                schema_text.append(f"  Description: {table_data['table_description']}")
            
            fields = table_data.get('fields', {})
            if fields:
                schema_text.append("  Columns:")
                for col_name, col_info in fields.items():
                    col_type = col_info.get('type', 'Unknown')
                    col_desc = col_info.get('column_description', '')
                    schema_text.append(f"    - {col_name} ({col_type}): {col_desc}")
        
        return "\n".join(schema_text)
    
    def _build_cot_prompt(
        self,
        user_query: str,
        subproblems: Dict,
        schema: Optional[Dict] = None
    ) -> Tuple[str, str]:
        """
        Build Chain of Thought prompt for query plan generation.
        
        Creates a comprehensive prompt that guides the LLM through step-by-step
        reasoning to generate a query plan. The prompt includes:
        1. Analysis of each subproblem component
        2. Planning table relationships and joins
        3. Mapping columns to tables
        4. Planning aggregations and grouping
        5. Structuring execution steps
        
        The CoT reasoning is internal - the prompt guides reasoning but the
        output should be a structured query plan without reasoning explanations.
        
        Args:
            user_query: The original natural language query from the user.
            subproblems: Dictionary containing clause-wise subproblems with keys:
                        - SELECT: str or None
                        - FROM: str or None
                        - WHERE: str or None
                        - GROUP BY: str or None
                        - HAVING: str or None
                        - ORDER BY: str or None
                        - complexity: str
                        - requires_join: bool
                        - requires_aggregation: bool
            schema: Optional schema dictionary. If provided, includes schema
                   information in the prompt for better column/table mapping.
                   Default is None.
        
        Returns:
            Tuple of (system_prompt, user_prompt) strings:
            - system_prompt: System message defining the agent's role and task
            - user_prompt: User message with query, subproblems, and instructions
        
        Example:
            >>> subproblems = {"SELECT": "...", "FROM": "...", ...}
            >>> sys_prompt, user_prompt = agent._build_cot_prompt(
            ...     "Show revenue by region",
            ...     subproblems
            ... )
            >>> "query plan" in sys_prompt.lower()
            True
        """
        system_prompt = """You are a Query Plan Agent that generates executable query plans from SQL clause subproblems.

Your task is to analyze subproblems and create a structured, step-by-step execution plan that includes:
1. Execution steps (ordered operations)
2. Join order and conditions (table relationships)
3. Column-to-table mappings (which columns come from which tables)
4. Aggregation and grouping logic (functions, GROUP BY columns)

Use Chain of Thought reasoning internally to:
- Analyze each subproblem component
- Determine logical sequence of operations
- Identify table relationships and join conditions
- Plan aggregation strategies
- Structure the execution flow

IMPORTANT: Your output should be ONLY the structured query plan in JSON format. Do NOT include reasoning explanations or natural language descriptions in the output. The CoT reasoning should be internal only.

Output a valid JSON object with the query plan structure."""
        
        # Format subproblems for prompt
        subproblems_text = []
        subproblems_text.append("Subproblems:")
        subproblems_text.append(f"  SELECT: {subproblems.get('SELECT', 'None')}")
        subproblems_text.append(f"  FROM: {subproblems.get('FROM', 'None')}")
        subproblems_text.append(f"  WHERE: {subproblems.get('WHERE', 'None')}")
        subproblems_text.append(f"  GROUP BY: {subproblems.get('GROUP BY', 'None')}")
        subproblems_text.append(f"  HAVING: {subproblems.get('HAVING', 'None')}")
        subproblems_text.append(f"  ORDER BY: {subproblems.get('ORDER BY', 'None')}")
        subproblems_text.append(f"  Complexity: {subproblems.get('complexity', 'moderate')}")
        subproblems_text.append(f"  Requires Join: {subproblems.get('requires_join', False)}")
        subproblems_text.append(f"  Requires Aggregation: {subproblems.get('requires_aggregation', False)}")
        
        # Include schema if provided
        schema_text = ""
        if schema:
            schema_text = f"\n\nAvailable Schema:\n{self._format_schema_for_prompt(schema)}"
        
        user_prompt = f"""User Query: {user_query}

{chr(10).join(subproblems_text)}{schema_text}

Generate a query plan with the following structure:

{{
  "execution_steps": [
    {{
      "step_number": 1,
      "operation": "identify_base_table",
      "table": "table_name",
      "columns": ["col1", "col2"]
    }},
    {{
      "step_number": 2,
      "operation": "join_table",
      "join_type": "LEFT JOIN",
      "table": "other_table",
      "join_condition": {{
        "left_column": "table1.id",
        "right_column": "table2.foreign_id",
        "operator": "="
      }},
      "columns": ["col3"]
    }},
    {{
      "step_number": 3,
      "operation": "aggregate",
      "aggregation_function": "SUM",
      "aggregated_column": "amount",
      "group_by_columns": ["region"]
    }}
  ],
  "select_columns": [
    {{
      "column": "SUM(amount)",
      "alias": "total_amount",
      "source_table": "revenue_table"
    }},
    {{
      "column": "region",
      "alias": null,
      "source_table": "region_table"
    }}
  ],
  "from_table": "base_table_name",
  "joins": [
    {{
      "step": 2,
      "type": "LEFT JOIN",
      "table": "other_table",
      "condition": {{
        "left": "table1.id",
        "operator": "=",
        "right": "table2.foreign_id"
      }}
    }}
  ],
  "where_conditions": null,
  "group_by": ["region"],
  "having_conditions": null,
  "order_by": null,
  "subqueries": [],
  "complexity_indicators": {{
    "requires_join": true,
    "requires_aggregation": true,
    "join_count": 2,
    "aggregation_count": 1
  }}
}}

Guidelines:
- Use step-by-step reasoning internally to plan the query
- Identify the base table from the FROM subproblem
- Determine join order based on table relationships
- Map each SELECT column to its source table
- Plan aggregations if GROUP BY is present
- Support nested queries in subqueries array if needed
- Choose appropriate join types (INNER, LEFT, RIGHT, FULL) based on requirements
- Output ONLY the JSON, no explanations or reasoning text"""
        
        return system_prompt, user_prompt
    
    def _parse_query_plan_response(self, response: str) -> Dict:
        """
        Parse LLM response and extract query plan JSON.
        
        Extracts the JSON query plan from the LLM response, handling cases
        where the response may be wrapped in markdown code blocks or contain
        extra text. Validates the structure and ensures all required fields
        are present.
        
        Args:
            response: Raw response string from the LLM, which should contain
                    a JSON query plan, possibly wrapped in markdown code blocks.
        
        Returns:
            Dictionary containing the parsed query plan with structure:
            {
                "execution_steps": List[Dict] - Ordered execution steps
                "select_columns": List[Dict] - Columns to select with mappings
                "from_table": str - Base table name
                "joins": List[Dict] - Join operations
                "where_conditions": Dict or None - Filter conditions
                "group_by": List[str] or None - Grouping columns
                "having_conditions": Dict or None - Aggregate filters
                "order_by": List[Dict] or None - Sorting requirements
                "subqueries": List[Dict] - Nested queries (if any)
                "complexity_indicators": Dict - Complexity metadata
            }
        
        Raises:
            ValueError: If response cannot be parsed as valid JSON or is missing
                       required fields.
        
        Example:
            >>> response = '{{"execution_steps": [...], "from_table": "table1"}}'
            >>> plan = agent._parse_query_plan_response(response)
            >>> "execution_steps" in plan
            True
        """
        # Try to extract JSON from response
        response = response.strip()
        
        # Remove markdown code blocks if present
        if response.startswith("```json"):
            response = response[7:]
        elif response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()
        
        try:
            plan = json.loads(response)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Failed to parse JSON from response: {str(e)}\n"
                f"Response preview: {response[:300]}"
            )
        
        # Validate required fields
        required_fields = ["execution_steps", "select_columns", "from_table", "joins"]
        for field in required_fields:
            if field not in plan:
                raise ValueError(
                    f"Query plan missing required field: {field}\n"
                    f"Available fields: {list(plan.keys())}"
                )
        
        # Ensure optional fields exist with defaults
        if "where_conditions" not in plan:
            plan["where_conditions"] = None
        if "group_by" not in plan:
            plan["group_by"] = None
        if "having_conditions" not in plan:
            plan["having_conditions"] = None
        if "order_by" not in plan:
            plan["order_by"] = None
        if "subqueries" not in plan:
            plan["subqueries"] = []
        if "complexity_indicators" not in plan:
            plan["complexity_indicators"] = {
                "requires_join": len(plan.get("joins", [])) > 0,
                "requires_aggregation": plan.get("group_by") is not None,
                "join_count": len(plan.get("joins", [])),
                "aggregation_count": len([s for s in plan.get("execution_steps", []) if s.get("operation") == "aggregate"])
            }
        
        return plan
    
    def _validate_query_plan(self, plan: Dict) -> bool:
        """
        Validate query plan structure and logical consistency.
        
        Performs comprehensive validation on the query plan to ensure:
        - All required fields are present
        - Execution steps are numbered sequentially
        - Join conditions are valid
        - Column mappings reference valid tables
        - Aggregation logic is consistent with GROUP BY
        - No logical contradictions
        
        Args:
            plan: Query plan dictionary to validate.
        
        Returns:
            True if the plan is valid, otherwise raises ValueError with
            detailed error message.
        
        Raises:
            ValueError: If validation fails with specific error details.
        
        Example:
            >>> plan = {"execution_steps": [...], "from_table": "table1", ...}
            >>> agent._validate_query_plan(plan)
            True
        """
        # Validate execution_steps
        if not isinstance(plan.get("execution_steps"), list):
            raise ValueError("execution_steps must be a list")
        
        if len(plan["execution_steps"]) == 0:
            raise ValueError("execution_steps cannot be empty")
        
        # Check step numbering
        step_numbers = [step.get("step_number") for step in plan["execution_steps"]]
        expected_steps = list(range(1, len(plan["execution_steps"]) + 1))
        if step_numbers != expected_steps:
            raise ValueError(
                f"Execution steps must be numbered sequentially from 1. "
                f"Found: {step_numbers}, Expected: {expected_steps}"
            )
        
        # Validate from_table
        if not plan.get("from_table") or not isinstance(plan["from_table"], str):
            raise ValueError("from_table must be a non-empty string")
        
        # Validate select_columns
        if not isinstance(plan.get("select_columns"), list):
            raise ValueError("select_columns must be a list")
        
        if len(plan["select_columns"]) == 0:
            raise ValueError("select_columns cannot be empty")
        
        # Validate joins
        if not isinstance(plan.get("joins"), list):
            raise ValueError("joins must be a list")
        
        # Validate each join
        for join in plan["joins"]:
            if "type" not in join:
                raise ValueError("Each join must have a 'type' field")
            if "table" not in join:
                raise ValueError("Each join must have a 'table' field")
            if "condition" not in join:
                raise ValueError("Each join must have a 'condition' field")
            
            condition = join["condition"]
            if not isinstance(condition, dict):
                raise ValueError("Join condition must be a dictionary")
            
            required_condition_fields = ["left", "operator", "right"]
            for field in required_condition_fields:
                if field not in condition:
                    raise ValueError(f"Join condition missing required field: {field}")
        
        # Validate GROUP BY consistency
        if plan.get("group_by") is not None:
            if not isinstance(plan["group_by"], list):
                raise ValueError("group_by must be a list or None")
            
            # Check if there are aggregations in select_columns
            has_aggregation = any(
                "SUM(" in col.get("column", "") or
                "COUNT(" in col.get("column", "") or
                "AVG(" in col.get("column", "") or
                "MAX(" in col.get("column", "") or
                "MIN(" in col.get("column", "")
                for col in plan["select_columns"]
            )
            
            if not has_aggregation:
                raise ValueError(
                    "If group_by is specified, select_columns must include "
                    "aggregation functions (SUM, COUNT, AVG, etc.)"
                )
        
        # Validate subqueries structure
        if not isinstance(plan.get("subqueries"), list):
            raise ValueError("subqueries must be a list")
        
        return True
    
    def generate_query_plan(
        self,
        user_query: str,
        subproblems: Dict,
        filtered_schema: Optional[Dict] = None
    ) -> Dict:
        """
        Generate an executable query plan from subproblems.
        
        Main method that takes a user query and clause-wise subproblems, then
        generates a structured, step-by-step query plan using Chain of Thought
        reasoning. The plan includes execution steps, join order, column mappings,
        and aggregation logic. CoT reasoning is used internally but not included
        in the output.
        
        Args:
            user_query: The original natural language query from the user.
            subproblems: Dictionary containing clause-wise subproblems with keys:
                        - SELECT: str or None - What to select
                        - FROM: str or None - Which tables to use
                        - WHERE: str or None - Filtering conditions
                        - GROUP BY: str or None - Grouping columns
                        - HAVING: str or None - Aggregate filters
                        - ORDER BY: str or None - Sorting requirements
                        - complexity: str - Query complexity level
                        - requires_join: bool - Whether joins are needed
                        - requires_aggregation: bool - Whether aggregation is needed
            filtered_schema: Optional filtered schema dictionary. If provided,
                           includes schema information in the prompt for better
                           column and table mapping. Default is None.
        
        Returns:
            Dictionary containing the query plan with structure:
            {
                "query": str - The original user query
                "execution_steps": List[Dict] - Ordered execution steps
                "select_columns": List[Dict] - Columns to select with table mappings
                "from_table": str - Base table name
                "joins": List[Dict] - Join operations with conditions
                "where_conditions": Dict or None - Filter conditions
                "group_by": List[str] or None - Grouping columns
                "having_conditions": Dict or None - Aggregate filters
                "order_by": List[Dict] or None - Sorting requirements
                "subqueries": List[Dict] - Nested queries (if any)
                "complexity_indicators": Dict - Complexity metadata
            }
        
        Raises:
            ValueError: If query or subproblems are invalid.
            Exception: If API call fails or response cannot be parsed.
        
        Example:
            >>> agent = QueryPlanAgent()
            >>> subproblems = {
            ...     "SELECT": "revenue, region",
            ...     "FROM": "revenue_table, region_table",
            ...     "GROUP BY": "region",
            ...     "requires_join": True,
            ...     "requires_aggregation": True
            ... }
            >>> plan = agent.generate_query_plan(
            ...     user_query="Show revenue by region",
            ...     subproblems=subproblems
            ... )
            >>> "execution_steps" in plan
            True
            >>> len(plan["execution_steps"]) > 0
            True
        """
        # Validate inputs
        if not user_query or not user_query.strip():
            raise ValueError("User query cannot be empty")
        
        if not subproblems:
            raise ValueError("Subproblems cannot be empty")
        
        if "SELECT" not in subproblems or "FROM" not in subproblems:
            raise ValueError("Subproblems must contain at least SELECT and FROM keys")
        
        # Build CoT prompt
        system_prompt, user_prompt = self._build_cot_prompt(
            user_query,
            subproblems,
            filtered_schema
        )
        
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
            
            response_text = response.choices[0].message.content
            
            # Parse response
            plan = self._parse_query_plan_response(response_text)
            
            # Validate plan
            self._validate_query_plan(plan)
            
            # Add query to plan
            plan["query"] = user_query
            
            return plan
        
        except ValueError as e:
            # Re-raise validation/parsing errors
            raise
        except Exception as e:
            # Raise API or other errors
            raise Exception(
                f"Failed to generate query plan: {str(e)}\n"
                f"Query: {user_query[:100]}"
            ) from e

