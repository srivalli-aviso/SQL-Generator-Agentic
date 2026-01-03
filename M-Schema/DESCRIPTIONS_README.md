# Table and Column Descriptions Guide

This guide explains how to add and manage table/column descriptions in the M-Schema JSON file.

## Files

- **`descriptions.py`**: Contains all table and column descriptions in Python dictionaries
- **`add_descriptions.py`**: Script to add descriptions to the JSON file
- **`cisco_stage_app_clickhouse.json`**: The M-Schema JSON file (updated with descriptions)

## Usage

### Adding Descriptions to JSON

```bash
# Add descriptions to the default JSON file (overwrites original)
python3 add_descriptions.py cisco_stage_app_clickhouse.json

# Add descriptions and save to a new file
python3 add_descriptions.py cisco_stage_app_clickhouse.json output_with_descriptions.json
```

### Updating Descriptions

1. Edit `descriptions.py` to modify or add descriptions
2. Run `add_descriptions.py` to update the JSON file

## Description Structure

### Table Descriptions

Located in `TABLE_DESCRIPTIONS` dictionary:
- Key: Full table name (e.g., `"cisco_stage_app.qtd_commit_upside"`)
- Value: Description string explaining the table's purpose, usage, and update frequency

### Column Descriptions

Located in `COLUMN_DESCRIPTIONS` dictionary:
- Key: Full table name
- Value: Dictionary mapping column names to description strings

## What to Include in Descriptions

### Table Descriptions Should Include:
1. **Business Purpose**: What the table represents
2. **Data Granularity**: Time period, aggregation level
3. **Key Relationships**: How it relates to other tables
4. **Update Frequency**: How often data is refreshed
5. **Common Use Cases**: Typical queries or analyses

### Column Descriptions Should Include:
1. **Business Meaning**: What the column represents
2. **Data Format/Units**: Currency, percentage, format
3. **Value Constraints**: Valid ranges, special values
4. **Calculation/Formula**: If it's a derived column
5. **Relationships**: Foreign keys, join columns
6. **Business Context**: How it's used in analysis

## Example

```python
# Table description
TABLE_DESCRIPTIONS = {
    "cisco_stage_app.qtd_commit_upside": (
        "Tracks quarterly forecasting metrics including QTD (Quarter-to-Date revenue), "
        "committed forecast revenue, and potential upside revenue..."
    )
}

# Column description
COLUMN_DESCRIPTIONS = {
    "cisco_stage_app.qtd_commit_upside": {
        "qtd": (
            "QTD (Quarter-to-Date) revenue - cumulative revenue from the start of the current quarter "
            "through the specified week. Decimal value in currency units..."
        )
    }
}
```

## Best Practices

1. **Be Concise**: 1-2 sentences for columns, 2-3 for tables
2. **Use Business Language**: Avoid technical jargon when possible
3. **Include Examples**: Reference actual values from the data
4. **Mention Relationships**: Note how tables/columns connect
5. **Clarify Calculations**: Explain derived/computed columns
6. **Note Special Cases**: NULL meanings, edge cases, data quality notes

## Verification

After running the script, verify descriptions were added:

```bash
# Check if descriptions are in the JSON
grep -A 2 '"comment"' cisco_stage_app_clickhouse.json | head -20
```

## Integration with Text-to-SQL

The descriptions are automatically included in the M-Schema string representation when using:

```python
from m_schema import MSchema

mschema = MSchema.load('cisco_stage_app_clickhouse.json')
schema_str = mschema.to_mschema()
# Descriptions will appear in the schema string
```

This improves LLM understanding of the schema for better SQL generation accuracy.

