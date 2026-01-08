import warnings
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text
from config import MSchemaConfig
import urllib3

# Suppress SSL warnings for unverified HTTPS requests
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

# Validate required configuration (CH_DB_NAME not required for listing databases)
if not MSchemaConfig.CH_DB_HOST or not MSchemaConfig.CH_DB_USER or not MSchemaConfig.CH_DB_PASSWORD:
    raise ValueError(
        "Missing required database credentials. "
        "Please set CH_DB_HOST, CH_DB_USER, and CH_DB_PASSWORD."
    )

# URL encode the password in case it contains special characters
encoded_password = quote_plus(MSchemaConfig.CH_DB_PASSWORD)

# Connect to ClickHouse (using 'default' database to list all databases)
clickhouse_url = (
    f'clickhouse+http://{MSchemaConfig.CH_DB_USER}:{encoded_password}@'
    f'{MSchemaConfig.CH_DB_HOST}:{MSchemaConfig.CH_DB_PORT}/default?'
    f'protocol={MSchemaConfig.CLICKHOUSE_DEFAULT_PROTOCOL}&verify={str(MSchemaConfig.SSL_VERIFY).lower()}'
)
print(f"Connecting to ClickHouse: {MSchemaConfig.CH_DB_HOST}:{MSchemaConfig.CH_DB_PORT}")
print(f"Fetching list of databases...\n")

db_engine = create_engine(clickhouse_url)

# Execute SHOW DATABASES query
with db_engine.connect() as connection:
    # ClickHouse uses SHOW DATABASES to list all databases
    result = connection.execute(text("SHOW DATABASES"))
    databases = [row[0] for row in result.fetchall()]

print("="*80)
print(f"Found {len(databases)} database(s):")
print("="*80)
for i, db_name in enumerate(databases, 1):
    print(f"{i}. {db_name}")

print("\n" + "="*80)
print("To use a specific database, update CH_DB_NAME in your script:")
print("="*80)
print(f"CH_DB_NAME = '{databases[0] if databases else 'default'}'  # or any other database from the list above")

