
from telethon import TelegramClient, events
import asyncio
import datetime
import platform
import psutil
import os
import re

api_id = 123456  # Replace with your API ID
api_hash = 'your_api_hash_here'  # Replace with your API Hash

# Load interval from config file
interval = 10  # default fallback
if os.path.exists("plan_config.txt"):
    with open("plan_config.txt", "r") as f:
        for line in f:
            if line.startswith("interval="):
                interval = int(line.strip().split("=")[1])

client = TelegramClient('session_name', api_id, api_hash)

@client.on(events.NewMessage(pattern=r'^\.info$'))
async def info_handler(event):
    system_info = platform.uname()
    msg = "**System Info**\n"
    msg += f"OS     : {system_info.system} {system_info.release}\n"
    msg += f"Node   : {system_info.node}\n"
    msg += f"Python : {platform.python_version()}"
    await event.reply(msg)

@client.on(events.NewMessage(pattern=r'^\.status$'))
async def status_handler(event):
    uptime = datetime.datetime.now() - datetime.datetime.fromtimestamp(psutil.boot_time())
    msg = f"Bot is running.\nUptime: {str(uptime).split('.')[0]}\nCurrent interval: {interval} seconds"
    await event.reply(msg)

@client.on(events.NewMessage(pattern=r'^\.time (\d+)([smh]?)$'))
async def time_command_handler(event):
    global interval
    match = re.match(r'^\.time (\d+)([smh]?)$', event.raw_text)
    if match:
        value, unit = int(match.group(1)), match.group(2)
        if unit == 'm':
            interval = value * 60
        elif unit == 'h':
            interval = value * 3600
        else:
            interval = value
        with open("plan_config.txt", "r") as f:
            lines = f.readlines()
        with open("plan_config.txt", "w") as f:
            for line in lines:
                if line.startswith("interval="):
                    f.write(f"interval={interval}\n")
                else:
                    f.write(line)
        await event.reply(f"✅ Interval updated to {interval} seconds.")
    else:
        await event.reply("❌ Invalid format. Use `.time 10s`, `.time 5m`, or `.time 1h`")

async def auto_forward():
    await client.start()
    print("Logged in.")

    dialogs = await client.get_dialogs()
    groups = [d for d in dialogs if d.is_group]

    if not groups:
        print("No groups found.")
        return

    saved_messages = await client.get_messages('me', limit=1)
    if not saved_messages:
        print("No messages in Saved Messages.")
        return

    message_to_forward = saved_messages[0]
    print(f"Forwarding: {message_to_forward.text or 'Media message'}")

    for group in groups:
        try:
            await message_to_forward.forward_to(group.id)
            print(f"✔ Forwarded to: {group.name}")
            await asyncio.sleep(interval)
        except Exception as e:
            print(f"❌ Failed to forward to {group.name}: {e}")

with client:
    client.loop.run_until_complete(auto_forward())
    client.run_until_disconnected()
