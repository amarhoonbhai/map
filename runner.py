
import os
import json
import asyncio
import logging
import sqlite3
from datetime import datetime
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError, RPCError

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

USERS_DIR = "users"
SESSIONS_DIR = "sessions"
clients = {}
started_phones = set()

async def run_user_bot(config):
    phone = config["phone"]
    if phone in started_phones:
        return

    session_path = os.path.join(SESSIONS_DIR, f"{phone}.session")
    api_id = int(config["api_id"])
    api_hash = config["api_hash"]
    groups = config.get("groups", [])
    delay = config.get("msg_delay_sec", 5)
    cycle = config.get("cycle_delay_min", 15)

    user_state = {
        "delay": delay,
        "cycle": cycle,
    }

    client = TelegramClient(session_path, api_id, api_hash)

    try:
        await client.start()
    except sqlite3.OperationalError as e:
        logger.error(f"[{phone}] SQLite lock error: {e}")
        return
    except SessionPasswordNeededError:
        logger.error(f"[{phone}] 2FA password required. Skipping.")
        return
    except RPCError as e:
        logger.error(f"[{phone}] RPC Error: {e}")
        return
    except Exception as e:
        logger.exception(f"[{phone}] Failed to start client: {e}")
        return

    started_phones.add(phone)
    logger.info(f"[✔] Started bot for {config['name']} ({phone})")

    @client.on(events.NewMessage)
    async def command_handler(event):
        me = await client.get_me()
        if event.sender_id != me.id:
            return

        text = event.raw_text.strip()

        if text.startswith(".time"):
            value = int(''.join(filter(str.isdigit, text)))
            if 'h' in text:
                user_state["cycle"] = value * 60
            else:
                user_state["cycle"] = value
            await event.respond(f"✅ Cycle delay set to {user_state['cycle']} minutes")

        elif text.startswith(".delay"):
            value = int(''.join(filter(str.isdigit, text)))
            user_state["delay"] = value
            await event.respond(f"✅ Message delay set to {value} seconds")

        elif text.startswith(".status"):
            await event.respond(
                f"📊 Status:\nCycle Delay: {user_state['cycle']} minutes\n"
                f"Message Delay: {user_state['delay']} seconds"
            )

        elif text.startswith(".info"):
            me = await client.get_me()
            expiry = "Developer" if me.id == 7876302875 else config.get("plan_expiry", "N/A")
            reply = (
                f"❀ User Info:\n❀ Name: {config.get('name')}\n❀ Cycle Delay: {user_state['cycle']} min\n"
                f"❀ Message Delay: {user_state['delay']} sec\n❀ Groups: {len(groups)}\n❀ Plan Expiry: {expiry}"
            )
            await event.respond(reply)

        elif text.startswith(".addgroup"):
            import re
            links = re.findall(r'https://t\.me/\S+', text)
            if not links:
                await event.respond("⚠️ No valid group links found.")
                return
            added = []
            skipped = []
            for link in links:
                if link not in groups:
                    groups.append(link)
                    added.append(link)
                else:
                    skipped.append(link)
            config["groups"] = groups
            with open(os.path.join(USERS_DIR, f"{phone}.json"), "w") as f:
                json.dump(config, f, indent=2)
            msg = ""
            if added:
                msg += f"✅ Added {len(added)} new group(s).\n"
            if skipped:
                msg += f"⚠️ Skipped {len(skipped)} duplicate(s)."
            await event.respond(msg.strip())

        elif text.startswith(".delgroup"):
            parts = text.split()
            if len(parts) == 2 and parts[1] in groups:
                groups.remove(parts[1])
                config["groups"] = groups
                with open(os.path.join(USERS_DIR, f"{phone}.json"), "w") as f:
                    json.dump(config, f, indent=2)
                await event.respond("❀ Group removed.")

        elif text.startswith(".groups"):
            if groups:
                await event.respond("❀ Groups:\n" + "\n".join([g for g in groups if "t.me" in g]))
            else:
                await event.respond("📋 No groups configured.")

        elif text.startswith(".help"):
            await event.respond(
                "🛠 Available Commands:\n"
                ".time <10m|1h> — Set cycle delay\n"
                ".delay <sec> — Set delay between messages\n"
                ".status — Show timing settings\n"
                ".info — Show full user info\n"
                ".addgroup <url> — Add group\n"
                ".delgroup <url> — Remove group\n"
                ".groups — List groups\n"
                ".help — Show this message"
            )

    async def forward_loop():
        while True:
            try:
                messages = await client.get_messages("me", limit=100)
                messages = list(reversed(messages))

                for msg in messages:
                    if msg.message is None and not msg.media:
                        continue

                    for group in groups:
                        try:
                            await client.forward_messages(group, msg)
                            logger.info(f"[{phone}] Forwarded to {group}")
                        except Exception as e:
                            logger.warning(f"[{phone}] Error forwarding to {group}: {e}")

                    await asyncio.sleep(user_state["delay"])

                logger.info(f"[{phone}] Cycle complete. Sleeping for {user_state['cycle']} minutes...")
                await asyncio.sleep(user_state["cycle"] * 60)
            except Exception as e:
                logger.exception(f"[{phone}] Error in forward loop: {e}")
                await asyncio.sleep(60)

    asyncio.create_task(forward_loop())
    await client.run_until_disconnected()

async def user_loader():
    while True:
        for file in os.listdir(USERS_DIR):
            if file.endswith(".json"):
                path = os.path.join(USERS_DIR, file)
                try:
                    with open(path, 'r') as f:
                        config = json.load(f)
                        expiry = config.get("plan_expiry")
                        if expiry and datetime.now() > datetime.fromisoformat(expiry):
                            logger.info(f"[⏳] Plan expired for {config['phone']}. Skipping.")
                            continue
                        asyncio.create_task(run_user_bot(config))
                except Exception as e:
                    logger.error(f"Error loading user config {file}: {e}")
        await asyncio.sleep(60)

async def main():
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    os.makedirs(USERS_DIR, exist_ok=True)
    await user_loader()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutdown requested. Exiting.")