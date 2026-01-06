# Migration Plan: Using gte-large-en-v1.5 Embedding Model

## Overview
Switch from `all-MiniLM-L6-v2` to `gte-large-en-v1.5` for better embedding quality.

## Model Information
- **Model Name**: `gte-large-en-v1.5` (or `Alibaba-NLP/gte-large-en-v1.5`)
- **Provider**: Alibaba NLP
- **Dimensions**: 1024 (larger than current 384-dim model)
- **Quality**: Higher quality embeddings, better for semantic search
- **Speed**: Slower than MiniLM but still fast
- **Library**: Available through `sentence-transformers`

## Steps to Implement

### Step 1: Verify Model Availability
- [ ] Check if `gte-large-en-v1.5` is available in sentence-transformers
- [ ] Test model loading locally
- [ ] Verify embedding dimensions (should be 1024)

### Step 2: Update Configuration
- [ ] Update `config.py` to use `gte-large-en-v1.5` as default model
- [ ] Update model name in `embedding_service.py` default parameter
- [ ] Update documentation with new model info

### Step 3: Update Embedding Service
- [ ] Modify `EmbeddingService.__init__()` to use new model
- [ ] Update docstrings to mention gte-large-en-v1.5
- [ ] Test that model loads correctly
- [ ] Verify embedding dimensions match (1024)

### Step 4: Update Requirements (if needed)
- [ ] Ensure `sentence-transformers>=2.2.0` is in requirements.txt
- [ ] Verify no additional dependencies needed
- [ ] Test installation

### Step 5: Test and Validate
- [ ] Test embedding generation with sample text
- [ ] Verify batch processing works
- [ ] Check embedding dimensions are correct (1024)
- [ ] Test with actual schema filtering
- [ ] Compare results with previous model

### Step 6: Update Documentation
- [ ] Update README.md with new model information
- [ ] Update example usage if needed
- [ ] Document model specifications (dimensions, speed, quality)

### Step 7: Re-generate Embeddings (if needed)
- [ ] Clear existing embeddings cache
- [ ] Re-run `precompute_embeddings()` with new model
- [ ] Verify new embeddings are stored correctly

## Model Comparison

| Feature | all-MiniLM-L6-v2 | gte-large-en-v1.5 |
|---------|------------------|-------------------|
| Dimensions | 384 | 1024 |
| Speed | Fast | Moderate |
| Quality | Good | Excellent |
| Size | ~80MB | ~1.3GB |
| Use Case | Fast, general purpose | High quality semantic search |

## Potential Issues & Solutions

### Issue 1: Model Download Size
- **Problem**: gte-large-en-v1.5 is ~1.3GB (larger than MiniLM)
- **Solution**: First download may take time, but model is cached

### Issue 2: Memory Usage
- **Problem**: Larger model uses more RAM
- **Solution**: Ensure sufficient memory (recommended: 4GB+ free RAM)

### Issue 3: Slower Initial Load
- **Problem**: Model loading takes longer
- **Solution**: Model is loaded once and cached in memory

### Issue 4: Vector Database Compatibility
- **Problem**: Existing embeddings have different dimensions (384 vs 1024)
- **Solution**: Clear vector database and re-generate embeddings

## Code Changes Required

1. **config.py**: Change default model name
2. **embedding_service.py**: Update default model parameter
3. **README.md**: Update model documentation

## Testing Checklist

- [ ] Model loads without errors
- [ ] Embeddings have correct dimensions (1024)
- [ ] Batch processing works correctly
- [ ] Schema filtering produces good results
- [ ] Performance is acceptable
- [ ] Memory usage is within limits

## Rollback Plan

If issues occur:
1. Revert to `all-MiniLM-L6-v2` in config.py
2. Clear embeddings cache
3. Re-generate embeddings with old model

