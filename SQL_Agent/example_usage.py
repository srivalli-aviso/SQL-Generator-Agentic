"""
Example Usage Script for SQL Agent

Demonstrates how to use the SQL Agent to generate SQL queries from query plans.
Integrates with Query Plan Agent results automatically.
"""

import json
import os
import urllib3
import warnings
from urllib.parse import quote_plus
from sql_agent import SQLAgent
from config import SQLAgentConfig

# Suppress SSL warnings for ClickHouse HTTPS connections
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings('ignore', message='Unverified HTTPS request')


def main():
    """
    Main function demonstrating SQL generation from query plans.
    
    This example:
    1. Loads query plans from Query Plan Agent results
    2. Generates SQL for each query plan
    3. Optionally validates SQL
    4. Optionally executes SQL against database
    5. Saves results to JSON files
    """
    print("=" * 80)
    print("SQL Agent - Example Usage")
    print("=" * 80)
    
    # Initialize SQL Agent
    print("\n🤖 Initializing SQL Agent...")
    
    # Build ClickHouse connection string from environment variables
    db_connection_string = None
    enable_execution = False
    
    # Check for ClickHouse credentials
    ch_db_host = os.getenv('CH_DB_HOST')
    ch_db_user = os.getenv('CH_DB_USER')
    ch_db_port = os.getenv('CH_DB_PORT', '8443')
    ch_db_password = os.getenv('CH_DB_PASSWORD')
    ch_db_name = os.getenv('CH_DB_NAME', 'default')
    
    if ch_db_host and ch_db_user and ch_db_password:
        # URL encode the password in case it contains special characters
        encoded_password = quote_plus(ch_db_password)
        # Construct ClickHouse connection string
        db_connection_string = (
            f"clickhouse+http://{ch_db_user}:{encoded_password}@"
            f"{ch_db_host}:{ch_db_port}/{ch_db_name}?protocol=https&verify=false"
        )
        enable_execution = True
        print(f"   ✓ Database connection configured (ClickHouse)")
    else:
        print(f"   ⚠ Database credentials not found in environment variables")
        print(f"      Set CH_DB_HOST, CH_DB_USER, CH_DB_PASSWORD to enable execution")
    
    config = SQLAgentConfig(
        model="openai/gpt-oss-120b",
        temperature=0.1,
        max_tokens=2000,
        query_plans_dir="../Query_Plan_Agent/results",
        filtered_schema_dir="../Schema_Linking_Agent/results",
        full_schema_path="../Schema_Linking_Agent/cisco_stage_app_modified_m_schema.json",
        sql_format="pretty",
        enable_fallback=True,
        enable_validation=False,  # Set to True to enable validation
        enable_execution=enable_execution,  # Enable if connection string is available
        db_connection_string=db_connection_string
    )
    
    agent = SQLAgent(config)
    print(f"   ✓ Agent initialized (model: {config.model})")
    print(f"   ✓ SQL format: {config.sql_format}")
    print(f"   ✓ Fallback enabled: {config.enable_fallback}")
    print(f"   ✓ Validation enabled: {config.enable_validation}")
    print(f"   ✓ Execution enabled: {config.enable_execution}")
    
    # Create results directory
    results_dir = config.results_dir
    os.makedirs(results_dir, exist_ok=True)
    print(f"   ✓ Results directory: {results_dir}")
    
    # Load query plans from Query Plan Agent results
    query_plans_dir = config.query_plans_dir
    print(f"\n📂 Loading query plans from: {query_plans_dir}")
    
    if not os.path.exists(query_plans_dir):
        print(f"❌ Error: Query plans directory not found: {query_plans_dir}")
        print("   Please run the Query Plan Agent first to generate query plans.")
        return
    
    # Find all query plan files
    plan_files = [
        f for f in os.listdir(query_plans_dir)
        if f.startswith("query_plan_query_") and f.endswith(".json")
    ]
    plan_files.sort(key=lambda x: int(x.split("_")[-1].split(".")[0]))
    
    if not plan_files:
        print(f"❌ Error: No query plan files found in {query_plans_dir}")
        print("   Please run the Query Plan Agent first.")
        return
    
    print(f"   ✓ Found {len(plan_files)} query plan files")
    
    print(f"\n📝 Processing {len(plan_files)} queries...")
    print("=" * 80)
    
    # Process each query plan file
    all_results = []
    successful = 0
    failed = 0
    
    for i, plan_file in enumerate(plan_files, 1):
        print(f"\n{'=' * 80}")
        print(f"Query {i}/{len(plan_files)}")
        print("=" * 80)
        
        try:
            # Load query plan
            print(f"\n1️⃣  Loading query plan from: {plan_file}")
            query_plan = agent.load_query_plan(plan_file)
            
            user_query = query_plan.get("query", "")
            print(f"   Query: {user_query}")
            print(f"   Execution Steps: {len(query_plan.get('execution_steps', []))}")
            print(f"   Joins: {len(query_plan.get('joins', []))}")
            print(f"   Select Columns: {len(query_plan.get('select_columns', []))}")
            
            # Generate SQL
            print(f"\n2️⃣  Generating SQL...")
            sql = agent.generate_sql(query_plan, user_query, query_index=i)
            
            print(f"\n📋 Generated SQL:")
            print("-" * 80)
            print(sql[:500] + ("..." if len(sql) > 500 else ""))
            print("-" * 80)
            
            # Validate SQL (if enabled)
            validation_result = None
            if config.enable_validation:
                print(f"\n3️⃣  Validating SQL...")
                is_valid, error = agent.validate_sql(sql)
                validation_result = {
                    "enabled": True,
                    "is_valid": is_valid,
                    "error": error
                }
                if is_valid:
                    print(f"   ✓ SQL validation passed")
                else:
                    print(f"   ⚠ SQL validation failed: {error}")
            else:
                validation_result = {
                    "enabled": False,
                    "is_valid": None,
                    "error": None
                }
            
            # Execute SQL (if enabled)
            execution_result = None
            if config.enable_execution:
                print(f"\n4️⃣  Executing SQL...")
                execution_result = agent.execute_sql(sql)
                if execution_result.get("success"):
                    print(f"   ✓ SQL execution successful")
                    print(f"   Rows returned: {execution_result.get('row_count', 0)}")
                    print(f"   Execution time: {execution_result.get('execution_time', 0):.3f}s")
                else:
                    print(f"   ⚠ SQL execution failed: {execution_result.get('error')}")
            else:
                execution_result = {
                    "enabled": False,
                    "success": None,
                    "error": None,
                    "row_count": None,
                    "execution_time": None
                }
            
            # Prepare output data
            output_data = {
                "query": user_query,
                "sql": sql,
                "sql_formatted": sql,  # Already formatted based on config
                "generation_method": "llm",  # Could be "fallback" if fallback was used
                "validation": validation_result,
                "execution": execution_result,
                "query_plan_source": plan_file
            }
            
            # Save result
            output_file = os.path.join(results_dir, f"sql_query_{i}.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            print(f"\n✓ SQL saved to: {output_file}")
            
            all_results.append(output_data)
            successful += 1
            
        except FileNotFoundError as e:
            print(f"\n❌ Error: {str(e)}")
            failed += 1
        except ValueError as e:
            print(f"\n❌ Validation Error: {str(e)}")
            failed += 1
        except Exception as e:
            print(f"\n❌ Error generating SQL: {str(e)}")
            failed += 1
            continue
    
    # Summary
    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print("=" * 80)
    print(f"Total queries processed: {len(plan_files)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Results saved to: {results_dir}/")
    
    # Statistics
    if all_results:
        avg_sql_length = sum(len(r.get("sql", "")) for r in all_results) / len(all_results)
        validation_enabled_count = sum(
            1 for r in all_results
            if r.get("validation", {}).get("enabled", False)
        )
        validation_passed_count = sum(
            1 for r in all_results
            if r.get("validation", {}).get("is_valid", False)
        )
        execution_enabled_count = sum(
            1 for r in all_results
            if r.get("execution", {}).get("enabled", False)
        )
        execution_success_count = sum(
            1 for r in all_results
            if r.get("execution", {}).get("success", False)
        )
        
        print(f"\n📊 Statistics:")
        print(f"   Average SQL length: {avg_sql_length:.0f} characters")
        
        if validation_enabled_count > 0:
            print(f"   Validation enabled: {validation_enabled_count}/{len(all_results)}")
            print(f"   Validation passed: {validation_passed_count}/{validation_enabled_count}")
        
        if execution_enabled_count > 0:
            print(f"   Execution enabled: {execution_enabled_count}/{len(all_results)}")
            print(f"   Execution successful: {execution_success_count}/{execution_enabled_count}")
    
    print("\n" + "=" * 80)
    print("Example Complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()

