import os
import json
from datetime import datetime, timedelta

USERS_DIR = "users"

def update_plan_expiry():
    print("--- Set Plan Expiry for Users ---")
    for filename in os.listdir(USERS_DIR):
        if filename.endswith(".json"):
            path = os.path.join(USERS_DIR, filename)
            with open(path, "r") as f:
                config = json.load(f)

            phone = config.get("phone", filename.replace(".json", ""))
            name = config.get("name", "Unknown")

            print(f"User: {name} ({phone})")
            try:
                days = int(input("  Enter plan duration in days (e.g. 30): "))
                expiry = (datetime.now() + timedelta(days=days)).isoformat()
                config["plan_expiry"] = expiry
                with open(path, "w") as f:
                    json.dump(config, f, indent=2)
                print(f"  ✅ Plan updated to expire on {expiry}")
            except ValueError:
                print("  ❌ Invalid input. Skipping.
")

if __name__ == "__main__":
    update_plan_expiry()
