# ========================================================
# Author: Alireza Parvaresh
# Last Edited: 2025-06-12
# Description: ClickHouse batch insertion & Telegram post parsing utilities
# ========================================================

import json
import logging
import requests
from datetime import datetime
import jdatetime
from functools import lru_cache
from salnama import taghvim


from fetch_tools.configDB import (
    CLICKHOUSE_HTTP_URL,
    CLICKHOUSE_AUTH,
    DB_NAME,
)

logger = logging.getLogger(__name__)


# ---------------------- ClickHouse Insertion ---------------------- #

def insert_clickhouse_batch(table_name: str, data: list[dict], batch_size: int = 100):
    """
    Insert a list of dictionaries into a ClickHouse table using HTTP interface and JSONEachRow format.
    
    Args:
        table_name (str): The target table name.
        data (list[dict]): A list of row dictionaries to insert.
        batch_size (int): Number of rows to send per batch (default: 100).
    """
    if not data:
        logger.info("No data to insert.")
        return

    columns = list(data[0].keys())
    col_list = ", ".join(columns)
    insert_query = f"INSERT INTO {DB_NAME}.{table_name} ({col_list}) FORMAT JSONEachRow"
    headers = {"Content-Type": "application/json; charset=utf-8"}

    for start in range(0, len(data), batch_size):
        batch = data[start:start + batch_size]
        payload = "\n".join(json.dumps(serialize_row(row), ensure_ascii=False) for row in batch)

        try:
            response = requests.post(
                CLICKHOUSE_HTTP_URL,
                params={"query": insert_query},
                data=payload.encode("utf-8"),
                headers=headers,
                auth=CLICKHOUSE_AUTH,
                timeout=30
            )
            response.raise_for_status()
            logger.info(f"Inserted {len(batch)} rows into {DB_NAME}.{table_name}")
        except Exception as err:
            logger.error(f"Error inserting batch into {table_name}: {err}")


def serialize_row(row: dict) -> dict:
    """
    Convert a row into a JSON-serializable dict compatible with ClickHouse.

    Args:
        row (dict): Input dictionary.

    Returns:
        dict: Serialized dictionary.
    """
    out = {}
    for k, v in row.items():
        if v is None:
            # Handle nulls based on type or field name
            out[k] = '' if k in ['txtContent', 'channel', 'ptype', 'forwarded_from'] else 0
        elif hasattr(v, 'strftime'):
            # Format datetime fields
            out[k] = v.strftime('%Y-%m-%d %H:%M:%S')
        else:
            out[k] = v
    return out


# ---------------------- HTTP Session for Proxies ---------------------- #

def create_http_session(proxies: dict = None) -> requests.Session:
    """
    Create an HTTP session with proxy configuration.

    Args:
        proxies (dict): Optional proxy dictionary.

    Returns:
        requests.Session: Configured session.
    """
    session = requests.Session()
    if proxies:
        session.proxies.update(proxies)
    return session


# ---------------------- Telegram Post HTML Parser ---------------------- #

def _parse_post_element(el):
    """
    Parse a single Telegram post element (HTML) and extract relevant data.

    Args:
        el (bs4.element.Tag): Parsed HTML element of a post.

    Returns:
        dict or None: Parsed post data, or None if invalid.
    """
    link = el.find('a', class_='tgme_widget_message_date')
    if not link or 'href' not in link.attrs:
        return None

    try:
        msgid = int(link['href'].rstrip('/').split('/')[-1])
    except (ValueError, IndexError):
        return None

    # Extract view count
    views = 0
    view_el = el.find('span', class_='tgme_widget_message_views')
    if view_el:
        txt = view_el.get_text(strip=True)
        try:
            views = int(float(txt[:-1]) * 1000) if txt.endswith('K') else int(txt.replace(',', ''))
        except ValueError:
            logger.warning(f"Unable to parse view count: '{txt}'")

    # Extract post date
    time_el = link.find('time')
    date_str = time_el['datetime'] if time_el and time_el.has_attr('datetime') else link.get('title', '')
    try:
        date = datetime.fromisoformat(date_str)
    except Exception:
        logger.warning(f"Unable to parse date: '{date_str}'")
        return None

    # Extract text content
    text = ''
    text_el = el.find('div', class_='tgme_widget_message_text')
    if text_el:
        text = text_el.get_text(strip=True)

    # Detect content type
    types = []
    if text:
        types.append('text')
    if el.find('a', class_='tgme_widget_message_photo_wrap'):
        types.append('photo')
    if el.find('video') or el.find('div', class_='tgme_widget_message_video_player'):
        types.append('video')
    if el.find('audio') or el.find('div', class_='tgme_widget_message_voice_player'):
        types.append('audio')
    if el.find('a', class_='tgme_widget_message_document_wrap'):
        types.append('document')

    return {
        "msgid": msgid,
        "views": views,
        "date": date,
        "text": text,
        "type": ' + '.join(types) if types else 'unknown'
    }


# ---------------------- Holiday Checker ---------------------- #

# Instantiate the Jalali calendar from salnama
jalali_calendar = taghvim.Jalali()

@lru_cache(maxsize=None)
def is_holiday(shdate: str) -> bool:
    """
    Determine if a given Jalali date is a holiday in Iran.

    Args:
        shdate (str): Jalali date in "YYYY-M-D" format.

    Returns:
        bool: True if holiday, False otherwise.
    """
    return jalali_calendar.holiday(shdate) == 'تعطیل'


def get_media_type(msg) -> str:
    """
    Determine the media type of a Telegram message.
    Returns one of: 'photo', 'photo + text', 'video', 'video + text', 'document', 'sticker', or 'text'.
    """
    if msg.photo and msg.message:
        return "photo + text"
    if msg.photo:
        return "photo"
    if msg.video and msg.message:
        return "video + text"
    if msg.video:
        return "video"
    if msg.document:
        return "document"
    if msg.sticker:
        return "sticker"
    return "text"