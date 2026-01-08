"""
Example Usage Script for Query Plan Agent

Demonstrates how to use the Query Plan Agent to generate query plans from
subproblems. Integrates with Subproblem Agent results automatically.
"""

import json
import os
import sys
from query_plan_agent import QueryPlanAgent
from config import QueryPlanConfig


def main():
    """
    Main function demonstrating query plan generation.
    
    This example:
    1. Loads subproblems from Subproblem Agent results
    2. Generates query plans for each query
    3. Saves query plans to JSON files
    4. Displays summary statistics
    """
    print("=" * 80)
    print("Query Plan Agent - Example Usage")
    print("=" * 80)
    
    # Initialize Query Plan Agent
    print("\n🤖 Initializing Query Plan Agent...")
    config = QueryPlanConfig(
        model="openai/gpt-oss-120b",  # 120B MoE model, excellent for complex query planning
        temperature=0.1,
        max_tokens=3000,
        subproblems_dir="../Subproblem_Agent/results"
    )
    
    agent = QueryPlanAgent(config)
    print(f"   ✓ Agent initialized (model: {config.model})")
    
    # Create results directory
    results_dir = config.results_dir
    os.makedirs(results_dir, exist_ok=True)
    print(f"   ✓ Results directory: {results_dir}")
    
    # Load subproblems from Subproblem Agent results
    subproblems_dir = config.subproblems_dir
    print(f"\n📂 Loading subproblems from: {subproblems_dir}")
    
    if not os.path.exists(subproblems_dir):
        print(f"❌ Error: Subproblems directory not found: {subproblems_dir}")
        print("   Please run the Subproblem Agent first to generate subproblems.")
        return
    
    # Find all subproblem files
    subproblem_files = [
        f for f in os.listdir(subproblems_dir)
        if f.startswith("subproblems_query_") and f.endswith(".json")
    ]
    subproblem_files.sort(key=lambda x: int(x.split("_")[-1].split(".")[0]))
    
    if not subproblem_files:
        print(f"❌ Error: No subproblem files found in {subproblems_dir}")
        print("   Please run the Subproblem Agent first.")
        return
    
    print(f"   ✓ Found {len(subproblem_files)} subproblem files")
    
    print(f"\n📝 Processing {len(subproblem_files)} queries...")
    print("=" * 80)
    
    # Process each subproblem file
    all_plans = []
    successful = 0
    failed = 0
    
    for i, subproblem_file in enumerate(subproblem_files, 1):
        print(f"\n{'=' * 80}")
        print(f"Query {i}/{len(subproblem_files)}")
        print("=" * 80)
        
        try:
            # Load subproblems
            print(f"\n1️⃣  Loading subproblems from: {subproblem_file}")
            subproblems_data = agent.load_subproblems(subproblem_file)
            
            user_query = subproblems_data["query"]
            subproblems = subproblems_data["subproblems"]
            
            print(f"   Query: {user_query}")
            print(f"   Complexity: {subproblems.get('complexity', 'N/A')}")
            print(f"   Requires Join: {subproblems.get('requires_join', False)}")
            print(f"   Requires Aggregation: {subproblems.get('requires_aggregation', False)}")
            
            # Generate query plan
            print(f"\n2️⃣  Generating query plan...")
            query_plan = agent.generate_query_plan(
                user_query=user_query,
                subproblems=subproblems
            )
            
            # Display plan summary
            print(f"\n📋 Query Plan Summary:")
            print(f"   Execution Steps: {len(query_plan.get('execution_steps', []))}")
            print(f"   Base Table: {query_plan.get('from_table', 'N/A')}")
            print(f"   Joins: {len(query_plan.get('joins', []))}")
            print(f"   Select Columns: {len(query_plan.get('select_columns', []))}")
            print(f"   Group By: {query_plan.get('group_by', 'None')}")
            print(f"   Subqueries: {len(query_plan.get('subqueries', []))}")
            
            # Save query plan
            output_file = os.path.join(results_dir, f"query_plan_query_{i}.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(query_plan, f, indent=2, ensure_ascii=False)
            
            print(f"\n✓ Query plan saved to: {output_file}")
            
            all_plans.append({
                "query": user_query,
                "plan": query_plan
            })
            successful += 1
            
        except FileNotFoundError as e:
            print(f"\n❌ Error: {str(e)}")
            failed += 1
        except ValueError as e:
            print(f"\n❌ Validation Error: {str(e)}")
            failed += 1
        except Exception as e:
            print(f"\n❌ Error generating query plan: {str(e)}")
            failed += 1
            continue
    
    # Summary
    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print("=" * 80)
    print(f"Total queries processed: {len(subproblem_files)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Results saved to: {results_dir}/")
    
    # Statistics
    if all_plans:
        total_steps = sum(len(p["plan"].get("execution_steps", [])) for p in all_plans)
        total_joins = sum(len(p["plan"].get("joins", [])) for p in all_plans)
        plans_with_aggregation = sum(
            1 for p in all_plans
            if p["plan"].get("group_by") is not None
        )
        plans_with_subqueries = sum(
            1 for p in all_plans
            if len(p["plan"].get("subqueries", [])) > 0
        )
        
        print(f"\n📊 Statistics:")
        print(f"   Average execution steps per plan: {total_steps / len(all_plans):.1f}")
        print(f"   Total joins across all plans: {total_joins}")
        print(f"   Plans with aggregation: {plans_with_aggregation}/{len(all_plans)}")
        print(f"   Plans with subqueries: {plans_with_subqueries}/{len(all_plans)}")
        
        # Join type distribution
        join_types = {}
        for plan_data in all_plans:
            for join in plan_data["plan"].get("joins", []):
                join_type = join.get("type", "UNKNOWN")
                join_types[join_type] = join_types.get(join_type, 0) + 1
        
        if join_types:
            print(f"\n   Join Type Distribution:")
            for join_type, count in sorted(join_types.items()):
                print(f"     - {join_type}: {count}")
    
    print("\n" + "=" * 80)
    print("Example Complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()

