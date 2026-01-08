"""
SQL Formatter Module

Utility functions for formatting SQL queries in different styles:
- Pretty: Indented, multi-line format
- Compact: Single line, minimal whitespace
- None: No formatting changes
"""

import re


def format_pretty(sql: str) -> str:
    """
    Format SQL with pretty-printing (indented, multi-line).
    
    Converts SQL into a readable, indented format with proper line breaks
    and consistent indentation. Makes SQL easier to read and debug.
    
    Args:
        sql: Raw SQL string to format.
    
    Returns:
        Formatted SQL string with indentation and line breaks for readability.
    
    Example:
        >>> sql = "SELECT * FROM table WHERE id=1"
        >>> formatted = format_pretty(sql)
        >>> "SELECT" in formatted
        True
    """
    # Remove extra whitespace
    sql = re.sub(r'\s+', ' ', sql.strip())
    
    # Basic keyword replacements for better formatting
    sql = re.sub(r'\bSELECT\b', '\nSELECT', sql, flags=re.IGNORECASE)
    sql = re.sub(r'\bFROM\b', '\nFROM', sql, flags=re.IGNORECASE)
    sql = re.sub(r'\bWHERE\b', '\nWHERE', sql, flags=re.IGNORECASE)
    sql = re.sub(r'\bGROUP BY\b', '\nGROUP BY', sql, flags=re.IGNORECASE)
    sql = re.sub(r'\bHAVING\b', '\nHAVING', sql, flags=re.IGNORECASE)
    sql = re.sub(r'\bORDER BY\b', '\nORDER BY', sql, flags=re.IGNORECASE)
    sql = re.sub(r'\bINNER JOIN\b', '\nINNER JOIN', sql, flags=re.IGNORECASE)
    sql = re.sub(r'\bLEFT JOIN\b', '\nLEFT JOIN', sql, flags=re.IGNORECASE)
    sql = re.sub(r'\bRIGHT JOIN\b', '\nRIGHT JOIN', sql, flags=re.IGNORECASE)
    sql = re.sub(r'\bFULL JOIN\b', '\nFULL JOIN', sql, flags=re.IGNORECASE)
    sql = re.sub(r'\bJOIN\b', '\nJOIN', sql, flags=re.IGNORECASE)
    sql = re.sub(r'\bON\b', '\n    ON', sql, flags=re.IGNORECASE)
    sql = re.sub(r'\bAND\b', '\n    AND', sql, flags=re.IGNORECASE)
    sql = re.sub(r'\bOR\b', '\n    OR', sql, flags=re.IGNORECASE)
    
    # Add indentation for SELECT columns
    sql = re.sub(r'(SELECT\s+)([^\n]+?)(\s+FROM)', r'\1\n    \2\n\3', sql, flags=re.IGNORECASE)
    
    # Clean up multiple newlines
    sql = re.sub(r'\n\n+', '\n', sql)
    
    # Add indentation after main clauses
    lines = sql.split('\n')
    formatted_lines = []
    indent_level = 0
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Decrease indent before certain clauses
        if re.match(r'^(FROM|WHERE|GROUP BY|HAVING|ORDER BY)', line, re.IGNORECASE):
            indent_level = 0
        
        formatted_lines.append('    ' * indent_level + line)
        
        # Increase indent after SELECT, FROM, JOIN
        if re.match(r'^(SELECT|FROM|JOIN)', line, re.IGNORECASE):
            indent_level = 1
    
    return '\n'.join(formatted_lines).strip()


def format_compact(sql: str) -> str:
    """
    Format SQL in compact form (single line, minimal whitespace).
    
    Converts SQL into a single-line format with minimal whitespace, making
    it more compact for storage or transmission.
    
    Args:
        sql: Raw SQL string to format.
    
    Returns:
        Compact SQL string with minimal whitespace on a single line.
    
    Example:
        >>> sql = "SELECT\n    *\nFROM\n    table"
        >>> compact = format_compact(sql)
        >>> "\n" not in compact
        True
    """
    # Remove all newlines and extra whitespace
    sql = re.sub(r'\s+', ' ', sql.strip())
    return sql


def format_none(sql: str) -> str:
    """
    No formatting - pass through SQL as-is.
    
    Returns the SQL string without any formatting changes. Useful when
    the SQL is already in the desired format.
    
    Args:
        sql: SQL string to return unchanged.
    
    Returns:
        SQL string unchanged from input.
    
    Example:
        >>> sql = "SELECT * FROM table"
        >>> result = format_none(sql)
        >>> result == sql
        True
    """
    return sql

