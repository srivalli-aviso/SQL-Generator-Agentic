"""
Database Executor Module

Optional database execution for testing generated SQL queries.
Supports execution against ClickHouse and other databases via SQLAlchemy.
"""

# #region agent log
import json, os
try:
    with open('/Users/srivalli/Desktop/workspace/SQL-Generator-Agentic/.cursor/debug.log', 'a') as f:
        f.write(json.dumps({"sessionId":"debug-session","runId":"post-fix","hypothesisId":"B","location":"db_executor.py:11","message":"db_executor module loading","data":{},"timestamp":int(__import__('time').time()*1000)}) + '\n')
except: pass
# #endregion

from typing import Dict, Optional
try:
    # #region agent log
    import json, os
    with open('/Users/srivalli/Desktop/workspace/SQL-Generator-Agentic/.cursor/debug.log', 'a') as f:
        f.write(json.dumps({"sessionId":"debug-session","runId":"post-fix","hypothesisId":"B","location":"db_executor.py:18","message":"Attempting sqlalchemy import","data":{},"timestamp":int(__import__('time').time()*1000)}) + '\n')
    # #endregion
    from sqlalchemy import create_engine, text
    # #region agent log
    with open('/Users/srivalli/Desktop/workspace/SQL-Generator-Agentic/.cursor/debug.log', 'a') as f:
        f.write(json.dumps({"sessionId":"debug-session","runId":"post-fix","hypothesisId":"B","location":"db_executor.py:19","message":"sqlalchemy import successful","data":{},"timestamp":int(__import__('time').time()*1000)}) + '\n')
    # #endregion
except ImportError as e:
    # #region agent log
    import json, os
    with open('/Users/srivalli/Desktop/workspace/SQL-Generator-Agentic/.cursor/debug.log', 'a') as f:
        f.write(json.dumps({"sessionId":"debug-session","runId":"post-fix","hypothesisId":"B","location":"db_executor.py:21","message":"sqlalchemy import failed","data":{"error":str(e)},"timestamp":int(__import__('time').time()*1000)}) + '\n')
    # #endregion
    raise
import time


def execute_query(
    sql: str,
    connection_string: str,
    dialect: str = "clickhouse"
) -> Dict:
    """
    Execute SQL query against database.
    
    Executes the SQL query against the specified database and returns
    execution results or error information. Supports ClickHouse and other
    databases via SQLAlchemy.
    
    Args:
        sql: SQL string to execute.
        connection_string: Database connection string in SQLAlchemy format.
                          For ClickHouse: clickhouse+http://user:pass@host:port/db
        dialect: Database dialect. Default is "clickhouse".
    
    Returns:
        Dictionary containing execution results:
        {
            "success": bool - Whether execution succeeded
            "error": Optional[str] - Error message if execution failed
            "row_count": Optional[int] - Number of rows returned
            "execution_time": Optional[float] - Execution time in seconds
            "sample_rows": Optional[List] - Sample of returned rows (first 5)
        }
    
    Example:
        >>> sql = "SELECT 1 AS test"
        >>> result = execute_query(sql, "clickhouse+http://user:pass@host:port/db")
        >>> "success" in result
        True
    """
    if not sql or not sql.strip():
        return {
            "success": False,
            "error": "SQL query is empty",
            "row_count": None,
            "execution_time": None,
            "sample_rows": None
        }
    
    if not connection_string:
        return {
            "success": False,
            "error": "Connection string is required",
            "row_count": None,
            "execution_time": None,
            "sample_rows": None
        }
    
    start_time = time.time()
    
    try:
        # #region agent log
        import json, os
        with open('/Users/srivalli/Desktop/workspace/SQL-Generator-Agentic/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"post-fix","hypothesisId":"B","location":"db_executor.py:93","message":"Creating SQLAlchemy engine","data":{"connection_string_preview":connection_string[:50] + "..." if len(connection_string) > 50 else connection_string},"timestamp":int(__import__('time').time()*1000)}) + '\n')
        # #endregion
        # Create engine
        engine = create_engine(connection_string)
        # #region agent log
        with open('/Users/srivalli/Desktop/workspace/SQL-Generator-Agentic/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"post-fix","hypothesisId":"B","location":"db_executor.py:95","message":"Engine created successfully","data":{},"timestamp":int(__import__('time').time()*1000)}) + '\n')
        # #endregion
        
        # Execute query
        with engine.connect() as connection:
            # #region agent log
            with open('/Users/srivalli/Desktop/workspace/SQL-Generator-Agentic/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"post-fix","hypothesisId":"B","location":"db_executor.py:99","message":"Executing SQL query","data":{"sql_preview":sql[:100] + "..." if len(sql) > 100 else sql},"timestamp":int(__import__('time').time()*1000)}) + '\n')
            # #endregion
            result = connection.execute(text(sql))
            
            # Fetch results
            rows = result.fetchall()
            row_count = len(rows)
            # #region agent log
            with open('/Users/srivalli/Desktop/workspace/SQL-Generator-Agentic/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"post-fix","hypothesisId":"B","location":"db_executor.py:105","message":"Query executed successfully","data":{"row_count":row_count},"timestamp":int(__import__('time').time()*1000)}) + '\n')
            # #endregion
            
            # Get sample rows (first 5)
            sample_rows = []
            for i, row in enumerate(rows[:5]):
                if hasattr(row, '_asdict'):
                    sample_rows.append(dict(row._asdict()))
                elif hasattr(row, '_mapping'):
                    sample_rows.append(dict(row._mapping))
                else:
                    # Convert tuple to list
                    sample_rows.append(list(row))
            
            execution_time = time.time() - start_time
            
            return {
                "success": True,
                "error": None,
                "row_count": row_count,
                "execution_time": execution_time,
                "sample_rows": sample_rows
            }
    
    except Exception as e:
        # #region agent log
        import json, os, traceback
        error_str = str(e)
        with open('/Users/srivalli/Desktop/workspace/SQL-Generator-Agentic/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"post-fix","hypothesisId":"B","location":"db_executor.py:130","message":"Execution error","data":{"error":error_str,"error_type":type(e).__name__,"traceback":traceback.format_exc()[:500]},"timestamp":int(__import__('time').time()*1000)}) + '\n')
        # #endregion
        execution_time = time.time() - start_time
        
        # Provide helpful error message for missing ClickHouse dialect
        error_msg = str(e)
        if "clickhouse" in error_msg.lower() and ("plugin" in error_msg.lower() or "dialect" in error_msg.lower()):
            helpful_msg = (
                f"ClickHouse SQLAlchemy dialect not found. "
                f"Please install: pip install clickhouse-sqlalchemy\n"
                f"Original error: {error_msg}"
            )
        else:
            helpful_msg = error_msg
        
        return {
            "success": False,
            "error": helpful_msg,
            "row_count": None,
            "execution_time": execution_time,
            "sample_rows": None
        }

