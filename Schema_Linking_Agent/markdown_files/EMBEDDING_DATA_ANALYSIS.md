# M-Schema Embedding Data Analysis

This document shows what data from M-Schema gets embedded vs what's stored separately vs what's excluded.

## 📊 Table-Level Data

### M-Schema Structure (Full Data Available)
```json
{
  "cisco_stage_app.qtd_commit_upside": {
    "fields": { ... },
    "examples": [],
    "table_description": "This table stores quarterly, monthly and weekly financial metrics..."
  }
}
```

### ✅ EMBEDDED (in embedding text)
**Format:** `"table_name: table_description"`

**Example:**
```
"cisco_stage_app.qtd_commit_upside: This table stores quarterly, monthly and weekly financial metrics (QTD, committed forecast and upside potential) broken down by geographic region and Cisco business segment. It is used for tracking revenue performance and forecasting at a granular time level."
```

**Included:**
- ✅ `table_name` (full name with schema)
- ✅ `table_description`

### ✅ STORED IN METADATA (not embedded, but available in vector DB)
```json
{
  "table_name": "cisco_stage_app.qtd_commit_upside",
  "table_description": "This table stores quarterly, monthly and weekly financial metrics..."
}
```

### ❌ NOT STORED ANYWHERE (completely excluded)
- ❌ `examples` (array)
- ❌ `fields` (columns are processed separately)

---

## 📊 Column-Level Data

### M-Schema Structure (Full Data Available)
```json
{
  "year": {
    "type": "String",
    "primary_key": true,
    "nullable": false,
    "default": "' '",
    "autoincrement": false,
    "examples": ["2023", "2021", "2019", "2020", "2022"],
    "column_description": "Fiscal year for which the financial figures are reported."
  }
}
```

### ✅ EMBEDDED (in embedding text)
**Format:** `"table_name.column_name (type): column_description"`

**Example:**
```
"cisco_stage_app.qtd_commit_upside.year (String): Fiscal year for which the financial figures are reported."
```

**Included:**
- ✅ `table_name` (full name with schema)
- ✅ `column_name`
- ✅ `type` (data type)
- ✅ `column_description`

### ✅ STORED IN METADATA (not embedded, but available in vector DB)
```json
{
  "table_name": "cisco_stage_app.qtd_commit_upside",
  "column_name": "year",
  "type": "String",
  "column_description": "Fiscal year for which the financial figures are reported.",
  "primary_key": true
}
```

**Included:**
- ✅ `table_name`
- ✅ `column_name`
- ✅ `type`
- ✅ `column_description`
- ✅ `primary_key` (boolean)

### ❌ NOT STORED ANYWHERE (completely excluded)
- ❌ `nullable` (boolean)
- ❌ `default` (string)
- ❌ `autoincrement` (boolean)
- ❌ `examples` (array of example values)

---

## 📊 Schema-Level Data

### M-Schema Structure (Full Data Available)
```json
{
  "db_id": "cisco_stage_app",
  "schema": "cisco_stage_app",
  "tables": { ... },
  "foreign_keys": []
}
```

### ❌ NOT STORED ANYWHERE (completely excluded)
- ❌ `db_id` (database identifier)
- ❌ `schema` (schema name)
- ❌ `foreign_keys` (foreign key relationships - handled separately by ForeignKeyExpander)

---

## 📦 Complete Embedding Structure

### Table Embedding Object
```json
{
  "embedding": [0.123, -0.456, ...],  // 1024 floats (gte-large-en-v1.5)
  "element_type": "table",
  "table_name": "cisco_stage_app.qtd_commit_upside",
  "column_name": null,
  "description": "This table stores quarterly, monthly and weekly financial metrics...",
  "metadata": {
    "table_name": "cisco_stage_app.qtd_commit_upside",
    "table_description": "This table stores quarterly, monthly and weekly financial metrics..."
  }
}
```

### Column Embedding Object
```json
{
  "embedding": [0.789, -0.234, ...],  // 1024 floats (gte-large-en-v1.5)
  "element_type": "column",
  "table_name": "cisco_stage_app.qtd_commit_upside",
  "column_name": "year",
  "description": "Fiscal year for which the financial figures are reported.",
  "metadata": {
    "table_name": "cisco_stage_app.qtd_commit_upside",
    "column_name": "year",
    "type": "String",
    "column_description": "Fiscal year for which the financial figures are reported.",
    "primary_key": true
  }
}
```

---

## 📋 Summary Table

| Data Field | Embedded? | In Metadata? | Excluded? | Notes |
|------------|-----------|--------------|-----------|-------|
| **Table Level** |
| `table_name` | ✅ | ✅ | ❌ | Full name with schema |
| `table_description` | ✅ | ✅ | ❌ | Used in embedding text |
| `examples` | ❌ | ❌ | ✅ | Not used |
| **Column Level** |
| `table_name` | ✅ | ✅ | ❌ | Included in embedding text |
| `column_name` | ✅ | ✅ | ❌ | Included in embedding text |
| `type` | ✅ | ✅ | ❌ | Included in embedding text |
| `column_description` | ✅ | ✅ | ❌ | Used in embedding text |
| `primary_key` | ❌ | ✅ | ❌ | Only in metadata |
| `nullable` | ❌ | ❌ | ✅ | Not stored |
| `default` | ❌ | ❌ | ✅ | Not stored |
| `autoincrement` | ❌ | ❌ | ✅ | Not stored |
| `examples` | ❌ | ❌ | ✅ | Not stored |
| **Schema Level** |
| `db_id` | ❌ | ❌ | ✅ | Not stored |
| `schema` | ❌ | ❌ | ✅ | Not stored |
| `foreign_keys` | ❌ | ❌ | ✅ | Handled separately |

---

## 🔍 Key Insights

1. **Embedding Text is Minimal**: Only includes names, types, and descriptions - the semantic information needed for similarity search.

2. **Metadata is Selective**: Stores key structural information (primary_key) but not all constraints (nullable, default, autoincrement).

3. **Examples are Excluded**: Example values are not embedded or stored, reducing storage but losing sample data information.

4. **Foreign Keys Handled Separately**: Foreign key relationships are not embedded but are processed by the `ForeignKeyExpander` module.

5. **Schema-Level Info Lost**: `db_id` and `schema` are not stored in embeddings, but are preserved in the filtered schema output.

---

## 💡 Potential Improvements

1. **Include Examples in Embedding**: Could add example values to embedding text for better semantic matching:
   ```
   "table.column (type): description. Examples: [val1, val2, val3]"
   ```

2. **Store More Metadata**: Could include `nullable`, `default` in metadata for SQL generation.

3. **Include Foreign Keys in Embedding**: Could embed FK relationships as part of table/column context.

4. **Schema Context**: Could include `db_id` and `schema` in table embeddings for multi-database scenarios.

