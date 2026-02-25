import logging
import os
import time
import json 
from concurrent.futures import ThreadPoolExecutor, as_completed, ProcessPoolExecutor
from multiprocessing import Manager
from utils.worker_posts import worker, load_channels_from_json

# ---------- Logging ----------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s]: %(message)s'
)
logger = logging.getLogger(__name__)

# ---------- Config ----------
BATCH_SIZE = 1000
MAX_THREADS = 64
MAX_PARALLEL_BATCHES = 4
OUTPUT_DIR = 'output/batches'


# ---------- Batch Processor ----------
def process_batch(batch_index, batch_channels, days, running_batches_counter):
    running_batches_counter.value += 1
    start_time = time.time()
    logger.info(f"[Batch {batch_index+1}] 🚀 Start | Channels: {len(batch_channels)} | Running batches: {running_batches_counter.value}")

    tasks = [(i + 1, len(batch_channels), ch) for i, ch in enumerate(batch_channels)]
    results_dict = {}

    with ThreadPoolExecutor(max_workers=min(MAX_THREADS, len(tasks))) as executor:
        futures = {executor.submit(worker, task, days=days): task for task in tasks}
        for future in as_completed(futures):
            try:
                result = future.result()
                if isinstance(result, tuple) and len(result) == 2:
                    channel, msgids = result
                    if msgids:
                        results_dict[channel] = msgids
                else:
                    logger.warning(f"[Batch {batch_index+1}] ⚠️ Unexpected result format: {result}")
            except Exception as e:
                logger.error(f"[Batch {batch_index+1}] ❌ Error in task: {e}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_file = os.path.join(OUTPUT_DIR, f'batch_{batch_index+1:03}.json')

    if results_dict:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results_dict, f, ensure_ascii=False, indent=2)
        total = sum(len(v) for v in results_dict.values())
        logger.info(f"[Batch {batch_index+1}] ✅ Saved {total} msgids → {output_file}")
    else:
        logger.warning(f"[Batch {batch_index+1}] ⚠️ No results found")

    duration = time.time() - start_time
    running_batches_counter.value -= 1
    logger.info(f"[Batch {batch_index+1}] ⏱️ Finished in {duration:.2f} seconds | Running batches now: {running_batches_counter.value}")
    return f"Batch {batch_index+1} done in {duration:.2f}s"


# ---------- Wrapper ----------
def batch_wrapper(args):
    result = process_batch(*args)
    logger.info(f"[Wrapper] ✅ Finished batch {args[0]+1}")
    return result


# ---------- Main ----------
def main(channels_file='input/channels.json', days=3):
    channels = load_channels_from_json(channels_file)
    channels = list(filter(None, channels))
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    total_batches = (len(channels) + BATCH_SIZE - 1) // BATCH_SIZE
    logger.info(f"📦 Total: {len(channels)} channels | Batches: {total_batches} | Parallel: {MAX_PARALLEL_BATCHES}")

    batches_raw = [
        (i, channels[i * BATCH_SIZE: (i + 1) * BATCH_SIZE], days)
        for i in range(total_batches)
    ]

    with Manager() as manager:
        running_batches_counter = manager.Value('i', 0)

        batches = [
            (batch_index, batch_channels, days, running_batches_counter)
            for (batch_index, batch_channels, days) in batches_raw
        ]

        with ProcessPoolExecutor(max_workers=MAX_PARALLEL_BATCHES) as executor:
            futures = [executor.submit(batch_wrapper, b) for b in batches]
            results = []
            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"❌ Error in batch execution: {e}")

    logger.info("🎉 All batches completed.")
    for r in results:
        logger.info(r)


# ---------- CLI ----------
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Multi-Batch Parallel Telegram Scraper")
    parser.add_argument('--channels', type=str, default='input/channels.json', help='Path to channel list')
    parser.add_argument('--days', type=int, default=1, help='How many days of posts to fetch')
    args = parser.parse_args()

    main(channels_file=args.channels, days=args.days)
