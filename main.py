
# Default API credentials (edit as needed)
DEFAULT_API_ID = 28464245
DEFAULT_API_HASH = "6fe23ca19e7c7870dc2aff57fb05c4d9"


import os
import json
import asyncio
import logging
import sqlite3
import time
from datetime import datetime
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError
from colorama import Fore, Style, init

init(autoreset=True)


# Plan definitions
PLAN_FEATURES = {
    "basic": {"max_groups": 1, "min_delay": 30, "max_days": 1},
    "pro": {"max_groups": 5, "min_delay": 15, "max_days": 7},
    "vip": {"max_groups": float('inf'), "min_delay": 10, "max_days": 30}
}


SESSIONS_DIR = "sessions"
USERS_DIR = "users"
USERS_FILE = "users.json"

os.makedirs(SESSIONS_DIR, exist_ok=True)
os.makedirs(USERS_DIR, exist_ok=True)
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, 'w') as f:
        json.dump({}, f)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

clients = {}
session_locks = {}

def load_users():
    with open(USERS_FILE, 'r') as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

def list_users(users):
    if not users:
        print(Fore.YELLOW + "No users logged in yet.")
        return
    print(Fore.CYAN + "Logged in users:")
    for phone, data in users.items():
        print(f"- {data['name']} ({phone})")

async def login_new_user():
    print(Fore.CYAN + "New User Login")

    phone = input("Enter phone number: ")
    use_default = input("Use default API credentials? (Y/n): ").strip().lower()
    if use_default == 'n':
        api_id = int(input("Enter API ID: "))
        api_hash = input("Enter API Hash: ")
    else:
        api_id = DEFAULT_API_ID
        api_hash = DEFAULT_API_HASH
    
    name = input("Enter display name: ")
    plan_days = int(input("Enter plan duration in days: "))
    expires_at = (datetime.now() + timedelta(days=plan_days)).isoformat()

    session_path = os.path.join(SESSIONS_DIR, f"{phone}.session")
    client = TelegramClient(session_path, api_id, api_hash)

    try:
        await client.start(phone=phone)
        me = await client.get_me()
        print(Fore.GREEN + f"Login successful: {me.first_name}")

        users = load_users()
        users[phone] = {
            "name": name,
            "phone": phone,
            "api_id": api_id,
            "api_hash": api_hash,
            "groups": [],
            "msg_delay_sec": 5,
            "cycle_delay_min": 15,
            "expires_at": expires_at,
            "plan_type": plan_type,
            "max_groups": PLAN_FEATURES[plan_type]["max_groups"],
            "min_delay": PLAN_FEATURES[plan_type]["min_delay"]
        }
        save_users(users)

        # Auto-run bot after login
        await run_user_bot(users[phone])

    except SessionPasswordNeededError:
        print(Fore.RED + "2FA enabled. Please remove 2FA and try again.")
    except Exception as e:
        print(Fore.RED + f"Login failed: {e}")
    finally:
        await client.disconnect()

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

        try:
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

            @client.on(events.NewMessage(pattern='/ping'))
            async def handler(event):
                await event.respond('pong!')

            await client.run_until_disconnected()

        except sqlite3.OperationalError as e:
            logger.error(f"[{phone}] SQLite lock error: {e}")
        except Exception as e:
            logger.error(f"[{phone}] Error: {e}")
        finally:
            await client.disconnect()

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

def menu():
    while True:
        print(Style.BRIGHT + "\n--- Telegram Bot Menu ---")
        print("[1] Add new user (login)")
        print("[2] Start all user bots")
        print("[3] Exit")
        choice = input("Select an option: ")

        if choice == '1':
            asyncio.run(login_new_user())
        elif choice == '2':
            print(Fore.CYAN + "Starting bot runner...")
            asyncio.run(watch_and_run_bots())
        
        elif choice == '3':
            print(Fore.CYAN + "Goodbye.")
            break
        else:
            print(Fore.RED + "Invalid choice.")

if __name__ == "__main__":
    menu()

            @client.on(events.NewMessage(pattern=r'\.time (\d+)m'))
            async def update_cycle(event):
                new_cycle = int(event.pattern_match.group(1))
                if new_cycle < 10:
                    await event.respond("❌ Minimum allowed cycle is 10 minutes.")
                    return

                users = load_users()
                phone = config["phone"]
                users[phone]["cycle_delay_min"] = new_cycle
                save_users(users)

        # Auto-run bot after login
        await run_user_bot(users[phone])
                await event.respond(f"✅ Cycle time updated to {new_cycle} minutes.")
                logger.info(f"[{phone}] Updated cycle_delay_min to {new_cycle} min")

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

        # Auto-run bot after login
        await run_user_bot(users[phone])

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
                phone = config["phone"]
                user_data = users.get(phone, {})
                delay = user_data.get("msg_delay_sec", 5)
                cycle = user_data.get("cycle_delay_min", 15)
                expires = user_data.get("expires_at", "N/A")
                await event.respond(f"📊 Status:\nDelay: {delay} sec\nCycle: {cycle} min\nExpires: {expires}")

            @client.on(events.NewMessage(pattern=r'\.info'))
            async def show_info(event):
                me = await client.get_me()
                users = load_users()
                phone = config["phone"]
                expires = users.get(phone, {}).get("expires_at", "N/A")
                await event.respond(f"👤 Info:\nName: {me.first_name}\nID: {me.id}\nUsername: @{me.username or 'N/A'}\nPlan Expires: {expires}")
