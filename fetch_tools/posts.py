import logging
import requests
import time
import random
from datetime import datetime, timedelta
from typing import List, Tuple

import jdatetime
from bs4 import BeautifulSoup

from salnama import taghvim
from config import proxies
from .configDB import HEADERS
from .utils import insert_clickhouse_batch, create_http_session, _parse_post_element
# -------------------- Logger Configuration --------------------
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# -------------------- Constants --------------------
BATCH_SIZE = 50
DELAY_RANGE = (1.0, 2.5)
jalali_calendar = taghvim.Jalali()


def fetch_and_insert_posts(channel: str, days: int = 3) -> Tuple[str, List[str]]:
    """
    Fetches posts from a Telegram channel for the last `days` days,
    inserts them into ClickHouse in batches, and returns collected msgids.

    Args:
        channel (str): Telegram channel username.
        days (int): Number of past days to fetch posts for.

    Returns:
        Tuple[str, List[str]]: Channel name and list of collected message IDs.
    """
    if not isinstance(channel, str) or not channel.strip():
        logger.error("Invalid channel name provided.")
        return (channel, [])

    today = datetime.utcnow().date()
    start_date = today - timedelta(days=days)

    http = create_http_session(proxies)
    base_url = f'https://t.me/s/{channel}'
    current_msgid = None
    posts_batch = []
    collected_msgids = []
    seen_msgids = set()  # Track all msgids processed in this run

    previous_msgid = None
    repeat_count = 0
    MAX_REPEAT = 3  # Max consecutive repeats of same msgid before break

    MAX_PAGES = 500
    page_count = 0

    logger.info(f"🚀 Starting scrape for channel: {channel} | Range: last {days} days")

    while True:
        if page_count >= MAX_PAGES:
            logger.warning(f"⚠️ Max pages ({MAX_PAGES}) reached. Breaking loop to avoid infinite scraping.")
            break

        url = f"{base_url}?before={current_msgid}" if current_msgid else base_url
        logger.debug(f"Fetching page: {url}")

        # Retry with exponential backoff on HTTP errors
        backoff = 1
        while True:
            try:
                response = http.get(url, headers=HEADERS, timeout=30)
                response.raise_for_status()
                break
            except requests.RequestException as e:
                logger.warning(f"HTTP error fetching {url}: {e} | Retrying in {backoff}s")
                time.sleep(backoff)
                backoff = min(backoff * 2, 60)

        soup = BeautifulSoup(response.text, 'html.parser')
        elements = soup.find_all('div', class_='tgme_widget_message_wrap')

        if not elements:
            logger.info("📭 No more posts found. Exiting loop.")
            break

        for el in elements:
            info = _parse_post_element(el)
            if not info:
                continue

            post_date = info['date'].date()
            if post_date < start_date:
                logger.info("📅 Reached start of date range. Ending collection.")
                if posts_batch:
                    insert_clickhouse_batch("telegram_posts_buffer", posts_batch, batch_size=BATCH_SIZE)
                return (channel, collected_msgids)

            if post_date > today:
                continue  # Skip future-dated posts

            msgid = info['msgid']

            # Skip duplicate msgids processed during this run
            if msgid in seen_msgids:
                logger.debug(f"⏭️ Skipping duplicate msgid: {msgid}")
                continue

            # Add new msgid to tracking sets
            seen_msgids.add(msgid)
            collected_msgids.append(msgid)

            logger.info(f"[+] @{channel} post fetched: msgid={msgid} | date={info['date']} | views={info['views']}")

            # Convert Gregorian date to Jalali and extract calendar info
            jdt = jdatetime.datetime.fromgregorian(date=info['date'])
            shdate = jdt.strftime('%Y-%m-%d')
            dow = jdt.weekday()
            is_hol = 1 if jalali_calendar.holiday(shdate) == 'تعطیل' else 0

            post_row = {
                "channel": channel,
                "msgid": msgid,
                "ptype": info.get('type', 'unknown'),
                "views": info['views'],
                "reactions": 0,
                "is_forwarded": 0,
                "forwarded_from": '',
                "txtContent": info['text'],
                "date": info['date'],
                "shdate": shdate,
                "day_of_week": dow,
                "is_holiday": is_hol,
                "insert_date": datetime.now(),
                "update_date": datetime.now()
            }

            posts_batch.append(post_row)
            current_msgid = msgid

            # Insert batch if batch size reached
            if len(posts_batch) >= BATCH_SIZE:
                insert_clickhouse_batch("telegram_posts_buffer", posts_batch, batch_size=BATCH_SIZE)
                posts_batch.clear()

        # Check for pagination stuck (same current_msgid repeated)
        if current_msgid == previous_msgid:
            repeat_count += 1
            if repeat_count >= MAX_REPEAT:
                logger.warning("⚠️ Pagination stuck (same msgid repeated). Breaking loop.")
                break
        else:
            repeat_count = 0
            previous_msgid = current_msgid

        page_count += 1
        time.sleep(random.uniform(*DELAY_RANGE))

    # Insert any remaining posts
    if posts_batch:
        insert_clickhouse_batch("telegram_posts_buffer", posts_batch, batch_size=BATCH_SIZE)

    logger.info("✅ Scraping complete.")
    return (channel, collected_msgids)

