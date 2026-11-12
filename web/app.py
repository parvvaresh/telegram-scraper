"""Web control panel for the Telegram scraper: config, run control, live progress, data."""

import json
import os
import secrets
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import jdatetime
import requests
from bs4 import BeautifulSoup
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from settings import BASE_DIR, CHANNELS_PATH, SETTINGS_PATH, http_proxies, load_settings, save_settings
from web import clickhouse as ch
from web.progress import comments_progress, posts_progress
from web.runner import runner

DIST = BASE_DIR / "frontend" / "dist"
WEB_USER = os.environ.get("WEB_USER", "admin")
WEB_PASSWORD = os.environ.get("WEB_PASSWORD", "")
_basic = HTTPBasic(auto_error=False)


def require_auth(creds: Optional[HTTPBasicCredentials] = Depends(_basic)):
    if not WEB_PASSWORD:
        return
    ok = creds and secrets.compare_digest(creds.username.encode(), WEB_USER.encode()) \
        and secrets.compare_digest(creds.password.encode(), WEB_PASSWORD.encode())
    if not ok:
        raise HTTPException(401, "Unauthorized", headers={"WWW-Authenticate": "Basic"})


app = FastAPI(title="Telegram Scraper Panel", dependencies=[Depends(require_auth)])


def _bad(e: Exception, code: int = 400):
    raise HTTPException(code, str(e))


if (DIST / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")


@app.get("/", include_in_schema=False)
def index():
    if (DIST / "index.html").exists():
        return FileResponse(DIST / "index.html")
    return HTMLResponse(
        "<h3>Frontend is not built yet.</h3><p>Run <code>cd frontend &amp;&amp; npm install &amp;&amp; npm run build</code>, "
        "then reload — or use the dev server: <code>npm run dev</code> (http://localhost:5173).</p>"
        "<p>The API is up: <a href='/docs'>/docs</a></p>", status_code=503)


# ---------------- summary for the dashboard ----------------
@app.get("/api/summary")
def summary():
    s = load_settings()
    try:
        channels = len(json.loads(CHANNELS_PATH.read_text(encoding="utf-8")).get("channels", []))
    except (OSError, ValueError):
        channels = 0
    runs = runner.list_runs(10)
    return {
        "channels": channels,
        "sessions": len(list((BASE_DIR / "session").glob("telegram_*.session"))),
        "telegram_configured": bool(s["telegram"]["api_id"] and s["telegram"]["api_hash"]),
        "http_proxy": bool(http_proxies(s)),
        "mtproto_proxy": bool(s["mtproto_proxy"]["server"]),
        "running": runner.is_running(),
        "runs": runs,
        "settings_saved": SETTINGS_PATH.exists(),
    }


# ---------------- settings ----------------
@app.get("/api/settings")
def get_settings():
    return {"settings": load_settings(), "path": str(SETTINGS_PATH.relative_to(BASE_DIR))
            if SETTINGS_PATH.is_relative_to(BASE_DIR) else str(SETTINGS_PATH),
            "exists": SETTINGS_PATH.exists()}


@app.put("/api/settings")
def put_settings(data: dict):
    try:
        return {"settings": save_settings(data)}
    except ValueError as e:
        _bad(e)


@app.get("/api/sessions")
def sessions():
    out = []
    for f in sorted((BASE_DIR / "session").glob("telegram_*.session")):
        st = f.stat()
        out.append({"name": f.name, "size": st.st_size,
                    "modified": datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds")})
    return out


# ---------------- channels ----------------
def _normalize(entry: str) -> Optional[str]:
    from utils.worker_posts import normalize_channel
    return normalize_channel(entry)


class Channels(BaseModel):
    channels: list[str]


@app.get("/api/channels")
def get_channels():
    try:
        raw = json.loads(CHANNELS_PATH.read_text(encoding="utf-8")).get("channels", [])
    except FileNotFoundError:
        raw = []
    except ValueError as e:
        _bad(f"input/channels.json is not valid JSON: {e}", 500)
    return {"channels": raw, "normalized": [_normalize(c) for c in raw]}


@app.put("/api/channels")
def put_channels(body: Channels):
    seen, cleaned = set(), []
    for c in body.channels:
        c = c.strip()
        name = _normalize(c)
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())
        cleaned.append(c)
    CHANNELS_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = CHANNELS_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps({"channels": cleaned}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(CHANNELS_PATH)
    return get_channels()


# ---------------- runs ----------------
class StartRun(BaseModel):
    mode: str = "all"
    days: Optional[int] = None
    limit: Optional[int] = None


@app.post("/api/run")
def start_run(body: StartRun):
    try:
        return runner.start(body.mode, body.days, body.limit)
    except RuntimeError as e:
        _bad(e, 409)
    except ValueError as e:
        _bad(e)


@app.post("/api/stop")
def stop_run():
    try:
        runner.stop()
    except RuntimeError as e:
        _bad(e, 409)
    return {"ok": True}


@app.get("/api/runs")
def list_runs(limit: int = 50):
    return runner.list_runs(min(max(limit, 1), 500))


def _run_view(run: dict) -> dict:
    run_dir = runner.run_dir(run["id"])
    names = [p["name"] for p in run["phases"]]
    files = [f"{n}.log" for n in names if (run_dir / f"{n}.log").exists()]
    if (run_dir / "workers").is_dir():
        files += [f"workers/{p.name}" for p in
                  sorted((run_dir / "workers").glob("*.log"), key=lambda p: int(p.stem.split("_")[-1]))]
    return {
        "run": run,
        "running": runner.is_running() and runner.current["id"] == run["id"],
        "progress": {
            "posts": posts_progress(run_dir) if "posts" in names else None,
            "comments": comments_progress(run_dir) if "comments" in names else None,
        },
        "files": files,
        "server_time": datetime.now().isoformat(timespec="seconds"),
    }


@app.get("/api/status")
def status(run_id: Optional[str] = None):
    try:
        if run_id:
            run = runner.load_run(run_id)
        else:
            run = runner.current or next(iter(runner.list_runs(1)), None)
    except (OSError, ValueError):
        _bad("run not found", 404)
    if not run:
        return {"run": None, "running": False}
    return _run_view(run)


@app.get("/api/runs/{run_id}/log")
def run_log(run_id: str, file: str, offset: int = -1):
    try:
        run_dir = runner.run_dir(run_id)
    except ValueError as e:
        _bad(e)
    path = (run_dir / file).resolve()
    if not path.is_relative_to(run_dir) or path.suffix != ".log" or not path.exists():
        _bad("log not found", 404)
    size = path.stat().st_size
    if offset < 0 or offset > size:
        offset = max(0, size - 64 * 1024)
    with open(path, "rb") as f:
        f.seek(offset)
        data = f.read(256 * 1024)
    return {"text": data.decode("utf-8", "replace"), "offset": offset + len(data), "size": size}


# ---------------- preview: scrape one page exactly like the post scraper ----------------
@app.get("/api/preview")
def preview(channel: str, before: Optional[int] = None):
    from fetch_tools.configDB import HEADERS
    from fetch_tools.utils import _parse_post_element

    name = _normalize(channel)
    if not name:
        _bad("invalid channel")
    settings = load_settings()
    proxies = http_proxies(settings)
    url = f"https://t.me/s/{name}" + (f"?before={before}" if before else "")
    t0 = time.monotonic()
    try:
        r = requests.get(url, headers=HEADERS, proxies=proxies or None, timeout=30)
    except requests.RequestException as e:
        return {"ok": False, "url": url, "proxy": bool(proxies), "error": str(e),
                "elapsed_ms": int((time.monotonic() - t0) * 1000)}
    elapsed = int((time.monotonic() - t0) * 1000)
    soup = BeautifulSoup(r.text, "html.parser")
    posts = []
    for el in soup.find_all("div", class_="tgme_widget_message_wrap"):
        info = _parse_post_element(el)
        if not info:
            continue
        posts.append({
            "msgid": info["msgid"],
            "date": info["date"].isoformat(),
            "shdate": jdatetime.datetime.fromgregorian(date=info["date"]).strftime("%Y-%m-%d %H:%M"),
            "views": info["views"],
            "type": info["type"],
            "text": info["text"][:600],
        })
    posts.sort(key=lambda p: p["msgid"], reverse=True)
    title = soup.find("div", class_="tgme_channel_info_header_title")
    return {
        "ok": r.ok, "status": r.status_code, "url": url, "final_url": r.url,
        "proxy": bool(proxies), "elapsed_ms": elapsed, "bytes": len(r.content),
        "channel": name, "title": title.get_text(strip=True) if title else "",
        "posts": posts, "next_before": min((p["msgid"] for p in posts), default=None),
    }


# ---------------- ClickHouse ----------------
def _ch(fn, *args):
    try:
        return fn(*args)
    except ch.ClickHouseError as e:
        _bad(e, 502)


@app.post("/api/db/test")
def db_test(data: Optional[dict] = None):
    cfg = load_settings()["clickhouse"]
    if data:
        cfg = {**cfg, **{k: v for k, v in data.items() if k in cfg}}
    return _ch(ch.ping, cfg)


@app.post("/api/db/init")
def db_init():
    return {"statements": _ch(ch.init_schema)}


@app.get("/api/db/overview")
def db_overview():
    return _ch(ch.overview)


@app.get("/api/db/channels")
def db_channels():
    return _ch(ch.channels)


@app.get("/api/db/posts")
def db_posts(channel: str = "", limit: int = 30):
    return _ch(ch.recent_posts, channel, min(limit, 200))


@app.get("/api/db/comments")
def db_comments(channel: str = "", limit: int = 30):
    return _ch(ch.recent_comments, channel, min(limit, 200))
