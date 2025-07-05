
import bson
from pymongo import MongoClient
from telethon.sessions import Session
from telethon.tl.types import InputPeerEmpty

class MongoSession(Session):
    def __init__(self, phone, mongo_uri, db_name="telethon", col_name="sessions"):
        super().__init__()
        self.phone = phone
        self.mongo_uri = mongo_uri
        self.db_name = db_name
        self.col_name = col_name
        self._setup_db()
        self._load()

    def _setup_db(self):
        self.client = MongoClient(self.mongo_uri)
        self.db = self.client[self.db_name]
        self.col = self.db[self.col_name]

    def _load(self):
        doc = self.col.find_one({"_id": self.phone})
        self._dc_id = doc.get("dc_id") if doc else None
        self._server_address = doc.get("server_address") if doc else None
        self._port = doc.get("port") if doc else None
        self._auth_key = self._decode_bytes(doc.get("auth_key")) if doc and doc.get("auth_key") else None
        self._takeout_id = doc.get("takeout_id") if doc else None
        self._entity_cache = doc.get("entity_cache", {}) if doc else {}

    def _update_db(self):
        doc = {
            "_id": self.phone,
            "dc_id": self._dc_id,
            "server_address": self._server_address,
            "port": self._port,
            "auth_key": self._encode_bytes(self._auth_key) if self._auth_key else None,
            "takeout_id": self._takeout_id,
            "entity_cache": self._entity_cache
        }
        self.col.replace_one({"_id": self.phone}, doc, upsert=True)

    def save(self):
        self._update_db()

    def delete(self):
        self.col.delete_one({"_id": self.phone})

    @property
    def dc_id(self):
        return self._dc_id

    @property
    def server_address(self):
        return self._server_address

    @property
    def port(self):
        return self._port

    @property
    def auth_key(self):
        return self._auth_key

    @property
    def takeout_id(self):
        return self._takeout_id

    @takeout_id.setter
    def takeout_id(self, value):
        self._takeout_id = value

    def set_dc(self, dc_id, server_address, port):
        self._dc_id = dc_id
        self._server_address = server_address
        self._port = port

    def get_update_state(self, entity_id):
        return None

    def set_update_state(self, entity_id, state):
        pass

    def get_update_states(self):
        return []

    def process_entities(self, tlo):
        if not hasattr(self, "_entity_cache"):
            self._entity_cache = {}
        if isinstance(tlo, list):
            for entity in tlo:
                if hasattr(entity, "id"):
                    self._entity_cache[str(entity.id)] = entity.to_dict()
        elif hasattr(tlo, "id"):
            self._entity_cache[str(tlo.id)] = tlo.to_dict()

    def get_entity_rows_by_phone(self, phone):
        return []

    def get_entity_rows_by_username(self, username):
        return []

    def get_entity_rows_by_name(self, name):
        return []

    def get_entity_rows_by_id(self, id, exact=True):
        return []

    def get_file(self):
        return None

    @property
    def cache_file(self):
        return None



import os
import asyncio
import logging
from datetime import datetime, timedelta
from pymongo import MongoClient
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError, RPCError
from telethon.sessions import Session

# ---------------------------------------
# Custom MongoDB session implementation
# ---------------------------------------

class MongoSession(Session):
    def __init__(self, phone, mongo_uri, db_name="telethon", col_name="sessions"):
        super().__init__()
        self.phone = phone
        self.mongo_uri = mongo_uri
        self.db_name = db_name
        self.col_name = col_name
        self._setup_db()
        self._load()

    def _setup_db(self):
        self.client = MongoClient(self.mongo_uri)
        self.db = self.client[self.db_name]
        self.col = self.db[self.col_name]

    def _load(self):
        doc = self.col.find_one({"_id": self.phone})
        if doc:
            self._dc_id = doc.get("dc_id")
            self._server_address = doc.get("server_address")
            self._port = doc.get("port")
            self._auth_key = self._decode_bytes(doc.get("auth_key"))
        else:
            self._dc_id = 0
            self._server_address = None
            self._port = None
            self._auth_key = None

    def _update_db(self):
        doc = {
            "_id": self.phone,
            "dc_id": self._dc_id,
            "server_address": self._server_address,
            "port": self._port,
            "auth_key": self._encode_bytes(self._auth_key) if self._auth_key else None,
        }
        self.col.replace_one({"_id": self.phone}, doc, upsert=True)

    def save(self):
        self._update_db()

    def delete(self):
        self.col.delete_one({"_id": self.phone})

# ---------------------------------------
# Main Runner Logic
# ---------------------------------------

MONGO_URI = "mongodb+srv://rahul:rahulkr@cluster0.szdpcp6.mongodb.net/?retryWrites=true&w=majority"
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["telethon"]
users_collection = db["users"]

API_ID = 20210979
API_HASH = "8cc33da16acda11d393c0cfffab8c1a0"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

clients = {}
started_phones = set()

async def run_user_bot(config):
    phone = config["phone"]
    if phone in started_phones:
        return

    groups = config.get("groups", [])
    delay = config.get("msg_delay_sec", 5)
    cycle = config.get("cycle_delay_min", 15)

    user_state = {
        "delay": delay,
        "cycle": cycle,
    }

    session = MongoSession(phone, MONGO_URI)
    client = TelegramClient(session, API_ID, API_HASH)

    try:
        await client.start()
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
    logger.info(f"[✔] Started bot for {config.get('name', phone)}")

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
            expiry = config.get("plan_expiry", "N/A")
            reply = (
                f"❀ User Info:\n❀ Name: {config.get('name')}\n❀ Cycle Delay: {user_state['cycle']} min\n"
                f"❀ Message Delay: {user_state['delay']} sec\n❀ Groups: {len(groups)}\n❀ Plan Expiry: {expiry}"
            )
            await event.respond(reply)

        elif text.startswith(".addgroup"):
            parts = text.split()
            if len(parts) == 2:
                new_group = parts[1]
                if new_group not in groups:
                    groups.append(new_group)
                    config["groups"] = groups
                    users_collection.update_one({"phone": phone}, {"$set": config})
                    await event.respond("❀ Group added.")
                else:
                    await event.respond("❀ Group already in list.")

        elif text.startswith(".delgroup"):
            parts = text.split()
            if len(parts) == 2 and parts[1] in groups:
                groups.remove(parts[1])
                config["groups"] = groups
                users_collection.update_one({"phone": phone}, {"$set": config})
                await event.respond("❀ Group removed.")

        elif text.startswith(".groups"):
            if groups:
                await event.respond("❀ Groups:\n" + "\n".join([g for g in groups if "t.me" in g]))
            else:
                await event.respond("📋 No groups configured.")

        elif text.startswith(".setplan"):
            parts = text.split()
            if len(parts) == 2 and parts[1].isdigit():
                days = int(parts[1])
                expiry_date = (datetime.now() + timedelta(days=days)).isoformat()
                config["plan_expiry"] = expiry_date
                users_collection.update_one({"phone": phone}, {"$set": {"plan_expiry": expiry_date}})
                await event.respond(f"📆 Plan set to expire in {days} days.")

        elif text.startswith(".activate"):
            started_phones.discard(phone)
            asyncio.create_task(run_user_bot(config))
            await event.respond("🔄 Re-activated your bot session.")

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
                ".setplan <days> — Set plan expiry\n"
                ".activate — Restart bot session\n"
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
        for config in users_collection.find():
            expiry = config.get("plan_expiry")
            if expiry and datetime.now() > datetime.fromisoformat(expiry):
                logger.info(f"[⏳] Plan expired for {config['phone']}. Skipping.")
                continue
            asyncio.create_task(run_user_bot(config))
        await asyncio.sleep(60)

async def main():
    await user_loader()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutdown requested. Exiting.")
