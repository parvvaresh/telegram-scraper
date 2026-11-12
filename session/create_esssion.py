import os
import sys

# Allow running as `python3 session/create_esssion.py` from the repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telethon.sync import TelegramClient
from telethon import connection
from telethon.errors import SessionPasswordNeededError

from config import api_hash, api_id, MTPROTO_PROXY_TUPLE, NUM_SESSIONS



for i in range(NUM_SESSIONS):
    session_name = f"session/telegram_{i}"
    print(f"\n📦 Creating session: {session_name}")

    # Create the Telegram client with MTProto proxy
    proxy_kwargs = (
        {"connection": connection.ConnectionTcpMTProxyAbridged, "proxy": MTPROTO_PROXY_TUPLE}
        if MTPROTO_PROXY_TUPLE else {}
    )
    client = TelegramClient(session_name, api_id, api_hash, **proxy_kwargs)

    with client:
        try:
            client.start()  # This will ask for phone number and code
            print(f"✅ Session {session_name} created successfully.")
        except SessionPasswordNeededError:
            print("🔐 Two-step verification is enabled. Please enter your password.")
            password = input("Password: ")
            client.sign_in(password=password)

print("\n🎉 All sessions have been created successfully.")