import os
import sys
import asyncio
import logging
from datetime import datetime, timedelta
from telethon import TelegramClient, events
from telethon.tl.functions.messages import GetDialogFiltersRequest

# Configuration
api_id = 21701625
api_hash = '966e14c95b3a387d3b262ebf837fada3'

interval_minutes = 10
message_delay_seconds = 10
auto_post_enabled = False
messages = []
plan_start_date = None
plan_days = 0
folder_name = None

logging.basicConfig(
    filename="bot_log.txt",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def load_config():
    global interval_minutes, message_delay_seconds, auto_post_enabled, plan_start_date, plan_days, folder_name
    if os.path.exists("plan_config.txt"):
        with open("plan_config.txt", "r") as f:
            for line in f:
                if line.startswith("interval="):
                    interval_minutes = max(10, int(line.strip().split("=")[1]))
                elif line.startswith("delay="):
                    message_delay_seconds = int(line.strip().split("=")[1])
                elif line.startswith("auto_post="):
                    auto_post_enabled = line.strip().split("=")[1].lower() == "on"
                elif line.startswith("plan_start="):
                    plan_start_date = datetime.strptime(line.strip().split("=")[1], "%Y-%m-%d")
                elif line.startswith("plan_days="):
                    plan_days = int(line.strip().split("=")[1])
                elif line.startswith("folder_name="):
                    folder_name = line.strip().split("=")[1]
    else:
        days_input = input("Enter plan duration in days: ").strip()
        if days_input.isdigit():
            plan_days = int(days_input)
            plan_start_date = datetime.today()
            auto_post_enabled = True
            save_config()
        else:
            print("Invalid input. Exiting.")
            exit()

def save_config():
    with open("plan_config.txt", "w") as f:
        f.write(f"interval={interval_minutes}\n")
        f.write(f"delay={message_delay_seconds}\n")
        f.write(f"auto_post={'on' if auto_post_enabled else 'off'}\n")
        f.write(f"plan_start={plan_start_date.strftime('%Y-%m-%d')}\n")
        f.write(f"plan_days={plan_days}\n")
        if folder_name:
            f.write(f"folder_name={folder_name}\n")

def check_plan_expiry():
    global auto_post_enabled
    if plan_start_date and plan_days:
        expiry_date = plan_start_date + timedelta(days=plan_days)
        if datetime.today().date() > expiry_date.date():
            auto_post_enabled = False
            print("⚠️ Plan expired. Auto-posting disabled.")
            save_config()

async def load_messages_from_saved():
    if not client.is_connected():
        await client.connect()
    messages.clear()
    async for msg in client.iter_messages('me', reverse=True):
        if msg.message or msg.media:
            messages.append(msg)
    if not messages:
        print("⚠️ No valid messages found in Saved Messages.")
        logging.warning("No valid messages found in Saved Messages.")

account_name = os.path.basename(sys.argv[0]).replace('.py', '').replace('bot_', '')
session_path = os.path.join('accounts', f"{account_name}.session")

group_db_file = "group_db.txt"
group_ids = set()

def load_group_db():
    global group_ids
    if os.path.exists(group_db_file):
        with open(group_db_file, "r") as f:
            group_ids = set(line.strip() for line in f if line.strip().isdigit() or line.strip().startswith("-100"))

def save_group_id(gid):
    group_ids.add(str(gid))
    with open(group_db_file, "w") as f:
        for gid in group_ids:
            f.write(f"{gid}\n")

forward_ids = set()

def load_forward_list():
    global forward_ids
    account_group_file = os.path.join("accounts", f"{account_name}_groups.txt")
    if os.path.exists(account_group_file):
        with open(account_group_file, "r") as f:
            forward_ids = set(line.strip() for line in f if line.strip())

def save_forward_id(gid):
    account_group_file = os.path.join("accounts", f"{account_name}_groups.txt")
    forward_ids.add(str(gid))
    with open(account_group_file, "w") as f:
        for gid in forward_ids:
            f.write(f"{gid}\n")

client = TelegramClient(session_path, api_id, api_hash)

# [KEEP EXISTING TELETHON EVENT HANDLERS HERE]

async def auto_post_loop():
    await client.connect()
    await load_messages_from_saved()
    check_plan_expiry()

    if not messages:
        print("⚠️ No messages to send. Make sure your Saved Messages contains text or media.")
        logging.warning("No messages to send.")
    if not group_ids and not forward_ids:
        print("⚠️ No groups to send to. Use .addgroup or .forwardto in Telegram.")
        logging.warning("No target groups to send messages to.")

    index = 0
    while True:
        if auto_post_enabled and messages:
            folder_id = None
            if folder_name:
                filters = await client(GetDialogFiltersRequest())
                for idx, f in enumerate(filters):
                    if f.title.lower() == folder_name.lower():
                        folder_id = idx + 1
                        break
            dialogs = await client.get_dialogs(folder=folder_id) if folder_id else await client.get_dialogs()
            for dialog in dialogs:
                if forward_ids and str(dialog.id) not in forward_ids:
                    continue
                if str(dialog.id) not in group_ids:
                    continue
                if dialog.is_group or dialog.is_channel:
                    try:
                        await client.forward_messages(dialog.id, messages[index % len(messages)])
                        await asyncio.sleep(message_delay_seconds)
                    except Exception as e:
                        print(f"Failed to send to {dialog.name}: {e}")
                        logging.error(f"Failed to send to {dialog.name}: {e}")
            index += 1
        await asyncio.sleep(interval_minutes * 60)

async def main():
    load_config()
    load_group_db()
    load_forward_list()
    await client.start()
    client.loop.create_task(auto_post_loop())
    print("Bot is now running in the background.")
    print("Type 'exit' to detach from terminal (bot will continue running)...")

    def wait_for_exit():
        while True:
            cmd = input()
            if cmd.strip().lower() == "exit":
                print("Terminal detached. Bot is still running in background.")
                break

    import threading
    threading.Thread(target=wait_for_exit, daemon=True).start()
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
    
