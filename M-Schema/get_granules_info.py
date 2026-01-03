import os
import warnings
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text
import urllib3

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

# URL encode the password
encoded_password = quote_plus(CH_DB_PASSWORD)

# Connect to ClickHouse
clickhouse_url = f'clickhouse+http://{CH_DB_USER}:{encoded_password}@{CH_DB_HOST}:{CH_DB_PORT}/{CH_DB_NAME}?protocol=https&verify=false'
print(f"Connecting to ClickHouse: {CH_DB_HOST}:{CH_DB_PORT}")
print(f"Database: {CH_DB_NAME}")
print(f"\nFetching granule information...\n")

db_engine = create_engine(clickhouse_url)

# Query to get granule information for all tables in the database
granules_query = f"""
SELECT 
    table,
    sum(rows) as total_rows,
    sum(bytes_on_disk) as total_bytes,
    sum(marks) as total_marks,
    count() as num_parts,
    formatReadableSize(sum(bytes_on_disk)) as readable_size
FROM system.parts
WHERE database = '{CH_DB_NAME}'
  AND active = 1
GROUP BY table
ORDER BY total_rows DESC
"""

print("="*100)
print("Granule Information for Tables in Database")
print("="*100)
print(f"{'Table Name':<40} {'Total Rows':<15} {'Total Marks':<15} {'Parts':<10} {'Size':<15}")
print("-"*100)

try:
    with db_engine.connect() as connection:
        result = connection.execute(text(granules_query))
        rows = result.fetchall()
        
        if not rows:
            print("No active parts found for tables in this database.")
        else:
            total_granules_all = 0
            for row in rows:
                table_name, total_rows, total_bytes, total_marks, num_parts, readable_size = row
                # In ClickHouse, marks represent granules
                # Each mark typically corresponds to one granule
                total_granules_all += total_marks or 0
                
                print(f"{table_name:<40} {total_rows:<15,} {total_marks:<15,} {num_parts:<10} {readable_size:<15}")
            
            print("-"*100)
            print(f"{'TOTAL':<40} {'':<15} {total_granules_all:<15,} {'':<10} {'':<15}")
            print(f"\nTotal Granules (Marks) across all tables: {total_granules_all:,}")

except Exception as e:
    print(f"Error querying granules: {e}")
    import traceback
    traceback.print_exc()

# Additional detailed query for specific table if needed
print("\n" + "="*100)
print("Detailed Granule Information (per partition)")
print("="*100)

detailed_query = f"""
SELECT 
    table,
    partition,
    name as part_name,
    rows,
    bytes_on_disk,
    marks,
    formatReadableSize(bytes_on_disk) as size,
    modification_time
FROM system.parts
WHERE database = '{CH_DB_NAME}'
  AND active = 1
ORDER BY table, partition, name
LIMIT 50
"""

try:
    with db_engine.connect() as connection:
        result = connection.execute(text(detailed_query))
        rows = result.fetchall()
        
        if rows:
            print(f"{'Table':<30} {'Partition':<20} {'Part Name':<30} {'Rows':<12} {'Marks':<10} {'Size':<15}")
            print("-"*100)
            for row in rows:
                table, partition, part_name, rows_count, bytes_on_disk, marks, size, mod_time = row
                print(f"{table:<30} {str(partition):<20} {part_name:<30} {rows_count:<12,} {marks:<10,} {size:<15}")
            
            if len(rows) == 50:
                print("\n... (showing first 50 parts, there may be more)")
        else:
            print("No active parts found.")
            
except Exception as e:
    print(f"Error querying detailed parts: {e}")

print("\n" + "="*100)
print("Notes:")
print("="*100)
print("• Marks = Granules: In ClickHouse, 'marks' represent granules")
print("• Each mark typically corresponds to one granule (smallest data unit)")
print("• Granules are the smallest indivisible data sets ClickHouse reads")
print("• Default granule size is usually 8192 rows")
print("• Active parts only: This query shows only active (non-detached) parts")

