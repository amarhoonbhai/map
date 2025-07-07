
from telethon import TelegramClient, events
import asyncio
import os
from datetime import datetime, timedelta

api_id = 21701625  # Replace with your API ID
api_hash = '966e14c95b3a387d3b262ebf837fada3'  # Replace with your API Hash

interval_minutes = 10
message_delay_seconds = 10
auto_post_enabled = False
messages = []

plan_start_date = None
plan_days = 0

# Load settings from config
folder_name = None
def load_config():
    global folder_name
    global interval_minutes, message_delay_seconds, auto_post_enabled, plan_start_date, plan_days
    if os.path.exists("plan_config.txt"):
        with open("plan_config.txt", "r") as f:
            for line in f:
                if line.startswith("interval="):
                    interval_minutes = max(10, int(line.strip().split("=")[1]))
                elif line.startswith("delay="):
                    message_delay_seconds = int(line.strip().split("=")[1])
                elif line.startswith("auto_post="):
                auto_post_enabled = line.strip().split("=")[1].lower() == "on"
            elif line.startswith("folder_name="):
                folder_name = line.strip().split("=")[1]
                    auto_post_enabled = line.strip().split("=")[1].lower() == "on"
                elif line.startswith("plan_start="):
                    plan_start_date = datetime.strptime(line.strip().split("=")[1], "%Y-%m-%d")
                elif line.startswith("plan_days="):
                    plan_days = int(line.strip().split("=")[1])
    else:
        # Prompt user for plan_days if config doesn't exist
        days_input = input("Enter plan duration in days: ").strip()
        if days_input.isdigit():
            plan_days = int(days_input)
            plan_start_date = datetime.today()
            auto_post_enabled = True
            save_config()
        else:
            print("Invalid input. Exiting.")
            exit()

# Save settings to config
def save_config():
    global folder_name
    with open("plan_config.txt", "w") as f:
        f.write(f"interval={interval_minutes}\n")
        f.write(f"delay={message_delay_seconds}\n")
        f.write(f"auto_post={'on' if auto_post_enabled else 'off'}\n")
        f.write(f"plan_start={plan_start_date.strftime('%Y-%m-%d')}\n")
        f.write(f"plan_days={plan_days}\n")

# Load messages from 'Saved Messages' via Telegram

def load_messages():
    global messages
    messages.clear()

    async def fetch_saved():
        async for msg in client.iter_messages('me', reverse=True):
            if msg.message or msg.media:
                messages.append(msg)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(fetch_saved())

    global messages
    if os.path.exists("saved_messages.txt"):
        with open("saved_messages.txt", "r", encoding="utf-8") as f:
            content = f.read()
            messages = [msg.strip() for msg in content.split("===") if msg.strip()]

def check_plan_expiry():
    global auto_post_enabled
    if plan_start_date and plan_days:
        expiry_date = plan_start_date + timedelta(days=plan_days)
        if datetime.today().date() > expiry_date.date():
            auto_post_enabled = False
            print("⚠️ Plan expired. Auto-posting disabled.")
            save_config()

load_config()
load_messages()
check_plan_expiry()

import sys
account_name = os.path.basename(sys.argv[0]).replace('.py', '').replace('bot_', '')
session_path = os.path.join('accounts', f"{account_name}.session")
client = TelegramClient(session_path, api_id, api_hash)

@client.on(events.NewMessage(pattern=r'^\.info$'))
async def info_handler(event):
    me = await client.get_me()
    msg = "**Account Info**\n"
    msg += f"👤 Name      : {me.first_name} {me.last_name or ''}\n"
    msg += f"🆔 User ID   : {me.id}\n"
    msg += f"📛 Username  : @{me.username or 'N/A'}\n"
    msg += f"💎 Premium   : {'Yes' if me.premium else 'No'}"
    await event.reply(msg)

@client.on(events.NewMessage(pattern=r'^\.status$'))
async def status_handler(event):
    remaining = "Unlimited"
    if plan_start_date and plan_days:
        expiry = plan_start_date + timedelta(days=plan_days)
        days_left = (expiry.date() - datetime.today().date()).days
        remaining = f"{days_left} days" if days_left >= 0 else "Expired"

    await event.reply(f"**Bot Status**\n"
                      f"🟢 Auto-post : {'ON' if auto_post_enabled else 'OFF'}\n"
                      f"⏱ Interval  : {interval_minutes} minutes\n"
                      f"🐢 Delay     : {message_delay_seconds} seconds\n"
                      f"📅 Plan      : {remaining}\n"
                      f"📝 Messages  : {len(messages)}")

@client.on(events.NewMessage(pattern=r'^\.time (\d+)[mM]$'))
async def set_time(event):
    global interval_minutes
    new_interval = int(event.pattern_match.group(1))
    if new_interval < 10:
        await event.reply("❌ Minimum interval is 10 minutes.")
    else:
        interval_minutes = new_interval
        save_config()
        await event.reply(f"✅ Interval set to {interval_minutes} minutes.")

@client.on(events.NewMessage(pattern=r'^\.delay (\d+)$'))
async def set_delay(event):
    global message_delay_seconds
    message_delay_seconds = int(event.pattern_match.group(1))
    save_config()
    await event.reply(f"✅ Per-message delay set to {message_delay_seconds} seconds.")

# Background task to forward messages
async def auto_post_loop():
    await client.connect()
    index = 0
    while True:
        if auto_post_enabled and messages:
                    from telethon.tl.functions.messages import GetDialogFiltersRequest
        folder_id = None
        if folder_name:
            filters = await client(GetDialogFiltersRequest())
            for idx, f in enumerate(filters):
                if f.title.lower() == folder_name.lower():
                    folder_id = idx + 1
                    break
        dialogs = await client.get_dialogs(folder=folder_id) if folder_id else await client.get_dialogs()
        for dialog in dialogs:
                if dialog.is_group or dialog.is_channel:
                    try:
                        await client.forward_messages(dialog.id, messages[index % len(messages)])
                        await asyncio.sleep(message_delay_seconds)
                    except Exception as e:
                        print(f"Failed to send to {dialog.name}: {e}")
            index += 1
        await asyncio.sleep(interval_minutes * 60)

# Start bot
async def main():
    await client.start()
    client.loop.create_task(auto_post_loop())
    print("Bot started. Waiting for commands...")
    
    print("Bot is now running in the background.")
    print("Type 'exit' to stop the bot...")
    loop = asyncio.get_event_loop()
    def wait_for_exit():
        while True:
            cmd = input()
            if cmd.strip().lower() == "exit":
                print("Exiting bot...")
                loop.call_soon_threadsafe(loop.stop)
                break
    import threading
    threading.Thread(target=wait_for_exit, daemon=True).start()
    await client.run_until_disconnected()
    

if __name__ == '__main__':
    asyncio.run(main())
