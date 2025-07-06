
from telethon import TelegramClient, events
import asyncio
import time

# Replace with your credentials
api_id = 123456  # 🔁 Your API ID
api_hash = 'your_api_hash_here'  # 🔁 Your API Hash

interval = 10  # seconds between forwarding
client = TelegramClient('session_name', api_id, api_hash)

@client.on(events.NewMessage(pattern=r'^\.info$'))
async def handler_info(event):
    await event.reply("🤖 Auto Forward Bot\nVersion: 1.0\nSource: Saved Messages")

@client.on(events.NewMessage(pattern=r'^\.status$'))
async def handler_status(event):
    await event.reply("✅ Bot is running and ready to forward.")

@client.on(events.NewMessage(pattern=r'^\.time$'))
async def handler_time(event):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    await event.reply(f"🕒 Current Server Time: {now}")

async def main():
    await client.start()
    print("Logged in successfully.")

    # Get all joined group chats
    dialogs = await client.get_dialogs()
    groups = [d for d in dialogs if d.is_group]

    if not groups:
        print("No groups found.")
        return

    # Get latest message from Saved Messages
    saved_messages = await client.get_messages('me', limit=1)
    if not saved_messages:
        print("No messages in Saved Messages.")
        return

    message_to_forward = saved_messages[0]
    print(f"Forwarding: {message_to_forward.text or 'Media message'}")

    # Forward to each group
    for group in groups:
        try:
            await message_to_forward.forward_to(group.id)
            print(f"✔ Forwarded to: {group.name}")
            await asyncio.sleep(interval)
        except Exception as e:
            print(f"❌ Failed to forward to {group.name}: {e}")

    print("Waiting for command input...")

    await client.run_until_disconnected()

with client:
    client.loop.run_until_complete(main())
