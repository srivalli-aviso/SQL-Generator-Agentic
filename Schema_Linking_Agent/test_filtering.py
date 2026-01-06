"""
Simple test script to verify filtering works correctly.
"""

import json
from query_based_schema_filter import QueryBasedSchemaFilter

# Initialize
print("Initializing filter...")
filter_instance = QueryBasedSchemaFilter(
    schema_path="./cisco_stage_app_modified_m_schema.json",
    vector_db_path="./vector_db"
)

# Check if embeddings exist
print("\nChecking stored tables...")
tables = filter_instance.vector_store.get_all_tables()
print(f"Found {len(tables)} tables in vector database")

if not tables:
    print("\n⚠ No embeddings found. Running precompute_embeddings()...")
    filter_instance.precompute_embeddings(force_recompute=True)
    tables = filter_instance.vector_store.get_all_tables()
    print(f"Now found {len(tables)} tables")

# Test with a simple query and very low threshold
print("\n" + "=" * 60)
print("Testing filter with query: 'revenue'")
print("=" * 60)

filtered = filter_instance.filter_schema(
    user_query="revenue",
    top_k_tables=10,
    top_k_columns=15,
    similarity_threshold=0.1,  # Very low threshold to see if anything matches
    fk_hops=0
)

print(f"\nResults:")
print(f"  Tables found: {len(filtered.get('tables', {}))}")
print(f"  Table names: {list(filtered.get('tables', {}).keys())}")

if filtered.get('tables'):
    for table_name, table_data in filtered['tables'].items():
        cols = table_data.get('fields', {})
        print(f"  - {table_name}: {len(cols)} columns")
        if cols:
            print(f"    Columns: {list(cols.keys())[:5]}...")
else:
    print("\n⚠ No tables found even with threshold 0.1!")
    print("This suggests embeddings might not be matching. Checking raw search...")
    
    # Test raw search
    query_emb = filter_instance.embedding_service.embed_text("revenue")
    results = filter_instance.vector_store.search_similar(
        query_embedding=query_emb,
        top_k=5,
        threshold=0.0,  # No threshold
        element_type="table"
    )
    
    print(f"\nRaw search results (no threshold): {len(results)}")
    for i, r in enumerate(results[:5], 1):
        print(f"  {i}. {r['metadata'].get('table_name')}: similarity={r.get('similarity', 0):.4f}, distance={r.get('distance', 0):.4f}")

