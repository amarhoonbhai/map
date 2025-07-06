
from telethon.sync import TelegramClient

# Replace with your own API ID and Hash from https://my.telegram.org
api_id = 123456  # 🔁 Your API ID
api_hash = 'your_api_hash_here'  # 🔁 Your API Hash

print("📱 Telegram Login")
phone = input("Enter your phone number (with country code): ")

with TelegramClient("session_name", api_id, api_hash) as client:
    client.start(phone)
    print("✅ Logged in successfully!")
