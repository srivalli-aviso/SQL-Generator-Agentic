import warnings
from sqlalchemy import create_engine, text
from config import MSchemaConfig
import urllib3

# Suppress SSL warnings for unverified HTTPS requests
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

# Validate required configuration
MSchemaConfig.validate_required()

# Get configuration values
CH_DB_NAME = MSchemaConfig.CH_DB_NAME

# Get ClickHouse connection URL from config
clickhouse_url = MSchemaConfig.get_clickhouse_url()
print(f"Connecting to ClickHouse: {MSchemaConfig.CH_DB_HOST}:{MSchemaConfig.CH_DB_PORT}")
print(f"Database: {CH_DB_NAME}")
print(f"Fetching list of tables...\n")

db_engine = create_engine(clickhouse_url)

# Execute SHOW TABLES query - ClickHouse shows both tables and views
with db_engine.connect() as connection:
    # ClickHouse uses SHOW TABLES to list all tables in the current database
    result = connection.execute(text(f"SHOW TABLES FROM {CH_DB_NAME}"))
    tables = [row[0] for row in result.fetchall()]
    
    # Also check for views separately
    try:
        views_result = connection.execute(text(f"SELECT name FROM system.tables WHERE database = '{CH_DB_NAME}' AND engine LIKE '%View%'"))
        views = [row[0] for row in views_result.fetchall()]
    except:
        views = []

print("="*80)
print(f"Found {len(tables)} table(s) in database '{CH_DB_NAME}':")
print("="*80)

# Check if deals_history_duration exists
target_table = 'deals_history_duration'
if target_table in tables:
    print(f"✓ '{target_table}' EXISTS in the database")
else:
    print(f"✗ '{target_table}' NOT FOUND in SHOW TABLES result")

print("\nAll tables:")
for i, table_name in enumerate(tables, 1):
    marker = " <-- THIS ONE" if table_name == target_table else ""
    print(f"{i:4d}. {table_name}{marker}")

print("\n" + "="*80)
print("Summary:")
print("="*80)
print(f"Total tables: {len(tables)}")

# Optionally, get more details about each table
if len(tables) > 0:
    print("\n" + "="*80)
    print("Table Details (first 10 tables):")
    print("="*80)
    for table_name in tables[:10]:
        try:
            with db_engine.connect() as connection:
                # Get row count
                count_result = connection.execute(text(f"SELECT count() FROM {CH_DB_NAME}.{table_name}"))
                row_count = count_result.fetchone()[0]
                
                # Get column count
                desc_result = connection.execute(text(f"DESCRIBE TABLE {CH_DB_NAME}.{table_name}"))
                columns = desc_result.fetchall()
                col_count = len(columns)
                
                print(f"{table_name:40s} | Rows: {row_count:>12,} | Columns: {col_count:>3}")
        except Exception as e:
            print(f"{table_name:40s} | Error: {str(e)[:50]}")
    
    if len(tables) > 10:
        print(f"\n... and {len(tables) - 10} more tables")

