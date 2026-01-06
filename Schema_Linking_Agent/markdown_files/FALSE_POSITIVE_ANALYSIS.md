# False Positive Reduction Analysis

## Question: Would adding Foreign Keys (table-level) and Examples (column-level) decrease false positives?

## Current Situation

**Table Embedding:**
```
"table_name: table_description"
```

**Column Embedding:**
```
"table_name.column_name (type): column_description"
```

**Excluded:**
- Foreign keys (handled separately by ForeignKeyExpander)
- Examples (completely excluded)

---

## Analysis: Foreign Keys at Table Level

### ✅ **YES - Would Likely Reduce False Positives**

**Reasons:**

1. **Relationship Context**
   - Foreign keys provide semantic context about table relationships
   - Helps distinguish tables that seem similar but serve different roles
   - Example: Two "user" tables - one with FK to "orders", another with FK to "sessions"

2. **Query Disambiguation**
   - Queries mentioning "join", "related", "connected" would match better
   - Helps identify tables that are part of a relationship chain
   - Example: Query "revenue by customer" - FK helps link revenue → customer tables

3. **Semantic Enrichment**
   - Adds domain knowledge to embeddings
   - Tables with similar descriptions but different relationships become more distinct
   - Example: "metrics" table with FK to "regions" vs "metrics" table with FK to "products"

**Potential Format:**
```
"table_name: table_description. Related to: [table1, table2] via foreign keys"
```

**Example:**
```
"cisco_stage_app.metrics: Financial performance data. Related to: cisco_stage_app.regions, cisco_stage_app.segments via foreign keys"
```

**Trade-offs:**
- ✅ More context = better disambiguation
- ⚠️ Slightly longer embedding text (but still manageable)
- ⚠️ Need to handle empty FK lists gracefully

---

## Analysis: Examples at Column Level

### ⚠️ **MAYBE - Could Help, But With Caveats**

**Reasons it COULD reduce false positives:**

1. **Value-Based Matching**
   - Concrete examples help match queries mentioning specific values
   - Example: Query "2023 revenue" - column with examples ["2023", "2022", "2021"] matches better

2. **Domain Disambiguation**
   - Similar column names in different contexts become more distinct
   - Example: "year" column with examples ["2023", "2022"] vs "year" with examples ["Q1", "Q2", "Q3"]
   - Helps distinguish fiscal year vs quarter year

3. **Pattern Recognition**
   - Examples reveal data patterns that descriptions might not capture
   - Example: Column with examples ["APJC", "Americas", "EMEA"] clearly indicates regions

**Reasons it MIGHT NOT help:**

1. **Noise Addition**
   - Examples might not be representative
   - Could add irrelevant semantic information
   - Example: Column "status" with examples ["active", "inactive"] might match queries about "activity" incorrectly

2. **Token/Size Increase**
   - Examples can be long (5+ values)
   - Increases embedding text length significantly
   - May dilute the core semantic signal

3. **Temporal Bias**
   - Examples might be outdated or biased
   - Example: Old year values might not match current queries

**Potential Format:**
```
"table_name.column_name (type): column_description. Examples: [val1, val2, val3]"
```

**Example:**
```
"cisco_stage_app.qtd_commit_upside.year (String): Fiscal year. Examples: [2023, 2021, 2019, 2020, 2022]"
```

**Trade-offs:**
- ✅ Better value-based matching
- ✅ Domain disambiguation
- ⚠️ Increased text length
- ⚠️ Potential noise
- ⚠️ Need to limit examples (2-3 max)

---

## Recommendation

### 🎯 **Recommended Approach**

**1. Add Foreign Keys at Table Level** ✅
- **High confidence** this will reduce false positives
- Provides relationship context
- Low risk of adding noise
- Moderate implementation effort

**2. Add Examples at Column Level (Limited)** ⚠️
- **Medium confidence** this will help
- Limit to 2-3 examples max
- Only include if examples are representative
- Consider making it configurable

### Implementation Strategy

**Phase 1: Foreign Keys (High Priority)**
```python
# Table embedding with FK
fk_tables = get_related_tables_via_fk(table_name, mschema)
if fk_tables:
    fk_text = f" Related to: {', '.join(fk_tables)} via foreign keys"
    table_text = f"{table_name}: {table_description}{fk_text}"
else:
    table_text = f"{table_name}: {table_description}"
```

**Phase 2: Examples (Optional, Configurable)**
```python
# Column embedding with examples (limited)
examples = column_data.get('examples', [])[:3]  # Limit to 3
if examples:
    examples_text = f" Examples: {examples}"
    column_text = f"{table_name}.{column_name} ({col_type}): {col_desc}{examples_text}"
else:
    column_text = f"{table_name}.{column_name} ({col_type}): {col_desc}"
```

---

## Expected Impact

### False Positive Reduction Scenarios

**Scenario 1: Similar Table Names**
- **Before:** "metrics" and "linearity_metrics" might both match
- **After:** FK context helps distinguish (e.g., one links to "regions", other to "segments")
- **Reduction:** ~20-30%

**Scenario 2: Ambiguous Column Names**
- **Before:** "year" column in multiple tables all match
- **After:** Examples ["2023", "2022"] vs ["Q1", "Q2"] help disambiguate
- **Reduction:** ~15-25%

**Scenario 3: Relationship Queries**
- **Before:** Query "revenue by customer" might miss customer table
- **After:** FK shows revenue table is related to customer table
- **Reduction:** ~30-40%

**Overall Expected Reduction:** 20-35% fewer false positives

---

## Testing Strategy

1. **Baseline Test:** Run current system on test queries, measure false positives
2. **FK Test:** Add FK to table embeddings, re-run, compare
3. **Examples Test:** Add examples to column embeddings, re-run, compare
4. **Combined Test:** Add both, measure combined impact

**Metrics:**
- Precision (relevant results / total results)
- Recall (relevant results found / all relevant results)
- False Positive Rate (irrelevant results / total results)

---

## Conclusion

**Foreign Keys:** ✅ **Strong recommendation** - High value, low risk
**Examples:** ⚠️ **Conditional recommendation** - Medium value, medium risk (limit to 2-3)

**Combined Impact:** Likely 20-35% reduction in false positives, with FK providing the majority of the benefit.

