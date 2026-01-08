"""
Example Usage Script for Subproblem Agent

Demonstrates how to use the Subproblem Agent to decompose queries
into clause-wise subproblems using filtered schemas from Schema Linking Agent.
"""

import json
import os
import sys

# Add Schema_Linking_Agent to path to import modules
schema_linking_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'Schema_Linking_Agent'
)
sys.path.insert(0, os.path.abspath(schema_linking_path))

from subproblem_agent import SubproblemAgent
from query_based_schema_filter import QueryBasedSchemaFilter  # type: ignore


def main():
    """
    Main function demonstrating subproblem decomposition.
    
    This example:
    1. Uses Schema Linking Agent to filter schema for each query
    2. Decomposes each query into clause-wise subproblems
    3. Saves subproblems to JSON files
    """
    print("=" * 80)
    print("Subproblem Agent - Example Usage")
    print("=" * 80)
    
    # Initialize Schema Linking Agent
    print("\n📊 Initializing Schema Linking Agent...")
    schema_path = os.path.join(schema_linking_path, "cisco_stage_app_modified_m_schema.json")
    vector_db_path = os.path.join(schema_linking_path, "vector_db")
    cache_path = os.path.join(schema_linking_path, "embeddings_cache.json")
    
    schema_filter = QueryBasedSchemaFilter(
        schema_path=schema_path,
        vector_db_path=vector_db_path,
        embedding_cache_path=cache_path
    )
    
    # Pre-compute embeddings if needed
    print("\n⏳ Checking embeddings...")
    schema_filter.precompute_embeddings(force_recompute=False)
    
    # Initialize Subproblem Agent
    print("\n🤖 Initializing Subproblem Agent...")
    subproblem_agent = SubproblemAgent(
        model="llama-3.1-70b-versatile",
        temperature=0.1,
        max_tokens=2000
    )
    
    # Create results directory
    results_dir = "./results"
    os.makedirs(results_dir, exist_ok=True)
    
    # Same 10 queries from Schema Linking Agent
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
    
    print(f"\n📝 Processing {len(queries)} queries...")
    print("=" * 80)
    
    # Process each query
    all_subproblems = []
    
    for i, user_query in enumerate(queries, 1):
        print(f"\n{'=' * 80}")
        print(f"Query {i}/{len(queries)}: {user_query}")
        print("=" * 80)
        
        # Step 1: Filter schema using Schema Linking Agent
        print("\n1️⃣  Filtering schema...")
        filtered_schema = schema_filter.filter_schema(
            user_query=user_query,
            top_k_tables=10,
            top_k_columns=15,
            similarity_threshold=0.5,
            fk_hops=1
        )
        
        num_tables = len(filtered_schema.get("tables", {}))
        total_columns = sum(
            len(t.get("fields", {})) 
            for t in filtered_schema.get("tables", {}).values()
        )
        print(f"   ✓ Filtered to {num_tables} tables, {total_columns} columns")
        
        # Step 2: Decompose query into subproblems
        print("\n2️⃣  Decomposing query into subproblems...")
        try:
            subproblems = subproblem_agent.decompose_query(
                user_query=user_query,
                filtered_schema=filtered_schema
            )
            
            # Display results
            print(f"\n📋 Subproblems:")
            print(f"   SELECT: {subproblems.get('SELECT', 'N/A')}")
            print(f"   FROM: {subproblems.get('FROM', 'N/A')}")
            print(f"   WHERE: {subproblems.get('WHERE', 'None')}")
            print(f"   GROUP BY: {subproblems.get('GROUP BY', 'None')}")
            print(f"   HAVING: {subproblems.get('HAVING', 'None')}")
            print(f"   ORDER BY: {subproblems.get('ORDER BY', 'None')}")
            print(f"   Complexity: {subproblems.get('complexity', 'N/A')}")
            print(f"   Requires Join: {subproblems.get('requires_join', False)}")
            print(f"   Requires Aggregation: {subproblems.get('requires_aggregation', False)}")
            
            # Save subproblems
            output_file = os.path.join(results_dir, f"subproblems_query_{i}.json")
            output_data = {
                "query": user_query,
                "subproblems": subproblems,
                "filtered_schema_stats": {
                    "num_tables": num_tables,
                    "num_columns": total_columns
                }
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            print(f"\n✓ Subproblems saved to: {output_file}")
            
            all_subproblems.append({
                "query": user_query,
                "subproblems": subproblems
            })
            
        except Exception as e:
            print(f"\n❌ Error decomposing query: {str(e)}")
            continue
    
    # Summary
    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print("=" * 80)
    print(f"Total queries processed: {len(all_subproblems)}/{len(queries)}")
    print(f"Results saved to: {results_dir}/")
    
    # Statistics
    if all_subproblems:
        complexities = [sp["subproblems"].get("complexity", "unknown") for sp in all_subproblems]
        joins_count = sum(1 for sp in all_subproblems if sp["subproblems"].get("requires_join", False))
        agg_count = sum(1 for sp in all_subproblems if sp["subproblems"].get("requires_aggregation", False))
        
        print(f"\n📊 Statistics:")
        print(f"   Queries requiring joins: {joins_count}/{len(all_subproblems)}")
        print(f"   Queries requiring aggregation: {agg_count}/{len(all_subproblems)}")
        print(f"   Complexity distribution:")
        for comp in ["simple", "moderate", "complex"]:
            count = complexities.count(comp)
            if count > 0:
                print(f"     - {comp}: {count}")
    
    print("\n" + "=" * 80)
    print("Example Complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()

