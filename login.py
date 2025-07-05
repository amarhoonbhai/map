import os
import json
import asyncio
from datetime import datetime, timedelta
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError

USERS_FILE = "users.json"

def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

async def login_new_user():
    from runner import run_user_bot

    print("🔐 Login a new user")
    phone = input("📱 Enter phone number: ").strip()
    display_name = input("👤 Enter display name: ").strip()
    plan_days = int(input("📆 Enter plan duration (in days): ").strip())
    api_id = int(input("🔢 Enter API ID: ").strip())
    api_hash = input("🔑 Enter API HASH: ").strip()

    client = TelegramClient(StringSession(), api_id, api_hash)
    await client.connect()

    if not await client.is_user_authorized():
        try:
            await client.send_code_request(phone)
            code = input("🔑 Enter the OTP sent to your Telegram: ").strip()
            await client.sign_in(phone, code)
        except SessionPasswordNeededError:
            pw = input("🔐 Two-Step Password: ").strip()
            await client.sign_in(password=pw)

    string_session = client.session.save()
    me = await client.get_me()
    print("✅  Login successful:", me.first_name)

    users = load_users()
    expires = (datetime.now() + timedelta(days=plan_days)).isoformat()
    users[phone] = {
        "phone": phone,
        "api_id": api_id,
        "api_hash": api_hash,
        "name": display_name,
        "session": string_session,
        "expires_at": expires,
        "msg_delay_sec": 5,
        "cycle_delay_min": 15,
        "groups": []
    }
    save_users(users)

    await client.disconnect()
    print("🚀 Bot runner started in background.")
    asyncio.create_task(run_user_bot(users[phone]))

def menu():
    while True:
        print("--- Telegram Bot Menu ---")
        print("[1] Add new user (login)")
        print("[2] Start all user bots")
        print("[3] Exit")
        choice = input("Select an option: ").strip()
        if choice == "1":
            asyncio.run(login_new_user())
        elif choice == "2":
            from runner import watch_and_run_bots
            asyncio.run(watch_and_run_bots())
        elif choice == "3":
            break
        else:
            print("❌ Invalid choice.")

if __name__ == "__main__":
    menu()
