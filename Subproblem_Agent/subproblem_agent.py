"""
Subproblem Agent Module

Decomposes natural language queries into clause-wise subproblems based on
SQL-of-Thought framework. Breaks down queries into SQL clause components
(SELECT, FROM, WHERE, GROUP BY, HAVING, ORDER BY) for structured processing.
"""

import os
import json
from typing import Dict, List, Optional
from groq import Groq


class SubproblemAgent:
    """
    Agent that decomposes natural language queries into clause-wise subproblems.
    
    Based on SQL-of-Thought framework, this agent breaks down user queries
    into structured subproblems organized by SQL clause types. Each subproblem
    represents a component of the final SQL query.
    
    Attributes:
        client: Groq API client instance
        model: Model name to use for decomposition
        temperature: Temperature setting for generation
        max_tokens: Maximum tokens for response
    
    Example:
        >>> agent = SubproblemAgent()
        >>> filtered_schema = load_filtered_schema("filtered_schema.json")
        >>> subproblems = agent.decompose_query(
        ...     "Show me revenue by region and segment",
        ...     filtered_schema
        ... )
        >>> "SELECT" in subproblems
        True
    """
    
    def __init__(
        self,
        model: str = "llama-3.1-70b-versatile",
        temperature: float = 0.1,
        max_tokens: int = 2000
    ):
        """
        Initialize the Subproblem Agent.
        
        Args:
            model: Groq model to use. Options:
                  - "llama-3.1-70b-versatile" (default, fast, good quality)
                  - "gpt-4o-120b-preview" (if available via Groq)
                  - "mixtral-8x7b-32768" (alternative)
            temperature: Temperature for generation (0.0-1.0). Lower = more deterministic.
                        Default is 0.1 for consistent decomposition.
            max_tokens: Maximum tokens in response. Default is 2000.
        
        Raises:
            ValueError: If GROQ_API_KEY is not set in environment.
        
        Example:
            >>> agent = SubproblemAgent(model="llama-3.1-70b-versatile")
        """
        # Check for API key
        if "GROQ_API_KEY" not in os.environ:
            raise ValueError(
                "GROQ_API_KEY environment variable is not set. "
                "Please set it using: export GROQ_API_KEY='your-api-key'"
            )
        
        self.client = Groq()
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
    
    def _format_schema_for_prompt(self, filtered_schema: Dict) -> str:
        """
        Format filtered M-Schema into a readable string for the prompt.
        
        Converts the filtered schema dictionary into a structured text
        representation that can be included in the LLM prompt.
        
        Args:
            filtered_schema: Filtered M-Schema dictionary with structure:
                           - "tables": Dict - Dictionary of tables
                           - "db_id": str - Database identifier
                           - "schema": str - Schema name
        
        Returns:
            Formatted string representation of the schema.
        
        Example:
            >>> schema = {"tables": {"table1": {"fields": {...}}}}
            >>> formatted = agent._format_schema_for_prompt(schema)
            >>> "table1" in formatted
            True
        """
        schema_text = []
        tables = filtered_schema.get('tables', {})
        
        for table_name, table_data in tables.items():
            schema_text.append(f"\nTable: {table_name}")
            schema_text.append(f"Description: {table_data.get('table_description', 'N/A')}")
            
            fields = table_data.get('fields', {})
            if fields:
                schema_text.append("Columns:")
                for col_name, col_info in fields.items():
                    col_type = col_info.get('type', '')
                    col_desc = col_info.get('column_description', '')
                    is_pk = col_info.get('primary_key', False)
                    pk_marker = " (PRIMARY KEY)" if is_pk else ""
                    schema_text.append(f"  - {col_name} ({col_type}){pk_marker}: {col_desc}")
        
        return "\n".join(schema_text)
    
    def _generate_subproblems_prompt(
        self,
        user_query: str,
        filtered_schema: Dict
    ) -> str:
        """
        Generate the prompt for subproblem decomposition.
        
        Creates a comprehensive prompt that instructs the LLM to decompose
        the user query into clause-wise subproblems based on the provided
        filtered schema.
        
        Args:
            user_query: Natural language query from the user.
            filtered_schema: Filtered M-Schema dictionary.
        
        Returns:
            Complete prompt string for the LLM.
        
        Example:
            >>> prompt = agent._generate_subproblems_prompt(
            ...     "Show revenue by region",
            ...     filtered_schema
            ... )
            >>> "SELECT" in prompt or "decompose" in prompt.lower()
            True
        """
        schema_text = self._format_schema_for_prompt(filtered_schema)
        
        system_prompt = """You are an Expert SQL Query Decomposer specializing in breaking down natural language queries into structured, clause-wise subproblems.

Your task is to analyze a user query and the available database schema, then decompose the query into SQL clause subproblems. Each subproblem should correspond to a specific SQL clause type (SELECT, FROM, WHERE, GROUP BY, HAVING, ORDER BY).

# OBJECTIVES #
1. Identify what data needs to be selected (SELECT clause)
2. Identify which tables are needed (FROM clause)
3. Identify any filtering conditions (WHERE clause)
4. Identify grouping requirements (GROUP BY clause)
5. Identify aggregate filtering (HAVING clause)
6. Identify sorting requirements (ORDER BY clause)

# OUTPUT FORMAT #
Return a JSON object with the following structure:
{
  "SELECT": "description of what columns/expressions to select",
  "FROM": "description of which tables to use and how to join them",
  "WHERE": "description of filtering conditions (or null if none)",
  "GROUP BY": "description of grouping columns (or null if none)",
  "HAVING": "description of aggregate filters (or null if none)",
  "ORDER BY": "description of sorting requirements (or null if none)",
  "complexity": "simple|moderate|complex",
  "requires_join": true|false,
  "requires_aggregation": true|false
}

# RULES #
- Use natural language or semi-formal descriptions for each clause
- Be specific about table and column names from the schema
- If a clause is not needed, set it to null
- Always return valid JSON
- If the query is unclear, make reasonable assumptions based on the schema
- For multi-step queries, break them down into the main query structure"""
        
        user_prompt = f"""# USER QUERY #
{user_query}

# AVAILABLE SCHEMA #
{schema_text}

# TASK #
Decompose the above query into clause-wise subproblems. Analyze what the user wants and break it down into SQL clause components.

Return ONLY the JSON object, no additional text or explanation."""
        
        return system_prompt, user_prompt
    
    def _parse_subproblems_response(self, response: str) -> Dict:
        """
        Parse the LLM response into structured subproblems dictionary.
        
        Extracts JSON from the response and validates the structure.
        Handles cases where the response might contain extra text.
        
        Args:
            response: Raw response string from the LLM.
        
        Returns:
            Dictionary containing subproblems with clause types as keys.
        
        Raises:
            ValueError: If response cannot be parsed as valid JSON.
        
        Example:
            >>> response = '{{"SELECT": "revenue columns", "FROM": "metrics table"}}'
            >>> parsed = agent._parse_subproblems_response(response)
            >>> parsed["SELECT"]
            'revenue columns'
        """
        # Try to extract JSON from response
        response = response.strip()
        
        # Remove markdown code blocks if present
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()
        
        try:
            subproblems = json.loads(response)
            
            # Validate structure
            required_keys = ["SELECT", "FROM"]
            for key in required_keys:
                if key not in subproblems:
                    raise ValueError(f"Missing required key: {key}")
            
            # Ensure all clause keys exist (set to null if missing)
            clause_keys = ["SELECT", "FROM", "WHERE", "GROUP BY", "HAVING", "ORDER BY"]
            for key in clause_keys:
                if key not in subproblems:
                    subproblems[key] = None
            
            # Ensure metadata keys exist
            if "complexity" not in subproblems:
                subproblems["complexity"] = "moderate"
            if "requires_join" not in subproblems:
                subproblems["requires_join"] = False
            if "requires_aggregation" not in subproblems:
                subproblems["requires_aggregation"] = False
            
            return subproblems
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON from response: {str(e)}\nResponse: {response[:200]}")
    
    def _fallback_decomposition(
        self,
        user_query: str,
        filtered_schema: Dict
    ) -> Dict:
        """
        Fallback decomposition when primary method fails.
        
        Creates a coarser, higher-level decomposition when the detailed
        clause-wise decomposition cannot be generated. This ensures we
        always return structured output, even if less granular.
        
        Args:
            user_query: Natural language query from the user.
            filtered_schema: Filtered M-Schema dictionary.
        
        Returns:
            Dictionary with merged/coarse subproblems.
        
        Example:
            >>> fallback = agent._fallback_decomposition(
            ...     "Show revenue",
            ...     filtered_schema
            ... )
            >>> "SELECT" in fallback
            True
        """
        # Get table names from schema
        tables = list(filtered_schema.get('tables', {}).keys())
        table_list = ", ".join(tables) if tables else "available tables"
        
        # Create a merged subproblem
        return {
            "SELECT": f"Extract relevant data from: {user_query}",
            "FROM": f"Use tables: {table_list}",
            "WHERE": None,
            "GROUP BY": None,
            "HAVING": None,
            "ORDER BY": None,
            "complexity": "moderate",
            "requires_join": len(tables) > 1,
            "requires_aggregation": "by" in user_query.lower() or "group" in user_query.lower()
        }
    
    def decompose_query(
        self,
        user_query: str,
        filtered_schema: Dict
    ) -> Dict:
        """
        Decompose a user query into clause-wise subproblems.
        
        Main method that takes a natural language query and filtered schema,
        then decomposes it into structured subproblems organized by SQL clauses.
        Uses Groq API for decomposition with fallback mechanism.
        
        Args:
            user_query: Natural language query from the user.
            filtered_schema: Filtered M-Schema dictionary from Schema Linking Agent.
                           Should contain only relevant tables and columns.
        
        Returns:
            Dictionary containing subproblems with structure:
            {
                "SELECT": str or None - What to select
                "FROM": str or None - Which tables to use
                "WHERE": str or None - Filtering conditions
                "GROUP BY": str or None - Grouping columns
                "HAVING": str or None - Aggregate filters
                "ORDER BY": str or None - Sorting requirements
                "complexity": str - "simple"|"moderate"|"complex"
                "requires_join": bool - Whether joins are needed
                "requires_aggregation": bool - Whether aggregation is needed
            }
        
        Raises:
            ValueError: If query or schema is invalid.
            Exception: If API call fails after retries.
        
        Example:
            >>> agent = SubproblemAgent()
            >>> filtered_schema = {
            ...     "tables": {
            ...         "metrics": {"fields": {...}, "table_description": "..."}
            ...     }
            ... }
            >>> subproblems = agent.decompose_query(
            ...     "Show me revenue by region",
            ...     filtered_schema
            ... )
            >>> subproblems["SELECT"]
            'revenue columns...'
        """
        if not user_query or not user_query.strip():
            raise ValueError("User query cannot be empty")
        
        if not filtered_schema or not filtered_schema.get('tables'):
            raise ValueError("Filtered schema must contain at least one table")
        
        # Generate prompt
        system_prompt, user_prompt = self._generate_subproblems_prompt(
            user_query,
            filtered_schema
        )
        
        # Call Groq API
        try:
            # Note: Groq may not support response_format, so we'll parse JSON from text response
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
            try:
                subproblems = self._parse_subproblems_response(response_text)
                return subproblems
            except ValueError as parse_error:
                print(f"⚠ Warning: Failed to parse response, using fallback: {parse_error}")
                return self._fallback_decomposition(user_query, filtered_schema)
        
        except Exception as e:
            print(f"⚠ Warning: API call failed, using fallback: {str(e)}")
            return self._fallback_decomposition(user_query, filtered_schema)
    
    def decompose_batch(
        self,
        queries: List[str],
        filtered_schemas: List[Dict]
    ) -> List[Dict]:
        """
        Decompose multiple queries in batch.
        
        Processes multiple queries sequentially, decomposing each one
        into clause-wise subproblems. Useful for testing or processing
        multiple queries at once.
        
        Args:
            queries: List of natural language queries.
            filtered_schemas: List of filtered M-Schema dictionaries,
                            one for each query.
        
        Returns:
            List of subproblem dictionaries, one for each query.
        
        Example:
            >>> queries = ["Show revenue", "Find metrics"]
            >>> schemas = [schema1, schema2]
            >>> results = agent.decompose_batch(queries, schemas)
            >>> len(results)
            2
        """
        if len(queries) != len(filtered_schemas):
            raise ValueError("Number of queries must match number of schemas")
        
        results = []
        for query, schema in zip(queries, filtered_schemas):
            subproblems = self.decompose_query(query, schema)
            results.append(subproblems)
        
        return results

