# M-Schema Compression Options for Large Databases

When dealing with databases containing 100+ tables and 100s of columns, sending the full M-Schema to an LLM becomes impractical due to token limits and cost. Here are several strategies to make the schema more concise:

## 1. **Query-Based Schema Filtering** ⭐ (Recommended)

**Concept**: Use semantic search/embeddings to identify only relevant tables and columns based on the user query.

**Approach**:
- Embed user query and all table/column descriptions
- Find top-K most similar tables/columns (e.g., top 10-20 tables)
- Include foreign key relationships for selected tables
- Optionally include 1-2 hops of related tables via foreign keys

**Pros**:
- ✅ Dramatically reduces schema size (90-95% reduction)
- ✅ Only relevant information sent to LLM
- ✅ Better accuracy (less noise)
- ✅ Lower token costs

**Cons**:
- ❌ Requires embedding model (OpenAI, Cohere, etc.)
- ❌ May miss related tables if embeddings aren't perfect
- ❌ Additional latency for embedding search

**Implementation**:
```python
def filter_schema_by_query(mschema, user_query, top_k_tables=15, top_k_columns_per_table=20):
    # 1. Embed query and all table/column descriptions
    # 2. Find top-K most relevant tables
    # 3. For each table, find top-K most relevant columns
    # 4. Include foreign keys connecting selected tables
    # 5. Return filtered M-Schema
```

---

## 2. **Schema Summarization**

**Concept**: Create concise summaries instead of full details for tables/columns.

**Approach**:
- **Table-level**: Only include table name + description (skip all columns initially)
- **Column-level**: Only include column name + type + description (skip examples, defaults, nullable flags)
- **Progressive disclosure**: If LLM needs more details, fetch them in follow-up

**Pros**:
- ✅ Simple to implement
- ✅ Reduces size by 60-70%
- ✅ Preserves semantic information

**Cons**:
- ❌ May lose important metadata (primary keys, foreign keys)
- ❌ Examples can be valuable for understanding data

**Compression Levels**:
- **Level 1 (Minimal)**: Table name + description only
- **Level 2 (Medium)**: Table + column names + types + descriptions
- **Level 3 (Full)**: Everything including examples

---

## 3. **Hierarchical/Progressive Schema Disclosure**

**Concept**: Start with high-level overview, expand as needed.

**Approach**:
- **Step 1**: Send only table names + descriptions (no columns)
- **Step 2**: LLM identifies relevant tables
- **Step 3**: Send full details only for selected tables
- **Step 4**: If needed, expand to related tables via foreign keys

**Pros**:
- ✅ Minimal initial token usage
- ✅ Interactive refinement
- ✅ Can handle very large schemas

**Cons**:
- ❌ Requires multiple LLM calls (higher latency)
- ❌ More complex implementation
- ❌ May need conversation context management

---

## 4. **Metadata Pruning**

**Concept**: Remove less critical metadata fields.

**Fields to Remove/Simplify**:
- ❌ `examples` array (or limit to 2-3 examples)
- ❌ `default` values (unless critical)
- ❌ `autoincrement` flag (rarely needed)
- ❌ `nullable` flag (can infer from context)
- ✅ Keep: `type`, `primary_key`, `column_description`, `table_description`

**Pros**:
- ✅ Simple to implement
- ✅ Reduces size by 40-50%
- ✅ Preserves essential information

**Cons**:
- ❌ Examples can help LLM understand data format
- ❌ Some metadata might be needed for accurate SQL

---

## 5. **Table/Column Ranking & Top-K Selection**

**Concept**: Rank tables/columns by importance and include only top-K.

**Ranking Criteria**:
- **Frequency**: Tables/columns used in common queries
- **Centrality**: Tables with many foreign key relationships
- **Recency**: Recently accessed tables
- **User preferences**: Tables marked as important
- **Query similarity**: Semantic similarity to user query

**Pros**:
- ✅ Can combine multiple ranking signals
- ✅ Configurable (top 10, 20, 30 tables)
- ✅ Works well with query-based filtering

**Cons**:
- ❌ Requires tracking usage statistics
- ❌ May miss important but rarely-used tables

---

## 6. **Schema Clustering/Grouping**

**Concept**: Group related tables and send representative tables from each cluster.

**Approach**:
- Cluster tables by:
  - Foreign key relationships
  - Semantic similarity (descriptions)
  - Naming patterns (e.g., `user_*`, `order_*`)
- Send 1-2 representative tables per cluster
- Include cluster summaries

**Pros**:
- ✅ Reduces redundancy
- ✅ Maintains schema structure understanding
- ✅ Good for databases with many similar tables

**Cons**:
- ❌ May miss important tables in large clusters
- ❌ Requires clustering algorithm

---

## 7. **Hybrid Approach** ⭐⭐ (Best for Production)

**Combine multiple strategies**:

```python
def get_concise_schema(mschema, user_query, max_tables=20, max_columns_per_table=15):
    # Step 1: Query-based filtering (semantic search)
    relevant_tables = semantic_search_tables(mschema, user_query, top_k=max_tables)
    
    # Step 2: For each table, filter columns
    for table in relevant_tables:
        relevant_columns = semantic_search_columns(
            mschema.tables[table], 
            user_query, 
            top_k=max_columns_per_table
        )
    
    # Step 3: Include foreign keys for selected tables
    include_related_tables = get_foreign_key_related_tables(relevant_tables)
    
    # Step 4: Metadata pruning
    pruned_schema = prune_metadata(filtered_schema, 
        keep_examples=False,  # Remove examples
        keep_defaults=False,   # Remove defaults
        keep_nullable=False   # Remove nullable flags
    )
    
    # Step 5: Summarize if still too large
    if estimate_tokens(pruned_schema) > MAX_TOKENS:
        pruned_schema = summarize_schema(pruned_schema)
    
    return pruned_schema
```

---

## 8. **Schema Indexing with Retrieval**

**Concept**: Build a searchable index of schema, retrieve on-demand.

**Approach**:
- Pre-compute embeddings for all tables/columns
- Store in vector database (Pinecone, Weaviate, Chroma)
- At query time: retrieve top-K relevant schema elements
- Construct minimal M-Schema from retrieved elements

**Pros**:
- ✅ Fast retrieval (sub-second)
- ✅ Scales to 1000s of tables
- ✅ Can cache common queries

**Cons**:
- ❌ Requires vector database infrastructure
- ❌ Initial setup complexity

---

## Implementation Recommendations

### For Small-Medium Databases (10-50 tables):
- Use **Metadata Pruning** (#4) - simplest, effective

### For Large Databases (50-200 tables):
- Use **Query-Based Filtering** (#1) + **Metadata Pruning** (#4)

### For Very Large Databases (200+ tables):
- Use **Hybrid Approach** (#7) with vector database (#8)

### Quick Win Implementation:
```python
def quick_compress_schema(mschema, max_tables=20, max_examples=2):
    """Quick compression without embeddings"""
    # 1. Limit tables (if too many)
    tables = list(mschema.tables.keys())[:max_tables]
    
    # 2. For each table, limit examples
    compressed = {}
    for table in tables:
        compressed[table] = mschema.tables[table].copy()
        for col in compressed[table]['fields']:
            if 'examples' in compressed[table]['fields'][col]:
                compressed[table]['fields'][col]['examples'] = \
                    compressed[table]['fields'][col]['examples'][:max_examples]
    
    return compressed
```

---

## Token Estimation

To decide which approach to use, estimate token count:

```python
def estimate_tokens(mschema_str):
    # Rough estimate: 1 token ≈ 4 characters
    return len(mschema_str) / 4

# Typical limits:
# - GPT-4: 128K tokens context
# - GPT-3.5: 16K tokens context
# - Claude: 200K tokens context
# - Recommended: Keep schema < 20% of context (e.g., < 25K tokens for GPT-4)
```

---

## Example: Before vs After Compression

**Before (Full Schema)**:
- 100 tables × 50 columns = 5,000 columns
- ~500KB JSON = ~125K tokens
- Too large for most LLMs

**After (Query-Based + Pruning)**:
- 15 relevant tables × 20 columns = 300 columns
- ~50KB JSON = ~12.5K tokens
- ✅ Fits comfortably in context

**Reduction**: 90% smaller, 90% more relevant

