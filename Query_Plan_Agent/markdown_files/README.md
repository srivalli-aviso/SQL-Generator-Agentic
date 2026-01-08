# Query Plan Agent

Generates executable query plans from clause-wise subproblems using Chain of Thought (CoT) reasoning. Part of the SQL-of-Thought multi-agent framework for Text-to-SQL generation.

## Overview

The Query Plan Agent bridges the gap between subproblem decomposition and SQL generation by creating structured, step-by-step execution plans. It uses internal Chain of Thought reasoning to analyze subproblems and generate plans that include:

- **Execution Steps**: Ordered operations for query construction
- **Join Order & Conditions**: Table relationships and join logic
- **Column Mappings**: Which columns come from which tables
- **Aggregation Logic**: Functions and grouping strategies

## Architecture

```
Subproblem Agent Results (JSON)
    ↓
Query Plan Agent
    ├── Load subproblems from JSON
    ├── CoT Reasoning (internal)
    └── Generate Query Plan
    ↓
Query Plan (JSON)
    ↓
SQL Agent (separate folder)
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
from query_plan_agent import QueryPlanAgent
from config import QueryPlanConfig
import json

# Initialize agent
config = QueryPlanConfig(temperature=0.1)
agent = QueryPlanAgent(config)

# Load subproblems
subproblems_data = agent.load_subproblems("subproblems_query_1.json")

# Generate query plan
query_plan = agent.generate_query_plan(
    user_query=subproblems_data["query"],
    subproblems=subproblems_data["subproblems"]
)

# Save plan
with open("query_plan.json", "w") as f:
    json.dump(query_plan, f, indent=2)
```

### Running Example Script

```bash
# Make sure Subproblem Agent has generated results first
cd Query_Plan_Agent
python example_usage.py
```

The example script will:
1. Load all subproblem files from `../Subproblem_Agent/results/`
2. Generate query plans for each query
3. Save plans to `./results/query_plan_query_{i}.json`
4. Display summary statistics

## Configuration

Configuration is managed through `QueryPlanConfig`:

```python
from config import QueryPlanConfig

config = QueryPlanConfig(
    model="openai/gpt-oss-120b",  # Groq model (120B MoE, excellent for complex reasoning)
    temperature=0.1,  # Configurable (lower = more deterministic)
    max_tokens=3000,  # Higher for detailed plans
    subproblems_dir="../Subproblem_Agent/results",
    schema_path="../Schema_Linking_Agent/cisco_stage_app_modified_m_schema.json",
    results_dir="./results"
)
```

## Query Plan Structure

The query plan JSON has the following structure:

```json
{
  "query": "Show me revenue by region and segment",
  "execution_steps": [
    {
      "step_number": 1,
      "operation": "identify_base_table",
      "table": "revenue_table",
      "columns": ["revenue_amount", "region_id", "segment_id"]
    },
    {
      "step_number": 2,
      "operation": "join_table",
      "join_type": "LEFT JOIN",
      "table": "region_table",
      "join_condition": {
        "left_column": "revenue_table.region_id",
        "right_column": "region_table.id",
        "operator": "="
      },
      "columns": ["region_name"]
    }
  ],
  "select_columns": [
    {
      "column": "SUM(revenue_amount)",
      "alias": "total_revenue",
      "source_table": "revenue_table"
    }
  ],
  "from_table": "revenue_table",
  "joins": [...],
  "where_conditions": null,
  "group_by": ["region_name", "segment_name"],
  "having_conditions": null,
  "order_by": null,
  "subqueries": [],
  "complexity_indicators": {...}
}
```

## Features

- ✅ **Step-by-step execution plans** with ordered operations
- ✅ **Join order and conditions** with support for multiple join types
- ✅ **Column-to-table mappings** for accurate SQL generation
- ✅ **Aggregation and grouping logic** with function planning
- ✅ **Nested query support** for complex queries
- ✅ **Internal CoT reasoning** (not included in output)
- ✅ **Comprehensive validation** with clear error messages

## Input Requirements

The Query Plan Agent expects subproblems in the following format (from Subproblem Agent):

```json
{
  "query": "User query text",
  "subproblems": {
    "SELECT": "What to select",
    "FROM": "Which tables to use",
    "WHERE": null,
    "GROUP BY": null,
    "HAVING": null,
    "ORDER BY": null,
    "complexity": "moderate",
    "requires_join": true,
    "requires_aggregation": true
  }
}
```

## Error Handling

The agent raises exceptions on errors (no fallback mechanism):

- **FileNotFoundError**: If subproblems file doesn't exist
- **ValueError**: If subproblems are invalid or plan validation fails
- **Exception**: If API call fails or response cannot be parsed

## Integration

### With Subproblem Agent

The Query Plan Agent automatically integrates with Subproblem Agent results:

```python
# Subproblem Agent saves to: Subproblem_Agent/results/subproblems_query_1.json
# Query Plan Agent reads from: Subproblem_Agent/results/
# Query Plan Agent saves to: Query_Plan_Agent/results/query_plan_query_1.json
```

### With SQL Agent

The generated query plans are designed to be consumed by the SQL Agent (in a separate folder) for SQL generation.

## Files

- `query_plan_agent.py` - Main agent class
- `config.py` - Configuration settings
- `example_usage.py` - Example script with 10 queries
- `requirements.txt` - Dependencies
- `README.md` - This file
- `results/` - Output directory for query plans

## References

- **Paper**: SQL-of-Thought: Multi-agentic Text-to-SQL with Guided Error Correction
- **URL**: https://arxiv.org/pdf/2509.00581
- **Related Agents**: Subproblem Agent, Schema Linking Agent

## License

Part of the SQL-Generator-Agentic project.

