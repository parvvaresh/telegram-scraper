import os
import subprocess
import logging
import json
from pathlib import Path
from itertools import cycle
import argparse

# ---------- Logging Configuration ----------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ---------- Configurations ----------
SESSION_DIR = "session"                         # Directory containing Telegram session files
WORKER_SCRIPT = "python3 -m utils.worker_comments_reactions"  # Worker script with module mode
NUM_WORKERS = 10                                # Number of tmux workers to launch
TMP_BATCH_DIR = "output/batches"                # Directory to store batch files and JSON input files

os.makedirs(TMP_BATCH_DIR, exist_ok=True)

def load_data_from_json(directory=TMP_BATCH_DIR):
    all_items = []
    json_files = [f for f in os.listdir(directory) if f.endswith('.json')]

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

def launch_tmux_workers(session_files, batch_files, limit):
    for idx, batch_file in enumerate(batch_files):
        session_name = f"tg_worker_{idx}"
        session_path = session_files[idx % len(session_files)]

        cmd = (
            f'tmux new-session -d -s {session_name} '
            f'"{WORKER_SCRIPT} --session {session_path} --batch {batch_file} --limit {limit}"'
        )
        logger.info(f"🚀 Launching tmux '{session_name}' → session: '{session_path}', batch: '{batch_file}', limit: {limit}")
        try:
            subprocess.run(cmd, shell=True, check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to launch tmux session '{session_name}': {e}")

def main():
    parser = argparse.ArgumentParser(description="Launch tmux workers for Telegram crawler.")
    parser.add_argument('--limit', type=int, default=36, help='Limit for fetching comments per message')
    args = parser.parse_args()

    logger.info("📂 Reading session files...")
    session_files = sorted(str(f) for f in Path(SESSION_DIR).glob("telegram_*.session"))
    if not session_files:
        logger.error("❌ No session files found in 'session/' directory.")
        return
    logger.info(f"✅ Found {len(session_files)} session(s).")

    logger.info(f"📥 Loading channels and msgids from JSON: {TMP_BATCH_DIR}")
    all_msgids = load_data_from_json()
    if not all_msgids:
        logger.error("❌ No msgids found in JSON input.")
        return
    logger.info(f"📦 Total msgid pairs loaded: {len(all_msgids)}")

    logger.info(f"📤 Splitting into {NUM_WORKERS} chunks...")
    chunks = split_into_chunks(all_msgids, NUM_WORKERS)
    batch_paths = save_chunks_to_files(chunks, TMP_BATCH_DIR)

    logger.info("🚀 Launching tmux workers...")
    launch_tmux_workers(session_files, batch_paths, args.limit)

    logger.info("✅ All workers launched.")

if __name__ == '__main__':
    main()
