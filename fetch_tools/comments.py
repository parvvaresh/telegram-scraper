import logging
import asyncio
import random
from datetime import datetime

import jdatetime
from telethon.errors import FloodWaitError, MsgIdInvalidError

from .utils import (
    get_media_type,
    is_holiday,
    insert_clickhouse_batch,
)

# ---------- Logging ----------
logger = logging.getLogger(__name__)


# ---------- Main Async Fetcher ----------

async def fetch_and_insert_comments(client, session, channel: str, msg_ids: list[int], limit=36) -> list[int]:
    all_saved_ids = []

    for post_id in msg_ids:
        batch = []
        saved_ids = []
        count = 0

        try:
            # Validate post_id
            if isinstance(post_id, str) and post_id.startswith("https://t.me/"):
                try:
                    post_id = int(post_id.rstrip('/').split('/')[-1])
                except ValueError:
                    logger.warning(f"Invalid post_id URL format: {post_id}")
                    continue

            if not isinstance(post_id, int):
                logger.warning(f"Invalid post_id (not int): {post_id}")
                continue

            # Fetch comments
            async for msg in client.iter_messages(channel, reply_to=post_id):
                if not msg or not msg.message or not msg.date:
                    continue

                if limit is not None and count >= limit:
                    break

                user_id = getattr(msg.from_id, 'user_id', 0) or 0
                jdt = jdatetime.datetime.fromgregorian(date=msg.date)
                shdate = jdt.strftime("%Y-%-m-%-d")
                dow = jdt.weekday()
                is_hol = int(is_holiday(shdate))

                reactions = 0
                if getattr(msg, 'reactions', None) and msg.reactions.results:
                    try:
                        reactions = sum(r.count or 0 for r in msg.reactions.results)
                    except Exception:
                        logger.warning(f"Error parsing reactions for msg {msg.id}", exc_info=True)

                record = {
                    "comment_id": msg.id or 0,
                    "channel": channel,
                    "msgid": post_id,
                    "user_id": user_id,
                    "ptype": get_media_type(msg),
                    "reactions": reactions,
                    "is_reply": int(bool(msg.reply_to_msg_id)),
                    "reply_to": msg.reply_to_msg_id or 0,
                    "txtContent": msg.message or '',
                    "date": msg.date,
                    "shdate": shdate,
                    "day_of_week": dow,
                    "is_holiday": is_hol,
                    "insert_date": datetime.now(),
                    "update_date": datetime.now(),
                }

                batch.append(record)
                saved_ids.append(msg.id)
                count += 1

                if len(batch) >= 100:
                    insert_clickhouse_batch("telegram_comments_buffer", batch)
                    batch.clear()

                await asyncio.sleep(random.uniform(0.5, 1.5))

            if batch:
                insert_clickhouse_batch("telegram_comments_buffer", batch)

        except FloodWaitError as e:
            logger.warning(f"FloodWaitError: sleeping for {e.seconds}s")
            await asyncio.sleep(e.seconds + 1)
            continue  # Retry next post_id
        except MsgIdInvalidError:
            logger.error(f"Invalid post_id {post_id}; no comments fetched.")
        except Exception:
            logger.exception("Unexpected error occurred in get_comments")

        all_saved_ids.extend(saved_ids)

    return all_saved_ids
