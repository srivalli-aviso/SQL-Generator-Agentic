# Subproblem Agent Implementation Plan

Based on SQL-of-Thought paper: https://arxiv.org/pdf/2509.00581

## Overview

The Subproblem Agent decomposes natural language queries into clause-wise subproblems, breaking down complex queries into manageable SQL clause components (SELECT, FROM, WHERE, GROUP BY, HAVING, ORDER BY).

## Architecture

### Input
- **User Query**: Natural language query
- **Filtered Schema**: M-Schema filtered by Schema Linking Agent (contains only relevant tables/columns)

### Output
- **Structured JSON**: Clause-level subproblems with keys as SQL clause types and values as natural-language/semi-formal descriptions

### Process Flow
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

## Implementation Details

### 1. Core Module: `subproblem_agent.py`

**Class: `SubproblemAgent`**

**Key Methods:**
- `decompose_query(user_query: str, filtered_schema: Dict) -> Dict`
- `_generate_subproblems_prompt(user_query: str, filtered_schema: Dict) -> str`
- `_parse_subproblems_response(response: str) -> Dict`
- `_fallback_decomposition(user_query: str, filtered_schema: Dict) -> Dict`

### 2. Output Format

**Structured JSON:**
```json
{
  "SELECT": "revenue columns: won_amount, qtd, commit, upside",
  "FROM": "tables: metrics, qtd_commit_upside",
  "WHERE": "filters: year = 2023, region = 'Americas'",
  "GROUP BY": "grouping: region, segment",
  "HAVING": "aggregate filters: sum(revenue) > 10000",
  "ORDER BY": "sorting: revenue DESC",
  "complexity": "simple|moderate|complex",
  "requires_join": true|false,
  "requires_aggregation": true|false
}
```

### 3. Prompt Engineering

**System Prompt:**
- Role: Expert SQL Query Decomposer
- Task: Break down queries into SQL clause subproblems
- Output: Structured JSON with clause types as keys

**User Prompt Structure:**
1. User query
2. Filtered schema (tables and columns)
3. Instructions for clause-wise decomposition
4. Example output format

### 4. Fallback Strategy

**If decomposition fails:**
- Create fewer, higher-level subproblems
- Merge related clauses (e.g., SELECT + FROM together)
- Single subproblem representing whole intent
- Never give up - always return structured output

### 5. Integration Points

**Input Integration:**
- Receives filtered schema from `QueryBasedSchemaFilter.filter_schema()`
- Works with M-Schema format

**Output Integration:**
- Feeds into Query Plan Agent (future)
- Can be used directly for SQL generation (if needed)

### 6. Error Handling

- API failures: Retry with exponential backoff
- Parsing failures: Use fallback decomposition
- Invalid schema: Validate and provide helpful errors
- Timeout: Return fallback result

## File Structure

```
Subproblem_Agent/
├── subproblem_agent.py          # Main agent class
├── config.py                    # Configuration (Groq API, model settings)
├── prompts.py                   # Prompt templates
├── example_usage.py             # Example usage with 10 queries
├── test_subproblem_agent.py    # Unit tests
└── README.md                    # Documentation
```

## Configuration

- **Groq API**: Use GROQ_API_KEY environment variable
- **Model**: `gpt-4o-120b-preview` or `llama-3.1-70b-versatile` (via Groq)
- **Temperature**: 0.1 (for consistent decomposition)
- **Max Tokens**: 2000 (for subproblem descriptions)

## Testing

- Test with 10 queries from Schema_Linking_Agent
- Validate JSON structure
- Test fallback mechanisms
- Test with various query complexities

## Next Steps

1. Implement core `SubproblemAgent` class
2. Create prompt templates
3. Add fallback logic
4. Create example usage script
5. Test with real queries
6. Integrate with Schema Linking Agent output

