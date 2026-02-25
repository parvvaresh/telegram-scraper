# ========================================================
# Author: Alireza Parvaresh
# Last Edited: 2025-06-22
# Description: Fetch and store Telegram message reactions into ClickHouse
# ========================================================

import asyncio
import logging
from datetime import datetime

from telethon.errors import FloodWaitError

from fetch_tools.utils import insert_clickhouse_batch
from fetch_tools.configDB import DB_NAME

# Setup logger
logger = logging.getLogger(__name__)

# Buffer table names in ClickHouse
REACTIONS_TABLE = "telegram_reactions_buffer"
POSTS_TABLE = "telegram_posts_buffer"

# Batch size for insertion
BATCH_SIZE = 100


async def fetch_and_update_reactions(client, channel: str, message_ids: list[int]):
    """
    Fetch reactions for a list of Telegram messages in a channel
    and batch-insert them into ClickHouse.

    Args:
        client (TelegramClient): Active Telethon client.
        channel (str): Telegram channel username or ID.
        message_ids (list[int]): List of message IDs to fetch reactions for.
    """
    logger.info(f"Start fetching reactions for {len(message_ids)} messages in '{channel}'.")

    # Buffers for batching insertions
    reactions_buffer = []
    posts_buffer = []

    now = datetime.now()

    for msg_id in message_ids:
        try:
            # Fetch the message by ID
            msg = await client.get_messages(channel, ids=msg_id)

            # Skip if no message or no reactions
            if not msg or not msg.reactions:
                continue

            # Count total reactions
            total_reactions = sum(r.count for r in msg.reactions.results)

            # Extract each reaction type
            for reaction in msg.reactions.results:
                reactions_buffer.append({
                    "channel": channel,
                    "msgid": msg_id,
                    "reaction": getattr(reaction.reaction, 'emoticon', str(reaction.reaction)),
                    "count": reaction.count,
                    "insert_date": now,
                    "update_date": now
                })

            # Store post-level reaction total
            posts_buffer.append({
                "channel": channel,
                "msgid": msg_id,
                "reactions": total_reactions,
                "update_date": now
            })

            # Insert batches if buffer is full
            if len(reactions_buffer) >= BATCH_SIZE:
                insert_clickhouse_batch(REACTIONS_TABLE, reactions_buffer)
                reactions_buffer.clear()

            if len(posts_buffer) >= BATCH_SIZE:
                insert_clickhouse_batch(POSTS_TABLE, posts_buffer)
                posts_buffer.clear()

        except FloodWaitError as fw:
            logger.warning(f"Flood wait triggered: sleeping for {fw.seconds} seconds.")
            await asyncio.sleep(fw.seconds + 5)

        except Exception as e:
            logger.error(f"Failed to process message ID {msg_id}: {e}")

    # Insert any remaining data
    if reactions_buffer:
        insert_clickhouse_batch(REACTIONS_TABLE, reactions_buffer)

    if posts_buffer:
        insert_clickhouse_batch(POSTS_TABLE, posts_buffer)

    logger.info(f"Finished processing {len(message_ids)} messages in '{channel}'.")

