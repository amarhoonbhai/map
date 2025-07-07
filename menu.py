
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta

ACCOUNTS_DIR = "accounts"

def ensure_dirs():
    os.makedirs(ACCOUNTS_DIR, exist_ok=True)

def run_background(account_name):
    script_path = os.path.abspath("auto_forward_saved.py")
    session_file = os.path.join(ACCOUNTS_DIR, f"{account_name}.session")
    if not os.path.exists(session_file):
        print(f"❌ Session for {account_name} not found.")
        return

    # Check plan expiry
    config_path = os.path.join(ACCOUNTS_DIR, f"{account_name}_config.txt")
    if not os.path.exists(config_path):
        print(f"⚠️ Plan config missing for {account_name}. Skipping.")
        return

    with open(config_path) as f:
        lines = f.readlines()
        days = int([line for line in lines if line.startswith("days=")][0].split("=")[1])
        start = [line for line in lines if line.startswith("start=")][0].split("=")[1].strip()
        start_date = datetime.strptime(start, "%Y-%m-%d")
        if datetime.now() > start_date + timedelta(days=days):
            print(f"⛔ Plan expired for {account_name}.")
            return

    cmd = f"nohup python3 {script_path} > {account_name}_log.txt 2>&1 &"
    os.system(cmd)
    print(f"✅ Started {account_name} in background. Log: {account_name}_log.txt")

def login_new_account():
    from getpass import getpass

    print("🔐 Adding a new Telegram account")
    account_name = input("Enter a unique account name (e.g., user1): ").strip().replace(" ", "_")
    api_id = input("Enter API ID: ").strip()
    api_hash = input("Enter API Hash: ").strip()
    phone = input("Enter phone number (with country code): ").strip()

    script_filename = f"temp_login_{account_name}.py"
    session_path = os.path.join(ACCOUNTS_DIR, f"{account_name}.session")

    with open(script_filename, "w") as f:
        f.write(f"""
from telethon.sync import TelegramClient

api_id = {api_id}
api_hash = '{api_hash}'
phone = '{phone}'

client = TelegramClient('{session_path}', api_id, api_hash)
client.connect()
if not client.is_user_authorized():
    client.send_code_request(phone)
    code = input("Please enter the code you received: ")
    client.sign_in(phone, code)
me = client.get_me()
print(f"✅  Login successful for {{me.first_name}}")
client.disconnect()
""")

    os.system(f"python3 {script_filename}")

    # Optional: Delete temp script after login
    os.remove(script_filename)

    print("💼 Choose a plan:")
    print("1. Basic Plan (10 sec interval)")
    print("2. Pro Plan (5 sec interval)")
    print("3. Premium Plan (1 sec interval)")
    choice = input("Enter your choice (1/2/3): ").strip()

    plan_map = {"1": 10, "2": 5, "3": 1}
    interval = plan_map.get(choice, 10)
    days = input("📆 Enter number of days for the plan: ").strip()

    config_path = os.path.join(ACCOUNTS_DIR, f"{account_name}_config.txt")
    with open(config_path, "w") as cfg:
        cfg.write(f"interval={interval}
")
        cfg.write(f"days={days}
")
        cfg.write(f"start={datetime.now().strftime('%Y-%m-%d')}
")

    run_background(account_name)

def list_accounts():
    sessions = [f for f in os.listdir(ACCOUNTS_DIR) if f.endswith(".session")]
    if not sessions:
        print("⚠️ No accounts found.")
        return
    print("🧾 Accounts:")
    for sess in sessions:
        account_name = sess.replace(".session", "")
        config_path = os.path.join(ACCOUNTS_DIR, f"{account_name}_config.txt")
        status = "✅ Active"
        if os.path.exists(config_path):
            with open(config_path) as f:
                lines = f.readlines()
                days = int([line for line in lines if line.startswith("days=")][0].split("=")[1])
                start = [line for line in lines if line.startswith("start=")][0].split("=")[1].strip()
                start_date = datetime.strptime(start, "%Y-%m-%d")
                if datetime.now() > start_date + timedelta(days=days):
                    status = "⛔ Expired"
        print(f"• {account_name} — {status}")

def main_menu():
    ensure_dirs()
    while True:
        print("\n===== TELEGRAM BOT MENU =====")
        print("1. Add new account & run")
        print("2. List added accounts")
        print("3. Exit")

        choice = input("Choose an option: ").strip()
        if choice == "1":
            login_new_account()
        elif choice == "2":
            list_accounts()
        elif choice == "3":
            print("👋 Exiting...")
            break
        else:
            print("❌ Invalid option.")

if __name__ == "__main__":
    main_menu()
