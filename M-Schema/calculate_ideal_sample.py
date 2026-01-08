import warnings
from sqlalchemy import create_engine, text
from config import MSchemaConfig
import urllib3

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

# Validate required configuration
MSchemaConfig.validate_required()

# Get configuration values
CH_DB_NAME = MSchemaConfig.CH_DB_NAME
INCLUDE_TABLES = MSchemaConfig.get_include_tables()

# Get ClickHouse connection URL from config
clickhouse_url = MSchemaConfig.get_clickhouse_url()
db_engine = create_engine(clickhouse_url)

# Build query with optional table filtering
base_query = """
SELECT 
    table,
    sum(rows) as total_rows,
    sum(marks) as total_marks
FROM system.parts
WHERE database = :db_name
  AND active = 1
"""

# Add table filtering if INCLUDE_TABLES is specified
if INCLUDE_TABLES:
    # Create placeholders for table names
    table_placeholders = ', '.join([f"'{table}'" for table in INCLUDE_TABLES])
    query = f"{base_query}  AND table IN ({table_placeholders})\nGROUP BY table\nORDER BY total_rows DESC"
else:
    query = f"{base_query}\nGROUP BY table\nORDER BY total_rows DESC"

# Use parameterized query for database name to prevent SQL injection
query = query.replace(':db_name', f"'{CH_DB_NAME}'")

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
# Use default from config
sample_coefficient = MSchemaConfig.SAMPLE_COEFFICIENT_DEFAULT

# Option 2: Sample by number of rows
# Sample at least configured granules worth of data for accuracy
min_granules_to_sample = MSchemaConfig.MIN_GRANULES_TO_SAMPLE
sample_rows = int(avg_rows_per_granule * min_granules_to_sample)

# Ensure minimum sample size for statistical significance
min_sample_rows = MSchemaConfig.MIN_SAMPLE_ROWS
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

