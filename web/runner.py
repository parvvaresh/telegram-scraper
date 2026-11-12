"""Starts/stops scraper runs as child processes and records their state on disk."""

import json
import os
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

from settings import BASE_DIR, load_settings
from web.progress import run_summary

RUNS_DIR = BASE_DIR / "logs" / "runs"
BATCH_DIR = BASE_DIR / "output" / "batches"
MODES = {"all": ["posts", "comments"], "posts": ["posts"], "comments": ["comments"]}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _alive(pid) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _killpg(pid: int, sig) -> None:
    try:
        os.killpg(pid, sig)
    except (ProcessLookupError, PermissionError):
        pass


class Runner:
    def __init__(self):
        self.lock = threading.Lock()
        self.current: dict | None = None
        self.proc: subprocess.Popen | None = None
        self.pgid: int | None = None
        self.stop_requested = False
        RUNS_DIR.mkdir(parents=True, exist_ok=True)
        self._recover()

    # ---------- persistence ----------
    def run_dir(self, run_id: str) -> Path:
        path = (RUNS_DIR / run_id).resolve()
        if path.parent != RUNS_DIR.resolve():
            raise ValueError("invalid run id")
        return path

    def _save(self, run: dict) -> None:
        path = RUNS_DIR / run["id"] / "run.json"
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(run, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)

    def load_run(self, run_id: str) -> dict:
        if self.current and self.current["id"] == run_id:
            return self.current
        return json.loads((self.run_dir(run_id) / "run.json").read_text(encoding="utf-8"))

    def list_runs(self, limit: int = 50) -> list[dict]:
        runs = []
        for d in sorted(RUNS_DIR.iterdir(), reverse=True):
            if len(runs) >= limit:
                break
            try:
                runs.append(self.load_run(d.name))
            except (OSError, ValueError):
                continue
        return runs

    def _recover(self) -> None:
        """After a panel restart: re-attach to a run whose process is still alive."""
        for run in self.list_runs(5):
            if run.get("status") != "running":
                continue
            phase = next((p for p in run["phases"] if p["status"] == "running"), None)
            if phase and _alive(phase.get("pid")):
                self.current = run
                self.pgid = phase["pid"]
                threading.Thread(target=self._watch_detached, args=(run, phase), daemon=True).start()
                return
            run["status"] = "interrupted"
            run["finished_at"] = run.get("finished_at") or _now()
            for p in run["phases"]:
                if p["status"] in ("running", "pending"):
                    p["status"] = "interrupted"
            self._save(run)

    def _watch_detached(self, run: dict, phase: dict) -> None:
        while _alive(phase["pid"]):
            time.sleep(2)
        phase["status"] = "stopped" if self.stop_requested else "finished"
        phase["finished_at"] = _now()
        for p in run["phases"]:
            if p["status"] == "pending":
                p["status"] = "skipped"
        run["status"] = "stopped" if self.stop_requested else "interrupted"
        run["finished_at"] = _now()
        self._attach_summary(run)
        self._save(run)

    # ---------- control ----------
    def is_running(self) -> bool:
        return bool(self.current and self.current["status"] == "running")

    def start(self, mode: str, days: int | None = None, limit: int | None = None) -> dict:
        if mode not in MODES:
            raise ValueError(f"unknown mode: {mode}")
        settings = load_settings()
        days = int(days or settings["posts"]["days"])
        limit = int(limit or settings["comments"]["limit"])
        with self.lock:
            if self.is_running():
                raise RuntimeError("A run is already in progress")
            run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
            (RUNS_DIR / run_id).mkdir(parents=True, exist_ok=False)
            run = {
                "id": run_id,
                "mode": mode,
                "params": {"days": days, "limit": limit},
                "status": "running",
                "started_at": _now(),
                "finished_at": None,
                "phases": [
                    {"name": p, "status": "pending", "pid": None, "returncode": None,
                     "started_at": None, "finished_at": None}
                    for p in MODES[mode]
                ],
            }
            self.current = run
            self.stop_requested = False
            self._save(run)
        threading.Thread(target=self._execute, args=(run,), daemon=True).start()
        return run

    def stop(self) -> None:
        if not self.is_running():
            raise RuntimeError("Nothing is running")
        self.stop_requested = True
        pgid = self.pgid
        if pgid:
            _killpg(pgid, signal.SIGTERM)
            threading.Timer(8, _killpg, args=(pgid, signal.SIGKILL)).start()

    def _command(self, phase: str, run: dict, run_dir: Path) -> list[str]:
        if phase == "posts":
            return [sys.executable, "get_posts.py", "--channels", "input/channels.json",
                    "--days", str(run["params"]["days"])]
        return [sys.executable, "get_comments_reactions.py", "--limit", str(run["params"]["limit"]),
                "--mode", "subprocess", "--log-dir", str(run_dir / "workers")]

    def _execute(self, run: dict) -> None:
        run_dir = RUNS_DIR / run["id"]
        for phase in run["phases"]:
            if self.stop_requested:
                phase["status"] = "skipped"
                continue
            if phase["name"] == "posts":
                # Stale batch files would otherwise be re-processed by the comments phase
                for f in BATCH_DIR.glob("batch_*.json"):
                    f.unlink()
            with open(run_dir / f"{phase['name']}.log", "ab") as log:
                proc = subprocess.Popen(
                    self._command(phase["name"], run, run_dir),
                    cwd=BASE_DIR, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                    start_new_session=True, env={**os.environ, "PYTHONUNBUFFERED": "1"},
                )
            self.proc, self.pgid = proc, proc.pid
            phase.update(status="running", pid=proc.pid, started_at=_now())
            self._save(run)

            rc = proc.wait()
            if self.stop_requested:
                _killpg(proc.pid, signal.SIGTERM)  # leftover children (workers / pool)
            phase.update(returncode=rc, finished_at=_now(),
                         status="stopped" if self.stop_requested else ("done" if rc == 0 else "failed"))
            self._save(run)
            if phase["status"] != "done":
                for p in run["phases"]:
                    if p["status"] == "pending":
                        p["status"] = "skipped"
                break

        statuses = {p["status"] for p in run["phases"]}
        if self.stop_requested:
            run["status"] = "stopped"
        elif statuses == {"done"}:
            run["status"] = "done"
        else:
            run["status"] = "failed"
        run["finished_at"] = _now()
        self._attach_summary(run)
        self.proc = self.pgid = None
        self._save(run)

    def _attach_summary(self, run: dict) -> None:
        try:
            run["summary"] = run_summary(RUNS_DIR / run["id"], [p["name"] for p in run["phases"]])
        except Exception as e:  # never let a summary problem break run bookkeeping
            run["summary"] = {"error": str(e)}


runner = Runner()
