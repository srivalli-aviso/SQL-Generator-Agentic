# Reranker Implementation Plan for Schema Linking Agent

## Overview

Add a two-stage retrieval system: Vector Search → Reranker → Final Results
- **Stage 1**: Fast vector search (existing)
- **Stage 2**: Accurate reranking with cross-encoder (new)
- **Fallback**: LLM-based reranker for validation (optional, not default)

## Architecture

```
User Query
    ↓
Vector Search (ChromaDB)
    ↓
Top-K Candidates (e.g., top 20 tables, top 30 columns)
    ↓
Cross-Encoder Reranker (BAAI/bge-reranker-base)
    ↓
Reranked Results (e.g., top 10 tables, top 15 columns)
    ↓
[Optional] LLM-based Validation (Groq API)
    ↓
Final Results with Reranker Scores
```

## Components

### 1. Reranker Module (`reranker.py`)

**Class: `Reranker`**

**Key Methods:**
- `__init__(model: str, enable_llm_fallback: bool)`
- `rerank_tables(query: str, candidates: List[Dict], top_k: int) -> List[Dict]`
- `rerank_columns(query: str, table_name: str, candidates: List[Dict], top_k: int) -> List[Dict]`
- `_rerank_with_cross_encoder(query: str, candidates: List[Dict]) -> List[Dict]`
- `_rerank_with_llm(query: str, candidates: List[Dict]) -> List[Dict]` (fallback)

### 2. Integration Points

**Modify `query_filter.py`:**
- Add reranker to `QueryFilter.__init__()`
- Integrate reranking in `get_relevant_tables()` and `get_relevant_columns()`
- Add reranker scores to metadata

**Modify `config.py`:**
- Add reranker configuration options
- Enable/disable reranker flag
- Reranker model selection
- LLM fallback configuration

### 3. Configuration

```python
# config.py additions
reranker_enabled: bool = True  # Enable reranker (on by default)
reranker_model: str = "BAAI/bge-reranker-base"  # Cross-encoder model
reranker_top_k_initial: int = 20  # Initial candidates from vector search
reranker_top_k_final: int = 10  # Final results after reranking
enable_llm_validation: bool = False  # LLM-based validation (off by default)
llm_validation_threshold: float = 0.7  # Only validate if confidence < threshold
```

## Implementation Details

### Stage 1: Vector Search (Existing)
- Returns top-K candidates (e.g., top 20 tables, top 30 columns)
- Uses similarity threshold (0.5)

### Stage 2: Cross-Encoder Reranker (New)
- Takes query + candidates
- Scores each candidate with cross-encoder
- Returns reranked top-K results
- Adds reranker_score to metadata

### Stage 3: LLM Validation (Optional Fallback)
- Only used if cross-encoder fails or confidence is low
- Uses Groq API to validate/rerank
- Not enabled by default

## File Structure

```
Schema_Linking_Agent/
├── reranker.py              # New: Reranker module
├── query_filter.py          # Modified: Add reranking integration
├── config.py                # Modified: Add reranker config
├── requirements.txt         # Modified: Add reranker dependencies
└── ...
```

## Dependencies

```python
# requirements.txt additions
sentence-transformers>=2.2.0  # Already have this
torch>=2.0.0                   # Already have this
# No new dependencies needed - BAAI/bge-reranker-base uses sentence-transformers
```

## Output Format Changes

**Before:**
```json
{
  "id": "table_1",
  "similarity": 0.85,
  "metadata": {"table_name": "metrics", ...}
}
```

**After:**
```json
{
  "id": "table_1",
  "similarity": 0.85,
  "reranker_score": 0.92,  # New: Reranker score
  "metadata": {
    "table_name": "metrics",
    "reranker_score": 0.92,  # Also in metadata
    ...
  }
}
```

## Performance Considerations

- **Latency**: Cross-encoder adds ~50-200ms per rerank call
- **Caching**: Cache reranker model (load once)
- **Batch Processing**: Rerank multiple candidates in batch
- **Fallback**: LLM validation only when needed (not default)

## Testing Strategy

1. Test with existing 10 queries
2. Compare results with/without reranker
3. Measure accuracy improvement
4. Measure latency impact
5. Test fallback mechanism

## Implementation Steps

1. Create `reranker.py` module
2. Add reranker configuration to `config.py`
3. Integrate reranker into `query_filter.py`
4. Update `requirements.txt` (if needed)
5. Test with example queries
6. Measure performance impact
7. Document usage

