# Query-Based Schema Filtering Implementation Plan

## Overview
Implement semantic search-based schema filtering using Groq embeddings, vector database, and foreign key traversal to reduce M-Schema size for LLM prompts.

## Architecture Components

### 1. **Embedding Service Module** (`embedding_service.py`)
   - **Purpose**: Generate embeddings using Groq API
   - **Functions**:
     - `embed_text(text: str) -> List[float]`: Generate embedding for single text
     - `embed_batch(texts: List[str]) -> List[List[float]]`: Batch embedding generation
     - `embed_schema_element(element: dict) -> dict`: Embed table/column with metadata
   - **Dependencies**: Groq API client

### 2. **Vector Database Module** (`vector_store.py`)
   - **Purpose**: Store and query embeddings
   - **Functions**:
     - `initialize_store()`: Initialize vector database connection
     - `store_embeddings(embeddings: List[dict])`: Store table/column embeddings
     - `search_similar(query_embedding: List[float], top_k: int, threshold: float) -> List[dict]`: Search similar elements
     - `update_embeddings(table_name: str, embeddings: dict)`: Update specific table embeddings
     - `get_all_tables() -> List[str]`: Get all stored table names
   - **Vector DB Options**: Chroma (local, easy setup) or Pinecone (cloud, scalable)
   - **Metadata Storage**: Store table_name, column_name, element_type (table/column), description

### 3. **Schema Embedding Generator** (`schema_embedder.py`)
   - **Purpose**: Generate embeddings for entire M-Schema
   - **Functions**:
     - `load_schema(json_path: str) -> dict`: Load M-Schema JSON
     - `extract_embeddable_text(table: dict, column: dict = None) -> str`: Create text representation for embedding
     - `embed_full_schema(mschema: dict) -> List[dict]`: Generate embeddings for all tables/columns
     - `save_embeddings(embeddings: List[dict], output_path: str)`: Save embeddings to disk (for caching)
   - **Embedding Strategy**:
     - **Table-level**: `table_name + table_description`
     - **Column-level**: `table_name + column_name + column_description + column_type`
     - **Full schema context**: Embed entire table structure as one text block

### 4. **Query-Based Filter** (`query_filter.py`)
   - **Purpose**: Filter schema based on user query
   - **Functions**:
     - `filter_by_query(user_query: str, top_k_tables: int, top_k_columns: int, similarity_threshold: float) -> dict`
     - `get_relevant_tables(query_embedding: List[float], top_k: int, threshold: float) -> List[str]`
     - `get_relevant_columns(table_name: str, query_embedding: List[float], top_k: int, threshold: float) -> List[str]`
     - `build_filtered_schema(selected_tables: List[str], selected_columns: dict) -> dict`

### 5. **Foreign Key Traversal** (`foreign_key_expander.py`)
   - **Purpose**: Include related tables via foreign keys
   - **Functions**:
     - `get_related_tables(table_names: List[str], max_hops: int, mschema: dict) -> Set[str]`
     - `traverse_foreign_keys(table: str, visited: Set, mschema: dict, current_hop: int, max_hops: int) -> Set[str]`
     - `expand_with_foreign_keys(selected_tables: List[str], mschema: dict, max_hops: int) -> List[str]`

### 6. **Main Schema Filtering Class** (`query_based_schema_filter.py`)
   - **Purpose**: Main orchestrator class
   - **Class**: `QueryBasedSchemaFilter`
   - **Methods**:
     - `__init__(schema_path: str, vector_db_path: str, embedding_service: EmbeddingService)`
     - `precompute_embeddings(force_recompute: bool = False)`: Pre-compute and store embeddings
     - `filter_schema(user_query: str, top_k_tables: int = 15, top_k_columns: int = 20, similarity_threshold: float = 0.7, fk_hops: int = 1) -> dict`
     - `update_embeddings(table_name: str = None)`: Update embeddings for changed tables
     - `get_statistics() -> dict`: Get filtering statistics

## Implementation Steps

### Phase 1: Setup & Infrastructure (Steps 1-3)

#### Step 1: Set Up Dependencies
- [ ] Install required packages:
  - `groq` (already installed)
  - `chromadb` or `pinecone-client` (vector database)
  - `numpy` (for similarity calculations)
- [ ] Create `requirements.txt` or update existing one
- [ ] Set up environment variables for Groq API key

#### Step 2: Create Embedding Service
- [ ] Create `embedding_service.py`
- [ ] Implement Groq API client wrapper
- [ ] Add batch processing for efficiency
- [ ] Add error handling and retry logic
- [ ] Add rate limiting if needed

#### Step 3: Set Up Vector Database
- [ ] Choose vector database (recommend Chroma for local dev)
- [ ] Create `vector_store.py`
- [ ] Implement connection and initialization
- [ ] Define schema/metadata structure for stored embeddings
- [ ] Implement CRUD operations (create, read, update, delete)

### Phase 2: Schema Embedding (Steps 4-5)

#### Step 4: Create Schema Embedding Generator
- [ ] Create `schema_embedder.py`
- [ ] Implement text extraction from M-Schema:
  - Table-level text: `"{table_name}: {table_description}"`
  - Column-level text: `"{table_name}.{column_name} ({type}): {column_description}"`
  - Full table context: Combine all table info into one embedding
- [ ] Implement batch embedding generation
- [ ] Add progress tracking for large schemas

#### Step 5: Implement Pre-computation Logic
- [ ] Load M-Schema JSON
- [ ] Generate embeddings for all tables
- [ ] Generate embeddings for all columns
- [ ] Store embeddings in vector database
- [ ] Save embeddings to disk (JSON/pickle) for caching
- [ ] Add timestamp/metadata for periodic updates

### Phase 3: Query Filtering (Steps 6-7)

#### Step 6: Implement Query-Based Filtering
- [ ] Create `query_filter.py`
- [ ] Implement query embedding generation
- [ ] Implement similarity search:
  - Search for top-K tables
  - For each selected table, search for top-K columns
  - Apply similarity threshold filtering
- [ ] Combine top-K and threshold criteria
- [ ] Build filtered M-Schema structure

#### Step 7: Implement Foreign Key Expansion
- [ ] Create `foreign_key_expander.py`
- [ ] Parse foreign keys from M-Schema
- [ ] Implement graph traversal (BFS/DFS) for foreign key relationships
- [ ] Add configurable hop limit (1-hop, 2-hop, etc.)
- [ ] Merge related tables into filtered schema

### Phase 4: Main Integration (Steps 8-9)

#### Step 8: Create Main Filtering Class
- [ ] Create `query_based_schema_filter.py`
- [ ] Integrate all components:
  - Embedding service
  - Vector store
  - Schema embedder
  - Query filter
  - Foreign key expander
- [ ] Implement main `filter_schema()` method
- [ ] Add configuration options (top_k, threshold, hops)
- [ ] Add error handling and logging

#### Step 9: Add Update Mechanism
- [ ] Implement periodic update detection
- [ ] Add method to update embeddings for changed tables
- [ ] Add incremental update support
- [ ] Add full schema re-embedding option

### Phase 5: Testing & Optimization (Steps 10-11)

#### Step 10: Create Test Suite
- [ ] Unit tests for each module
- [ ] Integration tests for full pipeline
- [ ] Test with sample queries
- [ ] Test with different schema sizes
- [ ] Performance benchmarking

#### Step 11: Optimization & Documentation
- [ ] Optimize batch processing
- [ ] Add caching mechanisms
- [ ] Add logging and monitoring
- [ ] Create usage examples
- [ ] Write documentation

## File Structure

```
Schema_Linking_Agent/
├── query_based_schema_filter.py    # Main class
├── embedding_service.py              # Groq embedding wrapper
├── vector_store.py                  # Vector database interface
├── schema_embedder.py               # Schema → embeddings
├── query_filter.py                  # Query-based filtering
├── foreign_key_expander.py          # FK traversal
├── config.py                        # Configuration
├── utils.py                         # Helper functions
└── tests/
    ├── test_embedding_service.py
    ├── test_vector_store.py
    ├── test_query_filter.py
    └── test_integration.py
```

## Configuration Options

```python
class FilterConfig:
    # Embedding
    embedding_model: str = "groq"  # or specific model name
    batch_size: int = 100
    
    # Vector Database
    vector_db_type: str = "chroma"  # or "pinecone"
    vector_db_path: str = "./vector_db"
    collection_name: str = "schema_embeddings"
    
    # Filtering
    default_top_k_tables: int = 15
    default_top_k_columns: int = 20
    default_similarity_threshold: float = 0.7
    default_fk_hops: int = 1
    
    # Update Strategy
    update_on_schema_change: bool = True
    periodic_update_interval: int = 86400  # seconds (24 hours)
```

## Usage Example

```python
from query_based_schema_filter import QueryBasedSchemaFilter

# Initialize
filter = QueryBasedSchemaFilter(
    schema_path="./cisco_stage_app_modified_m_schema.json",
    vector_db_path="./vector_db"
)

# Pre-compute embeddings (first time or when schema changes)
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

# Use filtered schema in LLM prompt
mschema_str = json.dumps(filtered_schema, indent=2)
```

## Key Design Decisions

1. **Embedding Strategy**: Embed entire table structure as one block (table + all columns) for better context
2. **Vector DB Choice**: Start with Chroma (local, easy), can migrate to Pinecone later
3. **Update Strategy**: Hybrid - pre-compute on first run, update incrementally when schema changes
4. **Similarity Search**: Combine top-K and threshold - must meet threshold AND be in top-K
5. **Foreign Keys**: Configurable hops, default 1-hop (directly connected tables)
6. **Caching**: Store embeddings on disk for faster subsequent loads

## Performance Considerations

- **Batch Processing**: Process embeddings in batches to optimize API calls
- **Caching**: Cache embeddings on disk to avoid re-computation
- **Incremental Updates**: Only re-embed changed tables/columns
- **Parallel Processing**: Consider parallel embedding generation for large schemas
- **Vector DB Indexing**: Ensure proper indexing for fast similarity search

## Next Steps After Implementation

1. Add evaluation metrics (precision, recall for relevant tables/columns)
2. Add query expansion (synonyms, related terms)
3. Add user feedback loop (learn from corrections)
4. Optimize for production (scaling, monitoring)

