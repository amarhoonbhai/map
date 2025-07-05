
import os
import json
import asyncio
import logging
from datetime import datetime
from telethon import TelegramClient, events
from telethon.sessions import StringSession

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

USERS_FILE = "users.json"
clients = {}

def load_users():
    with open(USERS_FILE, 'r') as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

async def run_user_bot(config):
    if "expires_at" in config:
        if datetime.now() > datetime.fromisoformat(config["expires_at"]):
            logger.warning(f"[{config['phone']}] Plan expired. Skipping.")
            return

    phone = config["phone"]
    string_session = config["session"]
    api_id = int(config["api_id"])
    api_hash = config["api_hash"]
    delay = config.get("msg_delay_sec", 5)
    cycle = config.get("cycle_delay_min", 15)

    client = TelegramClient(StringSession(string_session), api_id, api_hash)
    clients[phone] = client

    await client.start()
    me = await client.get_me()
    logger.info(f"[{phone}] Bot started for {me.first_name}")

    @client.on(events.NewMessage(pattern=r'\.help'))
    async def show_help(event):
        help_text = (
            "🤖 Available Commands:\n"
            ".status - Show current bot settings\n"
            ".info - Show user info\n"
            ".time Xm - Set cycle delay (min 10 min)\n"
            ".delay Xs - Set message delay (min 5 sec)\n"
            ".addgroup <link> - Save Telegram group link\n"
            ".groups - Show saved group links\n"
            ".help - Show this help message"
        )
        await event.respond(help_text)

    @client.on(events.NewMessage(pattern=r'\.status'))
    async def show_status(event):
        users = load_users()
        user_data = users.get(phone, {})
        delay = user_data.get("msg_delay_sec", 5)
        cycle = user_data.get("cycle_delay_min", 15)
        expires = user_data.get("expires_at", "N/A")
        await event.respond(f"📊 Status:\nDelay: {delay} sec\nCycle: {cycle} min\nExpires: {expires}")

    @client.on(events.NewMessage(pattern=r'\.info'))
    async def show_info(event):
        users = load_users()
        expires = users.get(phone, {}).get("expires_at", "N/A")
        await event.respond(f"👤 Info:\nName: {me.first_name}\nID: {me.id}\nUsername: @{me.username or 'N/A'}\nPlan Expires: {expires}")

    @client.on(events.NewMessage(pattern=r'\.time (\d+)m'))
    async def update_cycle(event):
        new_cycle = int(event.pattern_match.group(1))
        if new_cycle < 10:
            await event.respond("❌ Minimum allowed cycle is 10 minutes.")
            return
        users = load_users()
        users[phone]["cycle_delay_min"] = new_cycle
        save_users(users)
        await event.respond(f"✅ Cycle time updated to {new_cycle} minutes.")

    @client.on(events.NewMessage(pattern=r'\.delay (\d+)s'))
    async def update_delay(event):
        new_delay = int(event.pattern_match.group(1))
        if new_delay < 5:
            await event.respond("❌ Minimum allowed delay is 5 seconds.")
            return
        users = load_users()
        users[phone]["msg_delay_sec"] = new_delay
        save_users(users)
        await event.respond(f"✅ Message delay updated to {new_delay} seconds.")

    @client.on(events.NewMessage(pattern=r'\.addgroup (.+)'))
    async def add_group(event):
        group_link = event.pattern_match.group(1).strip()
        if not group_link.startswith("https://t.me/"):
            await event.respond("❌ Invalid group link. Must start with https://t.me/")
            return
        users = load_users()
        groups = users[phone].get("groups", [])
        if group_link not in groups:
            groups.append(group_link)
            users[phone]["groups"] = groups
            save_users(users)
            await event.respond(f"✅ Group link added: {group_link}")
        else:
            await event.respond(f"ℹ️ Group already exists: {group_link}")

    @client.on(events.NewMessage(pattern=r'\.groups'))
    async def list_groups(event):
        users = load_users()
        groups = users[phone].get("groups", [])
        if not groups:
            await event.respond("📭 No groups saved.")
        else:
            await event.respond("📋 Saved Groups:\n" + "\n".join(f"- {g}" for g in groups))

    try:
        await client.run_until_disconnected()
    except Exception as e:
        logger.error(f"[{phone}] Client error: {e}")
    finally:
        await client.disconnect()

async def cleanup_expired_users():
    while True:
        await asyncio.sleep(60)
        users = load_users()
        now = datetime.now()
        changed = False
        for phone, user in list(users.items()):
            if "expires_at" in user and datetime.fromisoformat(user["expires_at"]) < now:
                logger.info(f"[{phone}] Plan expired. Removing.")
                users.pop(phone)
                changed = True
        if changed:
            save_users(users)

async def watch_and_run_bots():
    asyncio.create_task(cleanup_expired_users())
    running = set()
    while True:
        users = load_users()
        for phone, config in users.items():
            if phone not in running:
                running.add(phone)
                asyncio.create_task(run_user_bot(config))
        await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(watch_and_run_bots())
