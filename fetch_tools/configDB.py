# -------------------- Constants & Settings  Data Bases--------------------

# Base URL for communicating with the ClickHouse server over HTTP
CLICKHOUSE_HTTP_URL = "http://localhost:8123/"

# Authentication credentials (username, password) for connecting to ClickHouse
CLICKHOUSE_AUTH = ("reza", "1234")

# Target database name used for queries and operations in ClickHouse
DB_NAME = "vazir1"

# HTTP headers used for sending requests, specifying a common user-agent for compatibility
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
