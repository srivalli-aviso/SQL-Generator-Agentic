"""
Debug script to investigate why filtering returns empty results.
"""

import json
from query_based_schema_filter import QueryBasedSchemaFilter
from embedding_service import EmbeddingService
from vector_store import VectorStore

def debug_filtering():
    """
    Debug the filtering process to see why no tables are being returned.
    """
    print("=" * 80)
    print("Debugging Query-Based Schema Filtering")
    print("=" * 80)
    
    # Initialize
    filter_instance = QueryBasedSchemaFilter(
        schema_path="./cisco_stage_app_modified_m_schema.json",
        vector_db_path="./vector_db"
    )
    
    # Check if embeddings exist
    print("\n1. Checking stored embeddings...")
    stored_tables = filter_instance.vector_store.get_all_tables()
    print(f"   Stored tables: {len(stored_tables)}")
    if stored_tables:
        print(f"   Tables: {stored_tables}")
    else:
        print("   ⚠ No tables found in vector database!")
        print("   Run precompute_embeddings() first.")
        return
    
    # Test query
    test_query = "Show me revenue by region and segment"
    print(f"\n2. Testing query: '{test_query}'")
    
    # Generate query embedding
    query_embedding = filter_instance.embedding_service.embed_text(test_query)
    print(f"   Query embedding dimension: {len(query_embedding)}")
    
    # Search without threshold to see all results
    print("\n3. Searching without threshold (to see all similarities)...")
    results = filter_instance.vector_store.search_similar(
        query_embedding=query_embedding,
        top_k=20,
        threshold=0.0,  # No threshold
        element_type="table"
    )
    
    print(f"   Found {len(results)} table results:")
    for i, result in enumerate(results[:10], 1):
        similarity = result.get('similarity', 0)
        table_name = result['metadata'].get('table_name', 'unknown')
        print(f"   {i}. {table_name}: similarity={similarity:.4f}")
    
    # Test with different thresholds
    print("\n4. Testing with different thresholds...")
    for threshold in [0.0, 0.3, 0.5, 0.7, 0.8]:
        results = filter_instance.vector_store.search_similar(
            query_embedding=query_embedding,
            top_k=10,
            threshold=threshold,
            element_type="table"
        )
        print(f"   Threshold {threshold}: {len(results)} tables found")
    
    # Test the actual filter
    print("\n5. Testing actual filter_schema() with lower threshold...")
    filtered = filter_instance.filter_schema(
        user_query=test_query,
        top_k_tables=10,
        top_k_columns=15,
        similarity_threshold=0.3,  # Lower threshold
        fk_hops=0
    )
    
    print(f"   Result: {len(filtered.get('tables', {}))} tables")
    for table_name in filtered.get('tables', {}).keys():
        print(f"   - {table_name}")

if __name__ == "__main__":
    debug_filtering()

