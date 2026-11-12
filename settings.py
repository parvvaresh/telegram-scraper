"""
Central settings for the scraper.

All values live in ``input/settings.json`` (editable from the web panel, or by hand).
Precedence (lowest -> highest): built-in DEFAULTS < environment variables < settings.json.
``config.py`` and ``fetch_tools/configDB.py`` read from here, so every script picks up
the latest values on its next start.
"""

import copy
import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SETTINGS_PATH = Path(os.environ.get("SCRAPER_SETTINGS", BASE_DIR / "input" / "settings.json"))
CHANNELS_PATH = BASE_DIR / "input" / "channels.json"

DEFAULTS = {
    "telegram": {
        "api_id": 0,
        "api_hash": "",
        "timeout": 30,
        "num_sessions": 4,
    },
    "http_proxy": {
        "host": "",
        "port": 0,
        "user": "",
        "password": "",
    },
    "mtproto_proxy": {
        "server": "",
        "port": 0,
        "secret": "",
    },
    "clickhouse": {
        "url": "http://localhost:8123/",
        "user": "reza",
        "password": "1234",
        "database": "vazir1",
    },
    "posts": {
        "days": 1,                    # how many past days to fetch
        "batch_size": 1000,           # channels per batch (one process per batch)
        "max_parallel_batches": 4,    # processes running at the same time
        "max_threads": 64,            # threads per batch
        "max_pages": 500,             # safety cap on pages per channel
        "delay_min": 1.0,             # random delay between pages (seconds)
        "delay_max": 2.5,
        "http_max_retries": 5,        # give up on a page after this many failed requests
        "insert_batch_size": 50,      # rows per ClickHouse insert
    },
    "comments": {
        "limit": 36,                  # max comments per post
        "num_workers": 10,            # capped at the number of session files
    },
}

# Environment variables that seed values (e.g. from docker-compose).
_ENV_MAP = {
    ("clickhouse", "url"): "CLICKHOUSE_HTTP_URL",
    ("clickhouse", "user"): "CLICKHOUSE_USER",
    ("clickhouse", "password"): "CLICKHOUSE_PASSWORD",
    ("clickhouse", "database"): "CLICKHOUSE_DB",
}


def _coerce(value, default):
    """Cast ``value`` to the type of ``default`` (bool/int/float/str)."""
    if isinstance(default, bool):
        if isinstance(value, str):
            return value.strip().lower() in ("1", "true", "yes", "on")
        return bool(value)
    if isinstance(default, int):
        if value in ("", None):
            return 0
        return int(float(value))
    if isinstance(default, float):
        if value in ("", None):
            return 0.0
        return float(value)
    return "" if value is None else str(value)


def _merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for section, values in (override or {}).items():
        if section not in out or not isinstance(values, dict):
            continue
        for key, value in values.items():
            if key in out[section]:
                out[section][key] = _coerce(value, DEFAULTS[section][key])
    return out


def _env_layer() -> dict:
    layer: dict = {}
    for (section, key), env in _ENV_MAP.items():
        if os.environ.get(env):
            layer.setdefault(section, {})[key] = os.environ[env]
    return layer


def load_settings() -> dict:
    """Return the effective settings (fresh read every call)."""
    settings = _merge(DEFAULTS, _env_layer())
    if SETTINGS_PATH.exists():
        try:
            settings = _merge(settings, json.loads(SETTINGS_PATH.read_text(encoding="utf-8")))
        except (OSError, ValueError) as e:
            raise RuntimeError(f"Cannot read {SETTINGS_PATH}: {e}") from e
    return settings


def validate_settings(settings: dict) -> list[str]:
    errors = []
    p = settings["posts"]
    if p["days"] < 1:
        errors.append("posts.days must be >= 1")
    for key in ("batch_size", "max_parallel_batches", "max_threads", "max_pages", "insert_batch_size"):
        if p[key] < 1:
            errors.append(f"posts.{key} must be >= 1")
    if p["delay_min"] < 0 or p["delay_max"] < p["delay_min"]:
        errors.append("posts.delay_max must be >= posts.delay_min >= 0")
    if p["http_max_retries"] < 0:
        errors.append("posts.http_max_retries must be >= 0")
    c = settings["comments"]
    if c["limit"] < 1 or c["num_workers"] < 1:
        errors.append("comments.limit and comments.num_workers must be >= 1")
    if not settings["clickhouse"]["database"].replace("_", "").isalnum():
        errors.append("clickhouse.database may only contain letters, digits and _")
    return errors


def save_settings(data: dict) -> dict:
    """Validate, merge onto defaults and atomically write settings.json."""
    settings = _merge(load_settings(), data)
    errors = validate_settings(settings)
    if errors:
        raise ValueError("; ".join(errors))
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = SETTINGS_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(SETTINGS_PATH)
    return settings


def http_proxy_url(settings: dict) -> str:
    p = settings["http_proxy"]
    if not (p["host"] and p["port"]):
        return ""
    auth = f"{p['user']}:{p['password']}@" if p["user"] else ""
    return f"http://{auth}{p['host']}:{p['port']}"


def http_proxies(settings: dict) -> dict:
    url = http_proxy_url(settings)
    return {"http": url, "https": url} if url else {}


def mtproto_proxy(settings: dict):
    """Telethon ``proxy`` tuple, or None when no MTProto proxy is configured."""
    m = settings["mtproto_proxy"]
    if m["server"] and m["port"]:
        return (m["server"], m["port"], m["secret"])
    return None
