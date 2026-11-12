"""Incremental log parsers that turn scraper logs into progress numbers for the UI."""

import re
from collections import OrderedDict, deque
from pathlib import Path

RE_LEVEL = re.compile(r"\[(WARNING|ERROR|CRITICAL)\]")
RE_INSERTED = re.compile(r"Inserted (\d+) rows into [\w]+\.(\w+)")
RE_INSERT_ERR = re.compile(r"Error inserting batch into (\w+)")

# get_posts.py / utils/worker_posts.py / fetch_tools/posts.py
RE_TOTAL = re.compile(r"Total: (\d+) channels \| Batches: (\d+)")
RE_FETCHING = re.compile(r"\[\+\] \(\d+/\d+\) Fetching channel: @(\S+)")
RE_POST = re.compile(r"\[\+\] @(\S+) post fetched: msgid=(\d+)")
RE_DONE = re.compile(r"\[✓\] \(\d+/\d+\) Done: @(\S+) \| Posts: (\d+)")
RE_FAILED = re.compile(r"\[✗\] \(\d+/\d+\) Error in @(\S+)")
RE_BATCH_DONE = re.compile(r"\[Batch (\d+)\] ⏱️ Finished")
RE_HTTP_ERR = re.compile(r"HTTP error fetching")

# get_comments_reactions.py
RE_PAIRS = re.compile(r"Total msgid pairs loaded: (\d+)")
RE_SESSIONS = re.compile(r"Found (\d+) session")
RE_LAUNCH = re.compile(r"Launching worker (\d+) → session: '([^']+)'")

# utils/worker_comments_reactions.py
RE_PROGRESS = re.compile(r"📊 progress (\d+)/(\d+) messages")
RE_PROCESSING = re.compile(r"Processing (\d+) messages from: (\S+)")
RE_FLOOD = re.compile(r"[Ff]lood wait.*?(\d+) seconds")

MAX_READ = 8 * 1024 * 1024


class LogParser:
    """Reads only the new bytes of a log file on every update()."""

    def __init__(self, path: Path):
        self.path = path
        self.offset = 0
        self.partial = b""
        self.state = self.initial_state()

    def initial_state(self) -> dict:
        return {
            "inserted": {},
            "insert_errors": 0,
            "warnings": 0,
            "errors": 0,
            "issues": deque(maxlen=40),
        }

    def update(self) -> dict:
        try:
            size = self.path.stat().st_size
        except FileNotFoundError:
            return self.state
        if size < self.offset:  # file was truncated / replaced
            self.__init__(self.path)
        if size > self.offset:
            with open(self.path, "rb") as f:
                f.seek(self.offset)
                data = f.read(MAX_READ)
            self.offset += len(data)
            lines = (self.partial + data).split(b"\n")
            self.partial = lines.pop()
            for raw in lines:
                self._feed_common(raw.decode("utf-8", "replace").rstrip("\r"))
        return self.state

    def _feed_common(self, line: str):
        s = self.state
        m = RE_INSERTED.search(line)
        if m:
            table = m.group(2).replace("_buffer", "")
            s["inserted"][table] = s["inserted"].get(table, 0) + int(m.group(1))
        if RE_INSERT_ERR.search(line):
            s["insert_errors"] += 1
        lvl = RE_LEVEL.search(line)
        if lvl:
            if lvl.group(1) == "WARNING":
                s["warnings"] += 1
            else:
                s["errors"] += 1
            s["issues"].append(line[:400])
        self.feed(line)

    def feed(self, line: str):
        pass

    def snapshot(self) -> dict:
        out = dict(self.update())
        out["issues"] = list(out["issues"])
        return out


class PostsParser(LogParser):
    def initial_state(self):
        s = super().initial_state()
        s.update({
            "total_channels": 0,
            "total_batches": 0,
            "batches_done": 0,
            "channels_done": 0,
            "channels_failed": 0,
            "posts_fetched": 0,
            "http_errors": 0,
            "active": OrderedDict(),       # channel -> posts fetched so far
            "recent": deque(maxlen=25),    # [channel, posts, ok]
        })
        return s

    def feed(self, line):
        s = self.state
        m = RE_POST.search(line)
        if m:
            s["posts_fetched"] += 1
            ch = m.group(1)
            if ch in s["active"]:
                s["active"][ch] += 1
            return
        m = RE_FETCHING.search(line)
        if m:
            s["active"][m.group(1)] = 0
            return
        m = RE_DONE.search(line)
        if m:
            s["channels_done"] += 1
            s["active"].pop(m.group(1), None)
            s["recent"].append([m.group(1), int(m.group(2)), True])
            return
        m = RE_FAILED.search(line)
        if m:
            s["channels_failed"] += 1
            s["active"].pop(m.group(1), None)
            s["recent"].append([m.group(1), 0, False])
            return
        if RE_HTTP_ERR.search(line):
            s["http_errors"] += 1
            return
        m = RE_TOTAL.search(line)
        if m:
            s["total_channels"], s["total_batches"] = int(m.group(1)), int(m.group(2))
            return
        if RE_BATCH_DONE.search(line):
            s["batches_done"] += 1

    def snapshot(self):
        out = super().snapshot()
        out["active"] = [[k, v] for k, v in out["active"].items()][:64]
        out["recent"] = list(reversed(out["recent"]))
        return out


class CoordinatorParser(LogParser):
    def initial_state(self):
        s = super().initial_state()
        s.update({"total_pairs": 0, "sessions": 0, "workers": {}})
        return s

    def feed(self, line):
        s = self.state
        m = RE_PAIRS.search(line)
        if m:
            s["total_pairs"] = int(m.group(1))
            return
        m = RE_SESSIONS.search(line)
        if m:
            s["sessions"] = int(m.group(1))
            return
        m = RE_LAUNCH.search(line)
        if m:
            s["workers"][m.group(1)] = m.group(2)


class WorkerParser(LogParser):
    def initial_state(self):
        s = super().initial_state()
        s.update({"status": "starting", "done": 0, "total": 0, "channel": "", "flood_waits": 0, "flood_seconds": 0})
        return s

    def feed(self, line):
        s = self.state
        m = RE_PROGRESS.search(line)
        if m:
            s["done"], s["total"] = int(m.group(1)), int(m.group(2))
            if s["status"] == "starting":
                s["status"] = "running"
            return
        m = RE_PROCESSING.search(line)
        if m:
            s["channel"] = m.group(2)
            return
        m = RE_FLOOD.search(line)
        if m:
            s["flood_waits"] += 1
            s["flood_seconds"] += int(m.group(1))
            return
        if "Client started" in line:
            s["status"] = "running"
        elif "Finished processing batch" in line:
            s["status"] = "done"
            s["channel"] = ""
        elif "Fatal error" in line:
            s["status"] = "failed"


_cache: dict = {}


def _parser(cls, path: Path) -> LogParser:
    key = (cls.__name__, str(path))
    if key not in _cache:
        _cache[key] = cls(path)
    return _cache[key]


def merge_inserted(*parts: dict) -> dict:
    out: dict = {}
    for p in parts:
        for k, v in p.items():
            out[k] = out.get(k, 0) + v
    return out


def posts_progress(run_dir: Path) -> dict:
    return _parser(PostsParser, run_dir / "posts.log").snapshot()


def comments_progress(run_dir: Path) -> dict:
    coord = _parser(CoordinatorParser, run_dir / "comments.log").snapshot()
    workers = []
    issues = list(coord["issues"])
    inserted = [coord["inserted"]]
    for path in sorted((run_dir / "workers").glob("worker_*.log"), key=lambda p: int(p.stem.split("_")[1])):
        idx = path.stem.split("_")[1]
        w = _parser(WorkerParser, path).snapshot()
        inserted.append(w["inserted"])
        issues.extend(f"[worker {idx}] {line}" for line in w["issues"][-10:])
        workers.append({
            "id": int(idx),
            "session": coord["workers"].get(idx, ""),
            "status": w["status"],
            "done": w["done"],
            "total": w["total"],
            "channel": w["channel"],
            "flood_waits": w["flood_waits"],
            "flood_seconds": w["flood_seconds"],
            "errors": w["errors"],
            "warnings": w["warnings"],
        })
    return {
        "total_pairs": coord["total_pairs"],
        "sessions": coord["sessions"],
        "done": sum(w["done"] for w in workers),
        "workers": workers,
        "inserted": merge_inserted(*inserted),
        "errors": coord["errors"] + sum(w["errors"] for w in workers),
        "warnings": coord["warnings"] + sum(w["warnings"] for w in workers),
        "issues": issues[-40:],
    }


def run_summary(run_dir: Path, phases: list[str]) -> dict:
    """Compact numbers stored in run.json when a run ends (shown in the history page)."""
    out: dict = {"errors": 0, "warnings": 0, "inserted": {}}
    parts = []
    if "posts" in phases:
        p = posts_progress(run_dir)
        out.update(total_channels=p["total_channels"], channels_done=p["channels_done"],
                   channels_failed=p["channels_failed"], posts_fetched=p["posts_fetched"],
                   http_errors=p["http_errors"])
        parts.append(p)
    if "comments" in phases:
        c = comments_progress(run_dir)
        out.update(total_pairs=c["total_pairs"], messages_done=c["done"], workers=len(c["workers"]),
                   flood_waits=sum(w["flood_waits"] for w in c["workers"]))
        parts.append(c)
    for part in parts:
        out["errors"] += part["errors"]
        out["warnings"] += part["warnings"]
    out["inserted"] = merge_inserted(*(part["inserted"] for part in parts))
    return out
