import os
import sys
import asyncio
from datetime import datetime, timedelta
from telethon import TelegramClient, events
from telethon.tl.functions.messages import GetDialogFiltersRequest
from telethon.tl.functions.messages import ImportChatInviteRequest

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

import logging

logging.basicConfig(
    filename="bot_log.txt",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

async def load_messages_from_saved():
    global messages
    async for msg in client.iter_messages('me', reverse=True):
        if msg.message or msg.media:
            messages.append(msg)
    if not messages:
        print("⚠️ No valid messages found in Saved Messages.")
        logging.warning("No valid messages found in Saved Messages.")

    global messages
    async for msg in client.iter_messages('me', reverse=True):
        if msg.message or msg.media:
            messages.append(msg)

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

@client.on(events.NewMessage(pattern=r'^\.folder (.+)$'))
async def set_folder(event):
    global folder_name
    folder_name = event.pattern_match.group(1).strip()
    save_config()
    await event.reply(f"✅ Folder target set to '{folder_name}'")

@client.on(events.NewMessage(pattern=r'^\.addgroup'))
async def bulk_add_groups(event):
    lines = event.raw_text.strip().splitlines()[1:]
    if not lines:
        await event.reply("❌ Please provide group links on separate lines.")
        return
    success = []
    failed = []
    for line in lines:
        link = line.strip()
        if not link.startswith("http"):
            failed.append((link, "Invalid format"))
            continue
        try:
            username = link.split("/")[-1]
            entity = await client.get_entity(username)
            gid = entity.id if entity.id < 0 else f"-100{entity.id}"
            save_group_id(gid)
            success.append(gid)
        except Exception as e:
            failed.append((link, str(e)))
    msg = ""
    if success:
        msg += f"✅ Added {len(success)} group(s):\n" + "\n".join(success) + "\n"
    if failed:
        msg += f"❌ Failed to add {len(failed)} group(s):\n" + "\n".join(f"{l} - {err}" for l, err in failed)
    await event.reply(msg or "No groups processed.")

@client.on(events.NewMessage(pattern=r'^\.forwardto (https?://t\.me/\S+)$'))
async def forward_to_group(event):
    link = event.pattern_match.group(1)
    try:
        username = link.split("/")[-1]
        entity = await client.get_entity(username)
        gid = entity.id if entity.id < 0 else f"-100{entity.id}"
        save_forward_id(gid)
        await event.reply(f"✅ Your messages will now be forwarded only to: `{gid}`")
    except Exception as e:
        await event.reply(f"❌ Could not add group: {e}")

@client.on(events.NewMessage(pattern=r'^\.clearforwardto$'))
async def clear_forward_list(event):
    forward_ids.clear()
    account_group_file = os.path.join("accounts", f"{account_name}_groups.txt")
    if os.path.exists(account_group_file):
        os.remove(account_group_file)
    await event.reply("✅ Cleared all forwarding targets for this account.")

@client.on(events.NewMessage(pattern=r'^\.help$'))
async def help_command(event):
    help_text = (
        "**🤖 Available Commands:**\n"
        "📦 `.addgroup` + links — Save multiple groups\n"
        "🎯 `.forwardto <t.me/link>` — Forward to specific group only\n"
        "🧹 `.clearforwardto` — Remove `.forwardto` restrictions\n"
        "🕒 `.time <10m>` — Set post interval (min 10 min)\n"
        "⏱ `.delay <seconds>` — Delay between messages\n"
        "📁 `.folder <name>` — Target folder's groups\n"
        "📊 `.status` — View status and plan\n"
        "👤 `.info` — Account info\n"
        "❌ `exit` — Detach terminal"
    )
    await event.reply(help_text)

async def auto_post_loop():
    await client.connect()
    await load_messages_from_saved()
    check_plan_expiry()

    if not messages:
        print("⚠️ No messages to send. Make sure your Saved Messages contains text or media.")
        logging.warning("No messages to send. Saved Messages might be empty.")
    if not group_ids and not forward_ids:
        print("⚠️ No groups to send to. Use .addgroup or .forwardto in Telegram.")
        logging.warning("No target groups to send messages to.")

    await client.connect()
    await load_messages_from_saved()
    check_plan_expiry()
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