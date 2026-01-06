# Query-Based Schema Filtering

A semantic search-based system for filtering large M-Schema databases to only relevant tables and columns based on user queries. Uses Groq embeddings and ChromaDB vector database for efficient similarity search.

## Features

- **Semantic Search**: Uses embeddings to find relevant tables/columns based on query meaning
- **Vector Database**: Fast similarity search using ChromaDB
- **Foreign Key Expansion**: Automatically includes related tables via foreign keys (configurable hops)
- **Pre-computed Embeddings**: Hybrid strategy - pre-compute once, update incrementally
- **Configurable Filtering**: Top-K tables/columns + similarity threshold

## Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

**Note:** Groq doesn't provide an embeddings API, so we use sentence-transformers (local embedding model) which runs on your machine. No API key is needed for embeddings. The model will be downloaded automatically on first use.

## Quick Start

```python
from query_based_schema_filter import QueryBasedSchemaFilter

# Initialize
filter = QueryBasedSchemaFilter(
    schema_path="./cisco_stage_app_modified_m_schema.json",
    vector_db_path="./vector_db"
)

# Pre-compute embeddings (first time only)
filter.precompute_embeddings(force_recompute=False)

# Filter schema based on query
user_query = "Show me revenue by region and segment"
filtered_schema = filter.filter_schema(
    user_query=user_query,
    top_k_tables=15,
    top_k_columns=20,
    similarity_threshold=0.7,
    fk_hops=1
)

# Use filtered schema
import json
mschema_str = json.dumps(filtered_schema, indent=2)
```

## Architecture

### Modules

1. **embedding_service.py** - Groq API wrapper for generating embeddings
2. **vector_store.py** - ChromaDB interface for storing/querying embeddings
3. **schema_embedder.py** - Converts M-Schema to embeddings
4. **query_filter.py** - Semantic search and filtering logic
5. **foreign_key_expander.py** - Traverses FK relationships (configurable hops)
6. **query_based_schema_filter.py** - Main orchestrator class

## Usage Examples

### Basic Filtering

```python
from query_based_schema_filter import QueryBasedSchemaFilter

filter = QueryBasedSchemaFilter("./schema.json")
filter.precompute_embeddings()

# Filter with default settings
filtered = filter.filter_schema("revenue by region")
```

### Custom Filtering Parameters

```python
filtered = filter.filter_schema(
    user_query="Show quarterly metrics",
    top_k_tables=10,           # Max 10 tables
    top_k_columns=15,          # Max 15 columns per table
    similarity_threshold=0.75,  # Higher threshold = more strict
    fk_hops=2                  # Include tables 2 hops away via FKs
)
```

### Update Embeddings

```python
# Update all embeddings
filter.update_embeddings()

# Update specific table
filter.update_embeddings(table_name="revenue_table")
```

### Get Statistics

```python
stats = filter.get_statistics()
print(f"Tables: {stats['num_tables']}")
print(f"Columns: {stats['num_columns']}")
print(f"Stored Tables: {stats['stored_tables']}")
```

## Configuration

Edit `config.py` to customize default settings:

```python
class FilterConfig:
    default_top_k_tables: int = 15
    default_top_k_columns: int = 20
    default_similarity_threshold: float = 0.7
    default_fk_hops: int = 1
    embedding_model: str = "nomic-embed-text-v1"
```

## How It Works

1. **Pre-computation**: Generates embeddings for all tables and columns
2. **Storage**: Stores embeddings in ChromaDB vector database
3. **Query Processing**: 
   - Embeds user query
   - Searches for similar tables/columns
   - Filters by threshold and top-K
4. **FK Expansion**: Includes related tables via foreign keys
5. **Schema Building**: Constructs filtered M-Schema with selected elements

## File Structure

```
Schema_Linking_Agent/
├── embedding_service.py          # Groq embedding wrapper
├── vector_store.py               # ChromaDB interface
├── schema_embedder.py           # Schema → embeddings
├── query_filter.py              # Query-based filtering
├── foreign_key_expander.py      # FK traversal
├── query_based_schema_filter.py # Main class
├── config.py                    # Configuration
├── example_usage.py            # Usage examples
├── requirements.txt            # Dependencies
└── README.md                   # This file
```

## Performance

- **Pre-computation**: ~1-2 seconds per table (depends on API rate limits)
- **Query Filtering**: ~100-500ms per query
- **Storage**: ~1-5MB per 100 tables (depends on embedding dimensions)

## Troubleshooting

### "sentence-transformers not installed"
```bash
pip install sentence-transformers
```

### Model download issues
The embedding model will be downloaded automatically on first use. If you have network issues, you can manually download models from HuggingFace.

**Note:** This system uses sentence-transformers (local embeddings) because Groq doesn't provide an embeddings API. No API key is needed for embeddings.

### "Vector store not initialized"
Make sure to call `precompute_embeddings()` before filtering.

### Low similarity scores
- Lower the `similarity_threshold` (e.g., 0.6 instead of 0.7)
- Increase `top_k_tables` and `top_k_columns`
- Check if embeddings were generated correctly

## License

Same as parent project.

