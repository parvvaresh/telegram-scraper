# -----------------------------------------------------------------------------
# Scraper configuration.
#
# Values are NOT edited here anymore: they come from input/settings.json, which
# you can edit from the web panel (`python3 -m web`) or by hand.
# See settings.py for the full list of keys and their defaults.
# -----------------------------------------------------------------------------
from settings import load_settings, http_proxy_url, http_proxies, mtproto_proxy

_settings = load_settings()

# Telegram API credentials (from my.telegram.org)
api_id = _settings["telegram"]["api_id"]
api_hash = _settings["telegram"]["api_hash"]

# Connection timeout for network operations (in seconds)
TELETHON_TIMEOUT = _settings["telegram"]["timeout"]

# HTTP proxy (used to scrape t.me/s/ pages)
HTTP_PROXY_HOST = _settings["http_proxy"]["host"]
HTTP_PROXY_PORT = _settings["http_proxy"]["port"]
HTTP_PROXY_USER = _settings["http_proxy"]["user"]
HTTP_PROXY_PASS = _settings["http_proxy"]["password"]
HTTP_PROXY_URL = http_proxy_url(_settings)
proxies = http_proxies(_settings)

# MTProto proxy (used by Telethon). MTPROTO_PROXY_TUPLE is None when not configured.
MTPROTO_PROXY = dict(_settings["mtproto_proxy"])
MTPROTO_PROXY_TUPLE = mtproto_proxy(_settings)

# Number of Telethon sessions create_esssion.py should create
NUM_SESSIONS = _settings["telegram"]["num_sessions"]
