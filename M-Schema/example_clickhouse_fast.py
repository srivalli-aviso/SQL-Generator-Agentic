import os
import warnings
from urllib.parse import quote_plus
from schema_engine import SchemaEngine
from sqlalchemy import create_engine
import urllib3
import time

# Suppress SSL warnings for unverified HTTPS requests
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

# ClickHouse Database Configuration
# All database credentials must be set as environment variables for security
CH_DB_HOST = os.getenv('CH_DB_HOST')
CH_DB_USER = os.getenv('CH_DB_USER')
CH_DB_PORT = os.getenv('CH_DB_PORT', '8443')  # Default port for ClickHouse Cloud HTTPS
CH_DB_PASSWORD = os.getenv('CH_DB_PASSWORD')
CH_DB_NAME = os.getenv('CH_DB_NAME')

# Validate required environment variables
if not CH_DB_HOST:
    raise ValueError("CH_DB_HOST environment variable is not set. Please set it using: export CH_DB_HOST='your-host'")
if not CH_DB_USER:
    raise ValueError("CH_DB_USER environment variable is not set. Please set it using: export CH_DB_USER='your-username'")
if not CH_DB_PASSWORD:
    raise ValueError("CH_DB_PASSWORD environment variable is not set. Please set it using: export CH_DB_PASSWORD='your-password'")
if not CH_DB_NAME:
    raise ValueError("CH_DB_NAME environment variable is not set. Please set it using: export CH_DB_NAME='your-database-name'")

# Set to False to fetch example values using groupUniqArray (faster than before but still takes time)
# Set to True to skip fetching example values (execution completes in minutes instead of hours)
SKIP_EXAMPLES = os.getenv('SKIP_EXAMPLES', 'false').lower() == 'true'  # Change to 'true' to skip examples

# URL encode the password
encoded_password = quote_plus(CH_DB_PASSWORD)

# Connect to ClickHouse
clickhouse_url = f'clickhouse+http://{CH_DB_USER}:{encoded_password}@{CH_DB_HOST}:{CH_DB_PORT}/{CH_DB_NAME}?protocol=https&verify=false'
print(f"Connecting to ClickHouse: {CH_DB_HOST}:{CH_DB_PORT}/{CH_DB_NAME}")
print(f"Fast Mode: {'ON (skipping examples)' if SKIP_EXAMPLES else 'OFF (fetching examples)'}")

db_engine = create_engine(clickhouse_url)

# Generate M-Schema
print("Generating M-Schema...")
start_time = time.time()

try:
    # Pass skip_examples=True to skip fetching example values (much faster!)
    schema_engine = SchemaEngine(engine=db_engine, db_name=CH_DB_NAME, skip_examples=SKIP_EXAMPLES)
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
    
    # Save to JSON
    output_file = f'./{CH_DB_NAME}_clickhouse.json'
    mschema.save(output_file)
    print(f"\n✓ M-Schema saved to: {output_file}")
    print(f"✓ Total execution time: {time.time() - start_time:.2f} seconds")
    
except KeyboardInterrupt:
    print("\n\n⚠ Process interrupted by user")
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()

