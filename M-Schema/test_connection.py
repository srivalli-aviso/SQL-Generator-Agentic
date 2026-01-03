#!/usr/bin/env python3
"""
Diagnostic script to test ClickHouse connection and DNS resolution
"""
import os
import socket
import sys
from urllib.parse import quote_plus

# ClickHouse Database Configuration
# All database credentials must be set as environment variables for security
CH_DB_HOST = os.getenv('CH_DB_HOST')
CH_DB_PORT = int(os.getenv('CH_DB_PORT', '8443'))  # Default port for ClickHouse Cloud HTTPS
CH_DB_USER = os.getenv('CH_DB_USER')

# Validate required environment variables
if not CH_DB_HOST:
    raise ValueError("CH_DB_HOST environment variable is not set. Please set it using: export CH_DB_HOST='your-host'")
if not CH_DB_USER:
    raise ValueError("CH_DB_USER environment variable is not set. Please set it using: export CH_DB_USER='your-username'")

print("="*80)
print("ClickHouse Connection Diagnostic")
print("="*80)
print(f"\nHost: {CH_DB_HOST}")
print(f"Port: {CH_DB_PORT}")
print(f"User: {CH_DB_USER}")

# Test 1: DNS Resolution
print("\n" + "="*80)
print("Test 1: DNS Resolution")
print("="*80)
try:
    ip_address = socket.gethostbyname(CH_DB_HOST)
    print(f"✓ DNS Resolution SUCCESS")
    print(f"  Hostname: {CH_DB_HOST}")
    print(f"  IP Address: {ip_address}")
except socket.gaierror as e:
    print(f"✗ DNS Resolution FAILED")
    print(f"  Error: {e}")
    print(f"  Error Code: {e.errno}")
    print(f"\n  Possible causes:")
    print(f"  1. No internet connection")
    print(f"  2. DNS server not responding")
    print(f"  3. Hostname is incorrect")
    print(f"  4. Firewall/proxy blocking DNS queries")
    print(f"  5. VPN or network configuration issues")
    sys.exit(1)

# Test 2: Port Connectivity
print("\n" + "="*80)
print("Test 2: Port Connectivity")
print("="*80)
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    result = sock.connect_ex((ip_address, CH_DB_PORT))
    sock.close()
    if result == 0:
        print(f"✓ Port {CH_DB_PORT} is OPEN and reachable")
    else:
        print(f"✗ Port {CH_DB_PORT} is CLOSED or unreachable")
        print(f"  Connection result code: {result}")
        print(f"\n  Possible causes:")
        print(f"  1. Firewall blocking the port")
        print(f"  2. ClickHouse service is down")
        print(f"  3. Network routing issues")
except Exception as e:
    print(f"✗ Port connectivity test FAILED")
    print(f"  Error: {e}")

# Test 3: SSL/TLS Connection
print("\n" + "="*80)
print("Test 3: SSL/TLS Connection Test")
print("="*80)
try:
    import ssl
    import socket
    
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)
    ssl_sock = context.wrap_socket(sock, server_hostname=CH_DB_HOST)
    ssl_sock.connect((ip_address, CH_DB_PORT))
    print(f"✓ SSL/TLS connection SUCCESS")
    print(f"  SSL Version: {ssl_sock.version()}")
    ssl_sock.close()
except Exception as e:
    print(f"✗ SSL/TLS connection FAILED")
    print(f"  Error: {e}")

# Test 4: SQLAlchemy Connection
print("\n" + "="*80)
print("Test 4: SQLAlchemy Connection Test")
print("="*80)
try:
    from sqlalchemy import create_engine, text
    import urllib3
    import warnings
    
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    warnings.filterwarnings('ignore', message='Unverified HTTPS request')
    
    CH_DB_PASSWORD = os.getenv('CH_DB_PASSWORD')
    if not CH_DB_PASSWORD:
        raise ValueError("CH_DB_PASSWORD environment variable is not set. Please set it using: export CH_DB_PASSWORD='your-password'")
    encoded_password = quote_plus(CH_DB_PASSWORD)
    clickhouse_url = f'clickhouse+http://{CH_DB_USER}:{encoded_password}@{CH_DB_HOST}:{CH_DB_PORT}/default?protocol=https&verify=false'
    
    print(f"Attempting connection...")
    db_engine = create_engine(clickhouse_url, connect_args={'connect_timeout': 10})
    
    with db_engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        row = result.fetchone()
        if row:
            print(f"✓ SQLAlchemy connection SUCCESS")
            print(f"  Test query returned: {row[0]}")
except Exception as e:
    print(f"✗ SQLAlchemy connection FAILED")
    print(f"  Error Type: {type(e).__name__}")
    print(f"  Error: {e}")
    import traceback
    print(f"\n  Full traceback:")
    traceback.print_exc()

print("\n" + "="*80)
print("Diagnostic Complete")
print("="*80)

