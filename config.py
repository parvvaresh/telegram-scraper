# -----------------------------
# Telegram API credentials
# -----------------------------
api_id = 27682564  # Unique API ID obtained from my.telegram.org
api_hash = '009222a70c4eac144828a1d4eec6a064'  # Secret API hash tied to the api_id

# Connection timeout for network operations (in seconds)
TELETHON_TIMEOUT = 30

# -----------------------------
# HTTP Proxy Configuration
# -----------------------------

# These are the credentials and IP settings for the HTTP proxy
HTTP_PROXY_HOST = '89.106.206.173'   # Proxy IP address
HTTP_PROXY_PORT = 8888               # Proxy port
HTTP_PROXY_USER = 'proxyuser'        # Proxy username
HTTP_PROXY_PASS = 'pass1234'         # Proxy password

# This builds a full HTTP proxy URL using the credentials
HTTP_PROXY_URL = f"http://{HTTP_PROXY_USER}:{HTTP_PROXY_PASS}@{HTTP_PROXY_HOST}:{HTTP_PROXY_PORT}"

# This dictionary can be used with libraries like requests, aiohttp, etc.
proxies = {
    'http': HTTP_PROXY_URL,    # Proxy for HTTP traffic
    'https': HTTP_PROXY_URL,   # Proxy for HTTPS traffic
}

# -----------------------------
# MTProto Proxy Configuration
# -----------------------------

# This section sets up the Telegram-specific MTProto proxy
MTPROTO_PROXY = {
    'server': '89.106.206.173',  # MTProto proxy server address
    'port': 443,                 # Standard secure port for MTProto
    'secret': '55483807d4df2aec370586b83766f5ae'  # Secret key in hex format
}


# -----------------------------
# Number of sessions you want to create
# -----------------------------
NUM_SESSIONS = 4