import warnings
from schema_engine import SchemaEngine
from sqlalchemy import create_engine
from config import MSchemaConfig
import urllib3
import time

# Suppress SSL warnings for unverified HTTPS requests
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

# Validate required configuration
MSchemaConfig.validate_required()

# Get configuration values
CH_DB_NAME = MSchemaConfig.CH_DB_NAME
SKIP_EXAMPLES = MSchemaConfig.SKIP_EXAMPLES
INCLUDE_TABLES = MSchemaConfig.get_include_tables()

# Get ClickHouse connection URL from config
clickhouse_url = MSchemaConfig.get_clickhouse_url()
print(f"Connecting to ClickHouse: {MSchemaConfig.CH_DB_HOST}:{MSchemaConfig.CH_DB_PORT}/{CH_DB_NAME}")
print(f"Fast Mode: {'ON (skipping examples)' if SKIP_EXAMPLES else 'OFF (fetching examples)'}")

# Display table filtering information
if INCLUDE_TABLES:
    print(f"Table Filtering: ON - Including only: {', '.join(INCLUDE_TABLES)}")
else:
    print(f"Table Filtering: OFF - Including all tables in database")

db_engine = create_engine(clickhouse_url)

# Generate M-Schema
print("Generating M-Schema...")
start_time = time.time()

try:
    # Pass include_tables if filtering is enabled, skip_examples for performance
    schema_engine = SchemaEngine(
        engine=db_engine, 
        db_name=CH_DB_NAME, 
        skip_examples=SKIP_EXAMPLES,
        include_tables=INCLUDE_TABLES
    )
    elapsed = time.time() - start_time
    print(f"✓ Schema extraction completed in {elapsed:.2f} seconds")
    
    mschema = schema_engine.mschema
    print("Generating M-Schema string representation...")
    mschema_str = mschema.to_mschema(example_num=0 if SKIP_EXAMPLES else 3)
    
    print("\n" + "="*80)
    print("M-Schema Representation (first 2000 characters):")
    print("="*80)
    print(mschema_str[:2000])
    if len(mschema_str) > 2000:
        print(f"\n... (truncated, total length: {len(mschema_str)} characters)")
    
    # Save to JSON using config file path
    output_file = MSchemaConfig.get_input_schema_file()
    mschema.save(output_file)
    print(f"\n✓ M-Schema saved to: {output_file}")
    print(f"✓ Total execution time: {time.time() - start_time:.2f} seconds")
    
except KeyboardInterrupt:
    print("\n\n⚠ Process interrupted by user")
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()

