import json
import logging
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)


def normalize_channel(entry: str) -> Optional[str]:
    """
    Extracts a clean Telegram channel username from a given input string.

    Args:
        entry (str): Raw channel identifier (URL, handle, or username).

    Returns:
        Optional[str]: Normalized channel username, or None if input is invalid.
    """
    if not isinstance(entry, str):
        return None
    entry = entry.strip().lstrip('@')
    parts = entry.split('/')
    return parts[-1] if parts and parts[-1] else None


def load_channels_from_json(file_path: str) -> List[str]:
    """
    Loads a list of Telegram channel usernames from a JSON file and normalizes them.

    The JSON file should contain a dictionary with a "channels" key mapped to a list
    of raw channel entries.

    Args:
        file_path (str): Path to the JSON file.

    Returns:
        List[str]: List of normalized channel usernames.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            raw_channels = data.get("channels", [])
            return [c for c in (normalize_channel(c) for c in raw_channels) if c]
    except FileNotFoundError:
        logger.error(f"❌ Channel file not found: {file_path}")
    except json.JSONDecodeError as e:
        logger.error(f"❌ Invalid JSON format in {file_path}: {e}")
    return []


def worker(channel_with_index: Tuple[int, int, str], days: int) -> List[str]:
    """
    Worker function for multiprocessing pool that processes a single Telegram channel.

    Args:
        channel_with_index (Tuple[int, int, str]): Tuple (index, total, channel).
        days (int): Number of days to fetch posts for.

    Returns:
        List[str]: List of message IDs fetched from the channel.
    """
    from fetch_tools.posts import fetch_and_insert_posts

    index, total, raw_channel = channel_with_index
    try:
        logger.info(f"[+] ({index}/{total}) Fetching channel: @{raw_channel}")
        channel, msgids = fetch_and_insert_posts(raw_channel, days)
        logger.info(f"[✓] ({index}/{total}) Done: @{channel} | Posts: {len(msgids)}")
        return channel, msgids

    except Exception as e:
        logger.exception(f"[✗] ({index}/{total}) Error in @{raw_channel}: {e}")
        return raw_channel, []
