import os
import sys
import subprocess
import logging
import json
from pathlib import Path
from itertools import cycle
import argparse

from settings import load_settings

# ---------- Logging Configuration ----------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ---------- Configurations ----------
_comments_cfg = load_settings()["comments"]
SESSION_DIR = "session"                         # Directory containing Telegram session files
WORKER_MODULE = "utils.worker_comments_reactions"
NUM_WORKERS = _comments_cfg["num_workers"]      # Number of workers to launch
BATCH_DIR = "output/batches"                    # batch_XXX.json files written by get_posts.py
TMP_BATCH_DIR = "output/tmp_batches"            # worker_batch_N.txt files for each worker

os.makedirs(BATCH_DIR, exist_ok=True)
os.makedirs(TMP_BATCH_DIR, exist_ok=True)


def load_data_from_json(directory=BATCH_DIR):
    all_items = []
    json_files = sorted(f for f in os.listdir(directory) if f.endswith('.json'))

    if not json_files:
        logger.warning(f"⚠️ No JSON files found in directory: {directory}")
        return []

    logger.info(f"📄 Found {len(json_files)} JSON file(s): {json_files}")

    for json_file in json_files:
        json_path = os.path.join(directory, json_file)
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for channel, msgid_list in data.items():
                for msgid in msgid_list:
                    all_items.append((channel, str(msgid)))
        except Exception as e:
            logger.error(f"❌ Failed to load {json_path}: {e}")

    return all_items


def split_into_chunks(data, n):
    chunks = [[] for _ in range(n)]
    for item, chunk in zip(data, cycle(chunks)):
        chunk.append(item)
    return chunks


def save_chunks_to_files(chunks, out_dir):
    paths = []
    for idx, chunk in enumerate(chunks):
        path = os.path.join(out_dir, f"worker_batch_{idx}.txt")
        with open(path, 'w', encoding='utf-8') as f:
            for channel, msgid in chunk:
                f.write(f"{channel} {msgid}\n")
        paths.append(path)
    return paths


def worker_command(session_path, batch_file, limit):
    return [sys.executable, "-m", WORKER_MODULE,
            "--session", session_path, "--batch", batch_file, "--limit", str(limit)]


def launch_tmux_workers(session_files, batch_files, limit):
    for idx, batch_file in enumerate(batch_files):
        session_name = f"tg_worker_{idx}"
        session_path = session_files[idx % len(session_files)]

        cmd = (
            f'tmux new-session -d -s {session_name} '
            f'"{" ".join(worker_command(session_path, batch_file, limit))}"'
        )
        logger.info(f"🚀 Launching tmux '{session_name}' → session: '{session_path}', batch: '{batch_file}', limit: {limit}")
        try:
            subprocess.run(cmd, shell=True, check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to launch tmux session '{session_name}': {e}")


def run_subprocess_workers(session_files, batch_files, limit, log_dir):
    """Run workers as child processes (one log file each) and wait for all of them."""
    os.makedirs(log_dir, exist_ok=True)
    procs = []
    for idx, batch_file in enumerate(batch_files):
        session_path = session_files[idx % len(session_files)]
        log_path = os.path.join(log_dir, f"worker_{idx}.log")
        logger.info(f"🚀 Launching worker {idx} → session: '{session_path}', batch: '{batch_file}', log: '{log_path}'")
        log_file = open(log_path, 'ab')
        proc = subprocess.Popen(
            worker_command(session_path, batch_file, limit),
            stdout=log_file, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
        procs.append((idx, proc, log_file))

    failed = 0
    for idx, proc, log_file in procs:
        rc = proc.wait()
        log_file.close()
        if rc == 0:
            logger.info(f"✅ Worker {idx} finished")
        else:
            failed += 1
            logger.error(f"❌ Worker {idx} exited with code {rc}")
    return failed


def main():
    parser = argparse.ArgumentParser(description="Launch workers for Telegram comments/reactions.")
    parser.add_argument('--limit', type=int, default=_comments_cfg["limit"], help='Limit for fetching comments per message')
    parser.add_argument('--mode', choices=['tmux', 'subprocess'], default='tmux',
                        help='tmux: detached tmux sessions (default). subprocess: run workers here and wait for them.')
    parser.add_argument('--log-dir', default='logs/workers', help='Worker log directory (subprocess mode)')
    args = parser.parse_args()

    logger.info("📂 Reading session files...")
    session_files = sorted(str(f) for f in Path(SESSION_DIR).glob("telegram_*.session"))
    if not session_files:
        logger.error("❌ No session files found in 'session/' directory.")
        return 1
    logger.info(f"✅ Found {len(session_files)} session(s).")

    logger.info(f"📥 Loading channels and msgids from JSON: {BATCH_DIR}")
    all_msgids = load_data_from_json()
    if not all_msgids:
        logger.error("❌ No msgids found in JSON input.")
        return 1
    logger.info(f"📦 Total msgid pairs loaded: {len(all_msgids)}")

    # A Telethon .session file is SQLite; sharing one between concurrent processes
    # causes "database is locked" errors, so never run more workers than sessions.
    num_workers = min(NUM_WORKERS, len(session_files))
    if num_workers < NUM_WORKERS:
        logger.warning(f"⚠️ Only {len(session_files)} session(s): using {num_workers} workers instead of {NUM_WORKERS}")

    logger.info(f"📤 Splitting into {num_workers} chunks...")
    chunks = split_into_chunks(all_msgids, num_workers)
    batch_paths = save_chunks_to_files(chunks, TMP_BATCH_DIR)

    if args.mode == 'subprocess':
        failed = run_subprocess_workers(session_files, batch_paths, args.limit, args.log_dir)
        logger.info(f"🏁 All workers finished ({failed} failed).")
        return 1 if failed == num_workers else 0

    logger.info("🚀 Launching tmux workers...")
    launch_tmux_workers(session_files, batch_paths, args.limit)
    logger.info("✅ All workers launched.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
