# Query Plan Agent - Implementation Plan

Based on SQL-of-Thought paper: https://arxiv.org/pdf/2509.00581

## Overview

The Query Plan Agent generates an executable query plan from clause-wise subproblems using Chain of Thought (CoT) reasoning. It bridges the gap between subproblem decomposition and SQL generation by creating a structured, step-by-step execution plan.

## Requirements Summary

- **Output Format**: Step-by-step execution plan (detailed reasoning steps internally, not in output)
- **Includes**: Join order/conditions, column-to-table mappings, aggregation/grouping logic
- **Excludes**: Natural-language reasoning/explanations in output
- **Input**: User query + subproblems from JSON files (`Subproblem_Agent/results/`)
- **Model**: Groq API (configurable temperature, other settings at default)
- **Detail Level**: Detailed - handles nested queries/subqueries, partially handles multiple join types
- **Error Handling**: Raise exception and let caller handle
- **Integration**: Automatically integrates with Subproblem Agent results

## Architecture

```
Subproblem Agent Results (JSON)
    ↓
Query Plan Agent
    ├── Load subproblems from JSON
    ├── Load filtered schema (if needed)
    ├── CoT Reasoning (internal)
    └── Generate Query Plan
    ↓
Query Plan (JSON)
    ├── Execution Steps
    ├── Join Order & Conditions
    ├── Column Mappings
    └── Aggregation Logic
```

## File Structure

```
Query_Plan_Agent/
├── query_plan_agent.py      # Main agent class
├── config.py                 # Configuration settings
├── example_usage.py          # Example script with 10 queries
├── requirements.txt          # Dependencies
├── README.md                 # Documentation
├── results/                  # Output directory
│   └── query_plan_query_{i}.json
└── QUERY_PLAN_AGENT_IMPLEMENTATION_PLAN.md  # This file
```

## Implementation Details

### 1. Configuration (`config.py`)

```python
@dataclass
class QueryPlanConfig:
    # Groq API Configuration
    model: str = "llama-3.1-70b-versatile"
    temperature: float = 0.1  # Configurable
    max_tokens: int = 3000  # Higher for detailed plans
    
    # Input Configuration
    subproblems_dir: str = "../Subproblem_Agent/results"
    schema_path: str = "../Schema_Linking_Agent/cisco_stage_app_modified_m_schema.json"
    
    # Output Configuration
    results_dir: str = "./results"
    output_format: str = "json"  # Always JSON
```

### 2. Query Plan Structure

The query plan JSON will have the following structure:

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
    },
    {
      "step_number": 3,
      "operation": "join_table",
      "join_type": "LEFT JOIN",
      "table": "segment_table",
      "join_condition": {
        "left_column": "revenue_table.segment_id",
        "right_column": "segment_table.id",
        "operator": "="
      },
      "columns": ["segment_name"]
    },
    {
      "step_number": 4,
      "operation": "aggregate",
      "aggregation_function": "SUM",
      "aggregated_column": "revenue_amount",
      "group_by_columns": ["region_name", "segment_name"]
    }
  ],
  "select_columns": [
    {
      "column": "SUM(revenue_amount)",
      "alias": "total_revenue",
      "source_table": "revenue_table"
    },
    {
      "column": "region_name",
      "alias": null,
      "source_table": "region_table"
    },
    {
      "column": "segment_name",
      "alias": null,
      "source_table": "segment_table"
    }
  ],
  "from_table": "revenue_table",
  "joins": [
    {
      "step": 2,
      "type": "LEFT JOIN",
      "table": "region_table",
      "condition": {
        "left": "revenue_table.region_id",
        "operator": "=",
        "right": "region_table.id"
      }
    },
    {
      "step": 3,
      "type": "LEFT JOIN",
      "table": "segment_table",
      "condition": {
        "left": "revenue_table.segment_id",
        "operator": "=",
        "right": "segment_table.id"
      }
    }
  ],
  "where_conditions": null,
  "group_by": ["region_name", "segment_name"],
  "having_conditions": null,
  "order_by": null,
  "subqueries": [],
  "complexity_indicators": {
    "requires_join": true,
    "requires_aggregation": true,
    "join_count": 2,
    "aggregation_count": 1
  }
}
```

### 3. Main Agent Class (`query_plan_agent.py`)

#### Key Methods:

1. **`__init__(config: QueryPlanConfig)`**
   - Initialize Groq client
   - Validate API key
   - Set up configuration

2. **`load_subproblems(subproblems_path: str) -> Dict`**
   - Load subproblems from JSON file
   - Validate structure
   - Return subproblems dictionary

3. **`generate_query_plan(user_query: str, subproblems: Dict, filtered_schema: Optional[Dict] = None) -> Dict`**
   - Main method to generate query plan
   - Uses CoT reasoning internally (not in output)
   - Returns structured query plan

4. **`_build_cot_prompt(user_query: str, subproblems: Dict, schema: Optional[Dict]) -> str`**
   - Build Chain of Thought prompt
   - Include subproblems analysis
   - Guide step-by-step reasoning
   - Request structured output

5. **`_parse_query_plan_response(response: str) -> Dict`**
   - Parse LLM response
   - Extract JSON from markdown if needed
   - Validate structure
   - Return query plan dictionary

6. **`_validate_query_plan(plan: Dict) -> bool`**
   - Validate query plan structure
   - Check required fields
   - Ensure logical consistency
   - Raise exceptions on validation failure

### 4. Chain of Thought Prompt Structure

The CoT prompt will guide the LLM through:

1. **Analyze Subproblems**
   - Understand SELECT requirements
   - Identify FROM tables
   - Process WHERE/GROUP BY/HAVING/ORDER BY if present

2. **Plan Table Relationships**
   - Identify base table
   - Determine join order
   - Map foreign key relationships
   - Choose join types (INNER/LEFT/RIGHT/FULL)

3. **Map Columns**
   - Map each SELECT column to source table
   - Identify aggregation needs
   - Handle column aliases

4. **Plan Aggregations**
   - Identify aggregation functions (SUM, COUNT, AVG, etc.)
   - Determine GROUP BY columns
   - Plan HAVING conditions if needed

5. **Structure Execution Steps**
   - Order operations logically
   - Handle nested queries if needed
   - Plan filter application order

### 5. Example Usage Script (`example_usage.py`)

The script will:
1. Load all 10 subproblem JSON files from `Subproblem_Agent/results/`
2. For each subproblem file:
   - Extract user query and subproblems
   - Optionally load filtered schema
   - Generate query plan
   - Save to `results/query_plan_query_{i}.json`
3. Display summary statistics

### 6. Error Handling

- **Invalid Subproblems JSON**: Raise `ValueError` with clear message
- **API Failures**: Raise `Exception` with error details
- **Invalid Plan Structure**: Raise `ValueError` during validation
- **Missing Required Fields**: Raise `ValueError` with missing field names

No fallback mechanism - exceptions propagate to caller.

### 7. Integration Points

#### Input Integration:
- Reads from `Subproblem_Agent/results/subproblems_query_{i}.json`
- Can optionally receive filtered schema from Schema Linking Agent

#### Output Integration:
- Saves to `Query_Plan_Agent/results/query_plan_query_{i}.json`
- Structured format ready for SQL Agent consumption

## Implementation Steps

### Phase 1: Core Structure
1. ✅ Create `config.py` with `QueryPlanConfig`
2. ✅ Create `query_plan_agent.py` with basic class structure
3. ✅ Implement `__init__` and Groq client setup
4. ✅ Create `requirements.txt`

### Phase 2: Input Handling
5. ✅ Implement `load_subproblems()` method
6. ✅ Add subproblem validation
7. ✅ Handle schema loading (optional)

### Phase 3: Query Plan Generation
8. ✅ Implement `_build_cot_prompt()` method
9. ✅ Design CoT prompt template
10. ✅ Implement `generate_query_plan()` method
11. ✅ Add LLM API call with CoT reasoning

### Phase 4: Response Processing
12. ✅ Implement `_parse_query_plan_response()` method
13. ✅ Add JSON extraction from markdown
14. ✅ Implement `_validate_query_plan()` method
15. ✅ Add comprehensive validation checks

### Phase 5: Example and Testing
16. ✅ Create `example_usage.py` script
17. ✅ Integrate with Subproblem Agent results
18. ✅ Test with all 10 queries
19. ✅ Create `README.md` with documentation

### Phase 6: Refinement
20. ✅ Handle nested queries in plan structure
21. ✅ Support multiple join types (INNER, LEFT, RIGHT, FULL)
22. ✅ Test edge cases and error scenarios
23. ✅ Optimize prompt for better plan quality

## Prompt Design Considerations

### CoT Reasoning Steps (Internal, not in output):

1. **Step 1: Analyze SELECT subproblem**
   - What columns/data are needed?
   - Are aggregations required?
   - Any column aliases needed?

2. **Step 2: Analyze FROM subproblem**
   - Which tables are involved?
   - What is the base table?
   - How are tables related?

3. **Step 3: Plan Joins**
   - Determine join order
   - Identify join conditions (foreign keys)
   - Choose appropriate join types
   - Map columns from each table

4. **Step 4: Plan Aggregations**
   - Identify aggregation functions
   - Determine GROUP BY columns
   - Plan HAVING conditions if needed

5. **Step 5: Plan Filters**
   - Process WHERE conditions
   - Determine filter application order
   - Handle complex conditions

6. **Step 6: Plan Sorting**
   - Process ORDER BY requirements
   - Determine sort columns and direction

7. **Step 7: Handle Complexity**
   - Check for nested queries
   - Plan subquery structure if needed
   - Integrate subqueries into main plan

8. **Step 8: Structure Execution Steps**
   - Order all operations logically
   - Create step-by-step execution plan
   - Ensure all dependencies are resolved

## Validation Rules

The query plan must have:
- ✅ At least one execution step
- ✅ Valid `from_table` (string, non-empty)
- ✅ `select_columns` array with at least one column
- ✅ `joins` array (can be empty)
- ✅ Each join must have: type, table, condition
- ✅ Each select column must have: column, source_table
- ✅ If GROUP BY exists, must have aggregation in select_columns
- ✅ Execution steps must be numbered sequentially starting from 1
- ✅ Join step numbers must reference valid execution steps

## Dependencies

```txt
groq>=0.4.0
python-dotenv>=1.0.0
```

## Configuration Example

```python
from config import QueryPlanConfig

config = QueryPlanConfig(
    model="llama-3.1-70b-versatile",
    temperature=0.1,  # Configurable
    max_tokens=3000,
    subproblems_dir="../Subproblem_Agent/results",
    schema_path="../Schema_Linking_Agent/cisco_stage_app_modified_m_schema.json"
)
```

## Usage Example

```python
from query_plan_agent import QueryPlanAgent
from config import QueryPlanConfig
import json

# Initialize agent
config = QueryPlanConfig(temperature=0.1)
agent = QueryPlanAgent(config)

# Load subproblems
subproblems = agent.load_subproblems("subproblems_query_1.json")

# Generate query plan
query_plan = agent.generate_query_plan(
    user_query=subproblems["query"],
    subproblems=subproblems["subproblems"]
)

# Save plan
with open("query_plan_query_1.json", "w") as f:
    json.dump(query_plan, f, indent=2)
```

## Testing Strategy

1. **Unit Tests**: Test individual methods (parsing, validation)
2. **Integration Tests**: Test with real subproblem files
3. **End-to-End Tests**: Test full pipeline with 10 queries
4. **Error Tests**: Test error handling and exceptions
5. **Edge Cases**: Test with complex queries, nested queries, multiple joins

## Success Criteria

- ✅ Generates valid query plans for all 10 test queries
- ✅ Handles nested queries/subqueries
- ✅ Supports multiple join types (at least INNER and LEFT)
- ✅ Provides clear column-to-table mappings
- ✅ Includes proper aggregation and grouping logic
- ✅ Raises clear exceptions on errors
- ✅ Integrates seamlessly with Subproblem Agent results
- ✅ Output format is consistent and structured

## Next Steps After Implementation

1. Integrate with SQL Agent (separate folder)
2. Add query plan visualization (optional)
3. Performance optimization
4. Extended join type support (RIGHT, FULL)
5. Advanced nested query handling

## References

- **Paper**: SQL-of-Thought: Multi-agentic Text-to-SQL with Guided Error Correction
- **URL**: https://arxiv.org/pdf/2509.00581
- **Related Agents**: Subproblem Agent, Schema Linking Agent

