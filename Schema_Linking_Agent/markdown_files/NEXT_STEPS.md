# Next Steps After Model Download

## ✅ Completed
- ✓ Model `Alibaba-NLP/gte-large-en-v1.5` downloaded and tested
- ✓ Configuration updated to use the new model
- ✓ Embedding service updated with `trust_remote_code=True` support

## 📋 Next Steps

### Step 1: Clear Old Embeddings (IMPORTANT!)

Since the embedding dimension changed from 384 to 1024, you MUST clear old embeddings:

```bash
cd Schema_Linking_Agent

# Remove old vector database
rm -rf vector_db/

# Remove old embeddings cache
rm -f embeddings_cache.json
```

**Why?** The old embeddings have 384 dimensions, but the new model produces 1024 dimensions. They're incompatible!

### Step 2: Re-generate Embeddings with New Model

Run the example script to generate new embeddings:

```bash
cd Schema_Linking_Agent
python3 example_usage.py
```

Or do it programmatically:

```python
from query_based_schema_filter import QueryBasedSchemaFilter

# Initialize
filter = QueryBasedSchemaFilter(
    schema_path="./cisco_stage_app_modified_m_schema.json",
    vector_db_path="./vector_db"
)

# Force re-compute embeddings with new model
filter.precompute_embeddings(force_recompute=True)
```

This will:
- Generate embeddings for all tables and columns using `gte-large-en-v1.5`
- Store them in the vector database
- Cache them for faster future loads

### Step 3: Test Query-Based Filtering

Test with a sample query:

```python
# Filter schema based on query
filtered = filter.filter_schema(
    user_query="Show me revenue by region and segment",
    top_k_tables=10,
    top_k_columns=15,
    similarity_threshold=0.7,
    fk_hops=1
)

# Check results
print(f"Selected {len(filtered['tables'])} tables")
for table_name in filtered['tables'].keys():
    print(f"  - {table_name}")
```

### Step 4: Verify Everything Works

Run the full example:

```bash
python3 example_usage.py
```

Expected output:
- Model loads successfully
- Embeddings generated (1024 dimensions)
- Schema filtering works
- Results saved to JSON files

## 🔍 Troubleshooting

### If you get dimension mismatch errors:
- Make sure you cleared the old vector_db and cache
- Re-run `precompute_embeddings(force_recompute=True)`

### If model loading is slow:
- First load downloads the model (~1.3GB)
- Subsequent loads are much faster (model is cached)

### If you get memory errors:
- The model uses ~2-4GB RAM
- Close other applications if needed
- Consider using a smaller model if memory is limited

## 📊 Model Comparison

| Aspect | Old (MiniLM) | New (GTE-Large) |
|--------|--------------|-----------------|
| Dimensions | 384 | 1024 |
| Quality | Good | Excellent |
| Speed | Fast | Moderate |
| Memory | ~500MB | ~2-4GB |
| Best For | Fast filtering | High-quality semantic search |

## ✅ Checklist

- [ ] Cleared old vector_db and embeddings_cache.json
- [ ] Re-generated embeddings with new model
- [ ] Tested query filtering
- [ ] Verified results are correct
- [ ] Updated any documentation if needed

## 🚀 You're Ready!

Once embeddings are re-generated, you can start using the query-based schema filtering with the high-quality GTE model!

