
import os
import json
import asyncio
import subprocess
from datetime import datetime, timedelta
from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError
from colorama import Fore, Style, init

init(autoreset=True)

SESSIONS_DIR = "sessions"
USERS_FILE = "users.json"

os.makedirs(SESSIONS_DIR, exist_ok=True)
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, 'w') as f:
        json.dump({}, f)

DEFAULT_API_ID = 28464245
DEFAULT_API_HASH = "6fe23ca19e7c7870dc2aff57fb05c4d9"

def load_users():
    with open(USERS_FILE, 'r') as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

async def login_new_user():
    from runner import run_user_bot  # avoid circular import
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
            "expires_at": expires_at
        }
        save_users(users)
        await run_user_bot(users[phone])
    except SessionPasswordNeededError:
        print(Fore.RED + "2FA enabled. Please remove 2FA and try again.")
    except Exception as e:
        print(Fore.RED + f"Login failed: {e}")
    finally:
        await client.disconnect()

    # Start runner in background
    try:
        subprocess.Popen(["python3", "runner.py"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(Fore.CYAN + "Runner started in background.")
    except Exception as e:
        print(Fore.RED + f"Failed to start runner: {e}")

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
            subprocess.Popen(["python3", "runner.py"])
            print(Fore.GREEN + "Runner started in background.")
        elif choice == '3':
            print(Fore.CYAN + "Goodbye.")
            break
        else:
            print(Fore.RED + "Invalid choice.")

if __name__ == "__main__":
    menu()
