"""
Example Usage Script

Demonstrates how to use the Query-Based Schema Filter to filter
M-Schema based on user queries.
"""

import json
import os
from query_based_schema_filter import QueryBasedSchemaFilter


def main():
    """
    Main function demonstrating query-based schema filtering.
    
    This example:
    1. Initializes the filter with the M-Schema
    2. Pre-computes embeddings (first time only)
    3. Filters schema based on a user query
    4. Saves the filtered schema to a file
    """
    # Initialize the filter
    print("=" * 80)
    print("Query-Based Schema Filter - Example Usage")
    print("=" * 80)
    
    filter_instance = QueryBasedSchemaFilter(
        schema_path="./cisco_stage_app_modified_m_schema.json",
        vector_db_path="./vector_db",
        embedding_cache_path="./embeddings_cache.json"
    )
    
    # Get statistics
    stats = filter_instance.get_statistics()
    print(f"\nSchema Statistics:")
    print(f"  Tables: {stats['num_tables']}")
    print(f"  Columns: {stats['num_columns']}")
    print(f"  Foreign Keys: {stats['num_foreign_keys']}")
    
    # Pre-compute embeddings (first time or when schema changes)
    print("\n" + "=" * 80)
    print("Pre-computing Embeddings")
    print("=" * 80)
    filter_instance.precompute_embeddings(force_recompute=False)
    
    # Create results directory if it doesn't exist
    results_dir = "./results"
    os.makedirs(results_dir, exist_ok=True)
    
    # Example queries
    queries = [
        "Show me revenue by region and segment",
        "What are the conversion rates and close rates?",
        "Display quarterly financial metrics",
        "Show me data about business units and segments",
        "Find won amount and QTD by year and quarter",
        "Show me upside potential and committed revenue by region",
        "What are the linearity metrics for different segments?",
        "Display funnel metrics with conversion percentages",
        "Show revenue performance by technical business unit",
        "Find metrics broken down by month and week"
    ]
    
    # Filter schema for each query
    for i, user_query in enumerate(queries, 1):
        print("\n" + "=" * 80)
        print(f"Query {i}: {user_query}")
        print("=" * 80)
        
        filtered_schema = filter_instance.filter_schema(
            user_query=user_query,
            top_k_tables=10,
            top_k_columns=15,
            similarity_threshold=0.5,
            fk_hops=1
        )
        
        # Display results
        num_tables = len(filtered_schema.get("tables", {}))
        total_columns = sum(
            len(t.get("fields", {})) 
            for t in filtered_schema.get("tables", {}).values()
        )
        
        print(f"\nFiltered Schema Results:")
        print(f"  Selected Tables: {num_tables}")
        print(f"  Total Columns: {total_columns}")
        print(f"  Foreign Keys: {len(filtered_schema.get('foreign_keys', []))}")
        
        print(f"\nSelected Tables:")
        for table_name in filtered_schema.get("tables", {}).keys():
            num_cols = len(filtered_schema["tables"][table_name].get("fields", {}))
            print(f"  - {table_name} ({num_cols} columns)")
        
        # Save filtered schema to results folder
        output_file = os.path.join(results_dir, f"filtered_schema_query_{i}.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(filtered_schema, f, indent=2, ensure_ascii=False)
        print(f"\n✓ Filtered schema saved to: {output_file}")
    
    print("\n" + "=" * 80)
    print("Example Complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()

