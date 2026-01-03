import os
import warnings
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text
import urllib3

# Suppress SSL warnings
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
db_engine = create_engine(clickhouse_url)

# Get granule and row information
query = f"""
SELECT 
    table,
    sum(rows) as total_rows,
    sum(marks) as total_marks
FROM system.parts
WHERE database = '{CH_DB_NAME}'
  AND active = 1
GROUP BY table
ORDER BY total_rows DESC
"""

with db_engine.connect() as connection:
    result = connection.execute(text(query))
    rows = result.fetchall()
    
    total_rows_all = 0
    total_marks_all = 0
    max_rows = 0
    max_marks = 0
    
    for table_name, total_rows, total_marks in rows:
        total_rows_all += total_rows or 0
        total_marks_all += total_marks or 0
        if total_rows > max_rows:
            max_rows = total_rows
            max_marks = total_marks

# Calculate ideal sample
# ClickHouse default granule size is typically 8192 rows
# For statistical sampling, we want to sample at least:
# 1. Enough to cover multiple granules (for accuracy)
# 2. A reasonable percentage of data (10-20% is common)
# 3. At least 10,000 rows for statistical significance

avg_rows_per_granule = max_rows / max_marks if max_marks > 0 else 8192

# Option 1: Sample by coefficient (percentage)
# 10% is a good balance between accuracy and performance
sample_coefficient = 0.1  # 10%

# Option 2: Sample by number of rows
# Sample at least 3-5 granules worth of data for accuracy
min_granules_to_sample = 5
sample_rows = int(avg_rows_per_granule * min_granules_to_sample)

# Ensure minimum sample size for statistical significance
min_sample_rows = 10000
sample_rows = max(sample_rows, min_sample_rows)

# For the largest table, calculate what percentage this represents
if max_rows > 0:
    sample_percentage = (sample_rows / max_rows) * 100
    sample_coefficient_from_rows = sample_rows / max_rows
else:
    sample_percentage = 0
    sample_coefficient_from_rows = 0.1

print("="*80)
print("Ideal SAMPLE Calculation")
print("="*80)
print(f"Largest table rows: {max_rows:,}")
print(f"Largest table marks (granules): {max_marks}")
print(f"Average rows per granule: {avg_rows_per_granule:,.0f}")
print(f"Total rows across all tables: {total_rows_all:,}")
print(f"Total granules across all tables: {total_marks_all}")
print("\n" + "="*80)
print("RECOMMENDED SAMPLE VALUES:")
print("="*80)

# Recommendation 1: By coefficient (most common)
print(f"\n1. SAMPLE BY COEFFICIENT (Recommended):")
print(f"   SAMPLE {sample_coefficient}")
print(f"   → Samples {sample_coefficient*100}% of data")
print(f"   → For largest table: ~{int(max_rows * sample_coefficient):,} rows")

# Recommendation 2: By number of rows
print(f"\n2. SAMPLE BY ROWS:")
print(f"   SAMPLE {sample_rows:,}")
print(f"   → Samples {sample_rows:,} rows")
print(f"   → Represents {sample_percentage:.2f}% of largest table")
print(f"   → Covers approximately {sample_rows/avg_rows_per_granule:.1f} granules")

# Recommendation 3: Alternative percentages
print(f"\n3. ALTERNATIVE SAMPLE COEFFICIENTS:")
for pct in [0.05, 0.1, 0.2, 0.5]:
    rows_at_pct = int(max_rows * pct)
    granules_at_pct = rows_at_pct / avg_rows_per_granule
    print(f"   SAMPLE {pct} → {pct*100}% = ~{rows_at_pct:,} rows (~{granules_at_pct:.1f} granules)")

print("\n" + "="*80)
print("FINAL RECOMMENDATION:")
print("="*80)
print(f"Use: SAMPLE {sample_coefficient}")
print(f"     (This samples {sample_coefficient*100}% of your data)")
print(f"     For your largest table, this is approximately {int(max_rows * sample_coefficient):,} rows")
print("="*80)

# Output just the number as requested
print(f"\nIdeal SAMPLE coefficient: {sample_coefficient}")

