# Subproblem Agent

Decomposes natural language queries into clause-wise subproblems based on the SQL-of-Thought framework.

## Overview

The Subproblem Agent is part of a multi-agent Text-to-SQL system. It takes a user query and filtered schema (from Schema Linking Agent) and decomposes the query into structured subproblems organized by SQL clause types (SELECT, FROM, WHERE, GROUP BY, HAVING, ORDER BY).

## Architecture

Based on [SQL-of-Thought paper](https://arxiv.org/pdf/2509.00581):

```
User Query + Filtered Schema 
    ↓
Subproblem Agent (Groq API)
    ↓
Clause-wise Decomposition
    ↓
Structured JSON Subproblems
    ↓
Query Plan Agent (next step)
```

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variable
export GROQ_API_KEY='your-groq-api-key'
```

## Usage

### Basic Usage

```python
from subproblem_agent import SubproblemAgent
from query_based_schema_filter import QueryBasedSchemaFilter

# Initialize Schema Linking Agent
schema_filter = QueryBasedSchemaFilter(
    schema_path="./schema.json",
    vector_db_path="./vector_db"
)

# Filter schema for a query
filtered_schema = schema_filter.filter_schema(
    user_query="Show me revenue by region and segment",
    top_k_tables=10,
    top_k_columns=15
)

# Initialize Subproblem Agent
agent = SubproblemAgent()

# Decompose query
subproblems = agent.decompose_query(
    user_query="Show me revenue by region and segment",
    filtered_schema=filtered_schema
)

print(subproblems)
```

### Output Format

```json
{
  "SELECT": "revenue columns: won_amount, qtd, commit, upside",
  "FROM": "tables: metrics, qtd_commit_upside",
  "WHERE": "filters: year = 2023",
  "GROUP BY": "grouping: region, segment",
  "HAVING": null,
  "ORDER BY": null,
  "complexity": "moderate",
  "requires_join": false,
  "requires_aggregation": true
}
```

## Features

- **Clause-wise Decomposition**: Breaks queries into SQL clause components
- **Structured Output**: JSON format with clause types as keys
- **Fallback Mechanism**: Always returns structured output, even on failure
- **Integration**: Works seamlessly with Schema Linking Agent
- **Multi-step Query Support**: Handles complex queries with multiple operations

## Configuration

Edit `config.py` or pass parameters to `SubproblemAgent()`:

```python
agent = SubproblemAgent(
    model="llama-3.1-70b-versatile",  # Groq model
    temperature=0.1,                   # Lower = more deterministic
    max_tokens=2000                    # Response length
)
```

## Example

Run the example script:

```bash
python3 example_usage.py
```

This will:
1. Process 10 example queries
2. Filter schema for each query
3. Decompose each into subproblems
4. Save results to `results/` folder

## Files

- `subproblem_agent.py` - Main agent class
- `config.py` - Configuration settings
- `example_usage.py` - Example usage with 10 queries
- `requirements.txt` - Python dependencies
- `README.md` - This file

## Next Steps

The subproblems output feeds into:
- **Query Plan Agent**: Generates executable query plans
- **SQL Agent**: Generates final SQL queries

## References

- SQL-of-Thought Paper: https://arxiv.org/pdf/2509.00581

