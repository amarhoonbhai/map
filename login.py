
import os
import json
import subprocess
from datetime import datetime, timedelta
from pymongo import MongoClient
from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError
from colorama import Fore, Style, init

init(autoreset=True)

MONGO_URI = "mongodb+srv://rahul:rahulkr@cluster0.szdpcp6.mongodb.net/?retryWrites=true&w=majority"
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["telethon"]
users_collection = db["users"]

SESSIONS_DIR = "sessions"
os.makedirs(SESSIONS_DIR, exist_ok=True)

def list_users():
    users = list(users_collection.find())
    if not users:
        print(Fore.YELLOW + "No users logged in yet.")
        return
    print(Fore.CYAN + "Logged in users:")
    for user in users:
        print(f"- {user['name']} ({user['phone']})")

def login_new_user():
    name = input("Enter a name for this user: ")
    api_id = input("API ID: ")
    api_hash = input("API HASH: ")
    plan_days = int(input("Enter number of days for the plan: "))
    phone = input("Phone number (with country code): ")

    session_path = os.path.join(SESSIONS_DIR, f"{phone}.session")
    client = TelegramClient(session_path, int(api_id), api_hash)

    client.connect()
    if not client.is_user_authorized():
        client.send_code_request(phone)
        code = input("Enter the code sent to Telegram: ")
        try:
            client.sign_in(phone, code)
        except SessionPasswordNeededError:
            password = input("Enter 2FA password: ")
            client.sign_in(password=password)

    print(Fore.GREEN + f"[✔] {name} logged in successfully.")

    user_data = {
        "name": name,
        "phone": phone,
        "api_id": int(api_id),
        "api_hash": api_hash,
        "cycle_delay_min": 15,
        "msg_delay_sec": 5,
        "groups": [],
        "plan_expiry": (datetime.now() + timedelta(days=plan_days)).isoformat()
    }

    users_collection.update_one({"phone": phone}, {"$set": user_data}, upsert=True)
    client.disconnect()

    print("🔁 Launching runner...")
    subprocess.Popen(["python3", "runner_mongo_final.py"])

def delete_user():
    phone = input("Enter the phone number of the user to delete: ")
    result = users_collection.delete_one({"phone": phone})
    if result.deleted_count:
        session_file = os.path.join(SESSIONS_DIR, f"{phone}.session")
        if os.path.exists(session_file):
            os.remove(session_file)
        print(Fore.RED + f"User {phone} deleted.")
    else:
        print(Fore.YELLOW + "User not found.")

def start():
    while True:
        print(Style.BRIGHT + "\n--- Telethon Multi-User Manager ---")
        print("1. List users")
        print("2. Login new user")
        print("3. Delete user")
        print("4. Exit")
        choice = input("Choose an option: ").strip()
        if choice == '1':
            list_users()
        elif choice == '2':
            login_new_user()
        elif choice == '3':
            delete_user()
        elif choice == '4':
            print("Goodbye.")
            break
        else:
            print("Invalid choice. Try again.")

if __name__ == "__main__":
    start()
