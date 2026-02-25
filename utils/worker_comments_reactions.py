import argparse
import asyncio
import logging
from telethon.sync import TelegramClient
from telethon.errors import FloodWaitError
from telethon import connection

from fetch_tools.reactions import fetch_and_update_reactions
from fetch_tools.comments import fetch_and_insert_comments
from config import api_hash, api_id, MTPROTO_PROXY

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

async def process(session_path, batch_file, limit):
    session_name = session_path.replace('.session', '')
    client = TelegramClient(
        session_name,
        api_id,
        api_hash,
        connection=connection.ConnectionTcpMTProxyAbridged,
        proxy=(
            MTPROTO_PROXY['server'],
            MTPROTO_PROXY['port'],
            MTPROTO_PROXY['secret']
        )
    )

    await client.start()
    logger.info(f"Client started for session: {session_path}")

    with open(batch_file, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]
        items = [tuple(line.split()) for line in lines if len(line.split()) == 2]

    grouped = {}
    for channel, msgid in items:
        try:
            grouped.setdefault(channel, []).append(int(msgid))
        except ValueError:
            logger.warning(f"Invalid msgid (not int): {msgid}")

    for channel, msgids in grouped.items():
        logger.info(f"Processing {len(msgids)} messages from: {channel}")

        try:
            await fetch_and_update_reactions(client, channel, msgids)
            logger.info(f"Reactions updated for: {channel}")
        except FloodWaitError as fw:
            logger.warning(f"Flood wait on reactions for {channel}: sleeping {fw.seconds} seconds")
            await asyncio.sleep(fw.seconds + 5)
        except Exception as e:
            logger.warning(f"Reactions error on {channel}: {e}")

        try:
            await fetch_and_insert_comments(client, None, channel, msgids, limit)
            logger.info(f"Comments updated for: {channel}")
        except FloodWaitError as fw:
            logger.warning(f"Flood wait on comments for {channel}: sleeping {fw.seconds} seconds")
            await asyncio.sleep(fw.seconds + 5)
        except Exception as e:
            logger.warning(f"Comments error on {channel}: {e}")

    await client.disconnect()
    logger.info("🔚 Finished processing batch.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--session', required=True, help='Path to .session file')
    parser.add_argument('--batch', required=True, help='Path to batch .txt file')
    parser.add_argument('--limit', required=True, type=int, help='Limit for fetching comments')

    args = parser.parse_args()

    try:
        asyncio.run(process(args.session, args.batch, args.limit))
    except Exception as e:
        logger.error(f"Fatal error: {e}")
