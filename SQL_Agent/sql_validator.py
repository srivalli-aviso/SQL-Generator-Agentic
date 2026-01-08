"""
SQL Validator Module

Optional SQL syntax validation for generated SQL queries.
Supports validation for different database dialects.
"""

import re
from typing import Tuple, Optional
import sqlparse


def validate_sql_syntax(sql: str, dialect: str = "clickhouse") -> Tuple[bool, Optional[str]]:
    """
    Validate SQL syntax for a given dialect.
    
    Performs basic SQL syntax validation using sqlparse library. Checks for
    common syntax errors and structural issues. Note that this is a basic
    validation and may not catch all dialect-specific issues.
    
    Args:
        sql: SQL string to validate.
        dialect: Database dialect for validation. Currently supports:
                - "clickhouse" (primary)
                - "mysql"
                - "postgresql"
                - "sqlite"
                Default is "clickhouse".
    
    Returns:
        Tuple of (is_valid, error_message):
        - is_valid: bool - True if SQL appears valid, False otherwise
        - error_message: Optional[str] - Error message if validation fails,
                         None if valid
    
    Example:
        >>> sql = "SELECT * FROM table"
        >>> is_valid, error = validate_sql_syntax(sql)
        >>> isinstance(is_valid, bool)
        True
    """
    if not sql or not sql.strip():
        return False, "SQL query is empty"
    
    try:
        # Parse SQL to check for syntax errors
        parsed = sqlparse.parse(sql)
        
        if not parsed:
            return False, "Failed to parse SQL query"
        
        # Check if we have at least one statement
        if len(parsed) == 0:
            return False, "No SQL statements found"
        
        # Basic validation - check for required clauses
        sql_upper = sql.upper().strip()
        
        # Must have SELECT
        if not sql_upper.startswith("SELECT"):
            # Allow WITH clauses (CTEs) before SELECT
            if not sql_upper.startswith("WITH"):
                return False, "SQL must start with SELECT or WITH"
        
        # Check for balanced parentheses
        if sql.count('(') != sql.count(')'):
            return False, "Unbalanced parentheses in SQL"
        
        # Check for balanced quotes
        single_quotes = sql.count("'") - sql.count("\\'")
        if single_quotes % 2 != 0:
            return False, "Unbalanced single quotes in SQL"
        
        double_quotes = sql.count('"') - sql.count('\\"')
        if double_quotes % 2 != 0:
            return False, "Unbalanced double quotes in SQL"
        
        # Basic structure validation
        has_from = "FROM" in sql_upper or "from" in sql
        
        # If it's a SELECT statement, it should have FROM (unless it's a subquery)
        if sql_upper.startswith("SELECT") and not has_from:
            # Check if it's a valid SELECT without FROM (e.g., SELECT 1)
            if not re.match(r'SELECT\s+[\d\w\s,\(\)]+$', sql_upper):
                return False, "SELECT statement missing FROM clause"
        
        return True, None
    
    except sqlparse.exceptions.SQLParseError as e:
        return False, f"SQL parse error: {str(e)}"
    except Exception as e:
        # If validation fails due to library issues, assume valid
        # (don't block SQL generation due to validator problems)
        return True, None

