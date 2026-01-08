# SQL Agent

Generates valid SQL queries from structured query plans using LLM-based generation. Part of the SQL-of-Thought multi-agent framework for Text-to-SQL generation.

## Overview

The SQL Agent converts executable query plans into syntactically and logically correct SQL queries. It uses Groq API (LLM-based) for flexible SQL generation with fallback support, configurable formatting, optional validation, and optional database execution.

## Architecture

```
Query Plan Agent Results (JSON)
    ↓
SQL Agent
    ├── Load query plan from JSON
    ├── LLM-based SQL Generation (Groq API)
    ├── Fallback Generation (if primary fails)
    ├── Optional SQL Validation
    ├── Optional SQL Formatting
    └── Optional Database Execution
    ↓
SQL Query (string) + Metadata
```

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set environment variable:
```bash
export GROQ_API_KEY='your-api-key'
```

## Usage

### Basic Usage

```python
from sql_agent import SQLAgent
from config import SQLAgentConfig
import json

# Initialize agent
config = SQLAgentConfig(temperature=0.1)
agent = SQLAgent(config)

# Load query plan
query_plan = agent.load_query_plan("query_plan_query_1.json")

# Generate SQL
sql = agent.generate_sql(query_plan)

# Save SQL
print(sql)
```

### Running Example Script

```bash
# Make sure Query Plan Agent has generated results first
cd SQL_Agent
python example_usage.py
```

The example script will:
1. Load all query plan files from `../Query_Plan_Agent/results/`
2. Generate SQL for each query plan
3. Optionally validate SQL (if enabled)
4. Optionally execute SQL against database (if enabled)
5. Save results to `./results/sql_query_{i}.json`

## Configuration

Configuration is managed through `SQLAgentConfig`:

```python
from config import SQLAgentConfig

config = SQLAgentConfig(
    model="openai/gpt-oss-120b",  # Groq model (same as Query Plan Agent)
    temperature=0.1,  # Low temperature (0-0.2), configurable
    max_tokens=2000,  # For SQL generation
    query_plans_dir="../Query_Plan_Agent/results",
    sql_format="pretty",  # "pretty" | "compact" | "none"
    enable_fallback=True,  # Enable fallback generation
    enable_validation=False,  # Optional SQL validation
    enable_execution=False,  # Optional database execution
    database_dialect="clickhouse",  # Primary dialect
    db_connection_string=None  # For execution testing
)
```

## Features

- ✅ **LLM-based SQL generation** using Groq API
- ✅ **Fallback generation** for error recovery
- ✅ **Configurable SQL formatting** (pretty, compact, none)
- ✅ **Optional SQL validation** (syntax checking)
- ✅ **Optional database execution** (testing against real database)
- ✅ **ClickHouse dialect support** (primary)
- ✅ **Advanced subquery support** (CTEs, nested, correlated)
- ✅ **Handles both string and structured** WHERE/HAVING/ORDER BY formats

## Input Requirements

The SQL Agent expects query plans in the following format (from Query Plan Agent):

```json
{
  "query": "User query text",
  "execution_steps": [...],
  "select_columns": [...],
  "from_table": "table_name",
  "joins": [...],
  "where_conditions": null,
  "group_by": [...],
  "having_conditions": null,
  "order_by": null,
  "subqueries": []
}
```

## Output Format

Each generated SQL is saved as JSON:

```json
{
  "query": "Show me revenue by region and segment",
  "sql": "SELECT SUM(metrics.revenue_amount) AS total_revenue...",
  "sql_formatted": "SELECT\n    SUM(metrics.revenue_amount) AS total_revenue...",
  "generation_method": "llm",
  "validation": {
    "enabled": false,
    "is_valid": null,
    "error": null
  },
  "execution": {
    "enabled": false,
    "success": null,
    "error": null,
    "row_count": null
  },
  "query_plan_source": "query_plan_query_1.json"
}
```

## Error Handling

The agent handles errors gracefully:

- **Invalid Query Plan**: Raises `ValueError` with clear message
- **LLM Generation Failure**: Attempts fallback generation (if enabled)
- **SQL Validation Failure**: Returns error message (if validation enabled)
- **Execution Failure**: Returns error details (if execution enabled)

## Integration

### With Query Plan Agent

The SQL Agent automatically integrates with Query Plan Agent results:

```python
# Query Plan Agent saves to: Query_Plan_Agent/results/query_plan_query_1.json
# SQL Agent reads from: Query_Plan_Agent/results/
# SQL Agent saves to: SQL_Agent/results/sql_query_1.json
```

### With Database Execution

The generated SQL is ready for database execution. If execution fails, the SQL and error can be fed into the Correction Loop (Correction Plan Agent and Correction SQL Agent).

## Files

- `sql_agent.py` - Main agent class
- `config.py` - Configuration settings
- `sql_formatter.py` - SQL formatting utilities
- `sql_validator.py` - Optional SQL validation
- `db_executor.py` - Optional database execution
- `example_usage.py` - Example script with 10 queries
- `requirements.txt` - Dependencies
- `README.md` - This file
- `results/` - Output directory for SQL queries

## SQL Formatting

The agent supports three formatting modes:

- **pretty**: Indented, multi-line format (default)
- **compact**: Single line, minimal whitespace
- **none**: No formatting changes

## Optional Features

### SQL Validation

Enable validation to check SQL syntax:

```python
config = SQLAgentConfig(enable_validation=True)
agent = SQLAgent(config)
is_valid, error = agent.validate_sql(sql)
```

### Database Execution

Enable execution to test SQL against database:

```python
config = SQLAgentConfig(
    enable_execution=True,
    db_connection_string="clickhouse+http://user:pass@host:port/db"
)
agent = SQLAgent(config)
result = agent.execute_sql(sql)
```

## References

- **Paper**: SQL-of-Thought: Multi-agentic Text-to-SQL with Guided Error Correction
- **URL**: https://arxiv.org/pdf/2509.00581
- **Related Agents**: Query Plan Agent, Schema Linking Agent, Subproblem Agent

## License

Part of the SQL-Generator-Agentic project.


