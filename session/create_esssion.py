
from telethon.sync import TelegramClient
from telethon import connection
from telethon.errors import SessionPasswordNeededError

from config import api_hash, api_id, MTPROTO_PROXY, NUM_SESSIONS



for i in range(NUM_SESSIONS):
    session_name = f"session/telegram_{i}"
    print(f"\n📦 Creating session: {session_name}")

    # Create the Telegram client with MTProto proxy
    client = TelegramClient(
        session_name,
        api_id,
        api_hash,
        connection=connection.ConnectionTcpMTProxyAbridged,  # ✅ Correct class
        proxy=(
            MTPROTO_PROXY['server'],
            MTPROTO_PROXY['port'],
            MTPROTO_PROXY['secret']  # Convert secret string to bytes
        )
    )

    with client:
        try:
            client.start()  # This will ask for phone number and code
            print(f"✅ Session {session_name} created successfully.")
        except SessionPasswordNeededError:
            print("🔐 Two-step verification is enabled. Please enter your password.")
            password = input("Password: ")
            client.sign_in(password=password)

print("\n🎉 All sessions have been created successfully.")