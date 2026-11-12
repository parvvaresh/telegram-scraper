# -------------------- ClickHouse settings --------------------
# Values come from input/settings.json (see settings.py); edit them from the web panel.
from settings import load_settings

_ch = load_settings()["clickhouse"]

# Base URL for communicating with the ClickHouse server over HTTP
CLICKHOUSE_HTTP_URL = _ch["url"]

# Authentication credentials (username, password) for connecting to ClickHouse
CLICKHOUSE_AUTH = (_ch["user"], _ch["password"])

# Target database name used for queries and operations in ClickHouse
DB_NAME = _ch["database"]

# HTTP headers used for sending requests, specifying a common user-agent for compatibility
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
