import os
import json
import asyncio
import logging
import sqlite3
from datetime import datetime
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError
from colorama import Fore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

USERS_FILE = "users.json"
SESSIONS_DIR = "sessions"
clients = {}
session_locks = {}

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
    if phone not in session_locks:
        session_locks[phone] = asyncio.Lock()

    async with session_locks[phone]:
        session_path = os.path.join(SESSIONS_DIR, f"{phone}.session")
        api_id = int(config["api_id"])
        api_hash = config["api_hash"]
        delay = config.get("msg_delay_sec", 5)
        cycle = config.get("cycle_delay_min", 15)

        client = TelegramClient(session_path, api_id, api_hash)
        clients[phone] = client

        for _ in range(3):  # retry logic
            try:
                await client.start()
                break
            except sqlite3.OperationalError as e:
                if 'database is locked' in str(e):
                    logger.warning(f"[{phone}] DB locked, retrying...")
                    await asyncio.sleep(2)
                else:
                    raise

        me = await client.get_me()
        print(Fore.GREEN + f"[{phone}] Started bot for {me.first_name}")

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
            logger.info(f"[{phone}] Updated cycle_delay_min to {new_cycle} min")

        @client.on(events.NewMessage(pattern=r'\.help'))
        async def show_help(event):
            help_text = (
                "🤖 Available Commands:\n"
                ".status - Show current bot settings\n"
                ".time Xm - Set cycle delay (min 10 minutes)\n"
                ".info - Show user info\n"
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
            me = await client.get_me()
            users = load_users()
            expires = users.get(phone, {}).get("expires_at", "N/A")
            await event.respond(f"👤 Info:\nName: {me.first_name}\nID: {me.id}\nUsername: @{me.username or 'N/A'}\nPlan Expires: {expires}")

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
        removed = False

        for phone, config in list(users.items()):
            expires_at = config.get("expires_at")
            if expires_at and datetime.fromisoformat(expires_at) < now:
                logger.info(f"[{phone}] Expired. Cleaning up.")
                users.pop(phone)
                removed = True

                # Remove client if running
                client = clients.get(phone)
                if client:
                    await client.disconnect()
                    clients.pop(phone)

                # Delete session file
                session_path = os.path.join(SESSIONS_DIR, f"{phone}.session")
                if os.path.exists(session_path):
                    os.remove(session_path)
                    logger.info(f"[{phone}] Session file deleted.")

        if removed:
            save_users(users)

async def watch_and_run_bots():
    asyncio.create_task(cleanup_expired_users())
    known_phones = set()
    while True:
        try:
            users = load_users()
            for phone, config in users.items():
                if phone not in known_phones:
                    known_phones.add(phone)
                    asyncio.create_task(run_user_bot(config))
        except Exception as e:
            logger.error(f"Watcher error: {e}")
        await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(watch_and_run_bots())


@client.on(events.NewMessage(pattern=r'\.delay (\d+)s'))
async def update_delay(event):
    new_delay = int(event.pattern_match.group(1))
    if new_delay < 5:
        await event.respond("❌ Minimum allowed delay is 5 seconds.")
        return

    users = load_users()
    phone = config["phone"]
    users[phone]["msg_delay_sec"] = new_delay
    save_users(users)
    await event.respond(f"✅ Message delay updated to {new_delay} seconds.")
    logger.info(f"[{phone}] Updated msg_delay_sec to {new_delay} sec")


@client.on(events.NewMessage(pattern=r'\.addgroup (.+)'))
async def add_group(event):
    group_link = event.pattern_match.group(1).strip()
    if not group_link.startswith("https://t.me/"):
        await event.respond("❌ Invalid group link. Must start with https://t.me/")
        return

    users = load_users()
    phone = config["phone"]
    user_data = users.get(phone, {})
    groups = user_data.get("groups", [])
    if group_link not in groups:
        groups.append(group_link)
        user_data["groups"] = groups
        users[phone] = user_data
        save_users(users)
        await event.respond(f"✅ Group link added: {group_link}")
    else:
        await event.respond(f"ℹ️ Group already exists: {group_link}")


@client.on(events.NewMessage(pattern=r'\.groups'))
async def list_groups(event):
    users = load_users()
    phone = config["phone"]
    user_data = users.get(phone, {})
    groups = user_data.get("groups", [])

    if not groups:
        await event.respond("📭 No groups saved.")
    else:
        group_list = "\n".join(f"- {g}" for g in groups)
        await event.respond(f"📋 Saved Groups:\n{group_list}")
