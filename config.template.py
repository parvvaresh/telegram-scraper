# -----------------------------
# Telegram API credentials
# -----------------------------
api_id = 0  # Set your API ID from my.telegram.org
api_hash = 'YOUR_API_HASH'  # Set your API hash from my.telegram.org

# Connection timeout for network operations (in seconds)
TELETHON_TIMEOUT = 30

# -----------------------------
# HTTP Proxy Configuration
# -----------------------------

# These are the credentials and IP settings for the HTTP proxy
HTTP_PROXY_HOST = ''                 # Proxy IP address
HTTP_PROXY_PORT = 0                  # Proxy port
HTTP_PROXY_USER = ''                 # Proxy username
HTTP_PROXY_PASS = ''                 # Proxy password

# This builds a full HTTP proxy URL using the credentials
HTTP_PROXY_URL = (
    f"http://{HTTP_PROXY_USER}:{HTTP_PROXY_PASS}@{HTTP_PROXY_HOST}:{HTTP_PROXY_PORT}"
    if HTTP_PROXY_HOST and HTTP_PROXY_PORT and HTTP_PROXY_USER and HTTP_PROXY_PASS
    else ''
)

# This dictionary can be used with libraries like requests, aiohttp, etc.
proxies = (
    {
        'http': HTTP_PROXY_URL,    # Proxy for HTTP traffic
        'https': HTTP_PROXY_URL,   # Proxy for HTTPS traffic
    }
    if HTTP_PROXY_URL
    else {}
)

# -----------------------------
# MTProto Proxy Configuration
# -----------------------------

# This section sets up the Telegram-specific MTProto proxy
MTPROTO_PROXY = {
    'server': '',                 # MTProto proxy server address
    'port': 0,                    # MTProto proxy port
    'secret': ''                  # Secret key in hex format
}


# -----------------------------
# Number of sessions you want to create
# -----------------------------
NUM_SESSIONS = 4
