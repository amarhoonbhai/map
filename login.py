
from telethon.sync import TelegramClient

# Replace with your own API ID and Hash from https://my.telegram.org
api_id = 21701625 # 🔁 Your API ID
api_hash = '966e14c95b3a387d3b262ebf837fada3'  # 🔁 Your API Hash

print("📱 Telegram Login")
phone = input("Enter your phone number (with country code): ")

with TelegramClient("session_name", api_id, api_hash) as client:
    client.start(phone)
    print("✅ Logged in successfully!")
