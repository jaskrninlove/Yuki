"""
Yuki Bot - Database Core
MongoDB centralized helpers.
"""

import logging
import random
from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING, ReturnDocument

log = logging.getLogger("yuki.db")

_client: AsyncIOMotorClient | None = None
_db = None

_sticker_cache: list[dict] = []
_sticker_cache_built: bool = False
_MAX_CACHE = 300

_memory_cache: dict[int, dict[str, dict]] = {}


async def connect(uri: str, db_name: str):
    global _client, _db

    _client = AsyncIOMotorClient(
        uri,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
        socketTimeoutMS=10000,
        maxPoolSize=10,
    )

    _db = _client[db_name]

    await _ensure_indexes()
    await _warm_sticker_cache()

    log.info("✅ MongoDB connected — db: %s", db_name)


def get_db():
    if _db is None:
        raise RuntimeError("Database not connected.")
    return _db


async def disconnect():
    global _client

    if _client:
        _client.close()
        log.info("🔌 MongoDB disconnected")


async def _ensure_indexes():
    db = get_db()

    await db.users.create_index([("user_id", ASCENDING)], unique=True)
    await db.groups.create_index([("chat_id", ASCENDING)], unique=True)

    await db.messages.create_index([("chat_id", ASCENDING), ("date", DESCENDING)])
    await db.messages.create_index([("user_id", ASCENDING), ("date", DESCENDING)])

    await db.stickers.create_index([("file_id", ASCENDING)], unique=True)
    await db.stickers.create_index([("uses", DESCENDING)])
    await db.stickers.create_index([("emoji", ASCENDING)])

    await db.safe_stickers.create_index([("file_id", ASCENDING)], unique=True)

    await db.gifts.create_index([("receiver_id", ASCENDING)])
    await db.gifts.create_index([("sender_id", ASCENDING)])

    await db.chat_memory.create_index([("chat_id", ASCENDING), ("keyword", ASCENDING)])
    await db.chat_settings.create_index([("chat_id", ASCENDING)], unique=True)

    await db.notes.create_index([("chat_id", ASCENDING), ("name", ASCENDING)], unique=True)
    await db.filters.create_index([("chat_id", ASCENDING), ("name", ASCENDING)], unique=True)
    await db.afk.create_index([("user_id", ASCENDING)], unique=True)
    await db.whispers.create_index([("wid", ASCENDING)], unique=True)

"""
More additions for yuki/core/database.py — needed by yuki/modules/rankings/helpers.py.

Place these alongside the ones from database_additions.py (after get_user/get_db).
"""


def _display_name(doc: dict) -> str:
    return doc.get("first_name") or doc.get("username") or "Unknown"


async def richest(limit: int = 10) -> list[dict]:
    cursor = get_db().users.find(
        {},
        {"user_id": 1, "first_name": 1, "username": 1, "balance": 1},
    ).sort("balance", DESCENDING).limit(limit)

    docs = [doc async for doc in cursor]

    for doc in docs:
        doc["name"] = _display_name(doc)

    return docs


async def highest_level(limit: int = 10) -> list[dict]:
    cursor = get_db().users.find(
        {},
        {"user_id": 1, "first_name": 1, "username": 1, "level": 1, "xp": 1},
    ).sort("level", DESCENDING).limit(limit)

    docs = [doc async for doc in cursor]

    for doc in docs:
        doc["name"] = _display_name(doc)

    return docs


async def most_active(limit: int = 10) -> list[dict]:
    cursor = get_db().users.find(
        {},
        {"user_id": 1, "first_name": 1, "username": 1, "total_messages": 1},
    ).sort("total_messages", DESCENDING).limit(limit)

    docs = [doc async for doc in cursor]

    for doc in docs:
        doc["name"] = _display_name(doc)

    return docs


async def get_by_id(user_id: int) -> dict | None:
    user = await get_user(user_id)

    if user:
        user["name"] = _display_name(user)

    return user


async def global_stats() -> dict:
    db = get_db()

    users_count = await db.users.count_documents({})
    messages_count = await db.messages.count_documents({})
    married_count = await db.users.count_documents({"married_to": {"$ne": None}})

    money_agg = await db.users.aggregate(
        [{"$group": {"_id": None, "total": {"$sum": "$balance"}}}]
    ).to_list(1)
    money = money_agg[0]["total"] if money_agg else 0

    levels_agg = await db.users.aggregate(
        [{"$group": {"_id": None, "total": {"$sum": "$level"}}}]
    ).to_list(1)
    levels = levels_agg[0]["total"] if levels_agg else 0

    # TODO: wire up real total once yuki/database/reputation.py schema is confirmed
    reputation_total = 0

    return {
        "users": users_count,
        "messages": messages_count,
        "money": money,
        "levels": levels,
        "reputation": reputation_total,
        "married": married_count,
    }

"""
Additions for yuki/core/database.py to support the XP listener.

1. Add this import near the top, alongside the existing pymongo import:

    from pymongo import ASCENDING, DESCENDING, ReturnDocument

2. Add the two functions below (place them near get_user/upsert_user).
"""

async def ensure_user(user_id: int, first_name: str = "", username: str = "") -> dict:
    """
    Fetch a user's document, creating it (with defaults from upsert_user's
    $setOnInsert block) if it doesn't exist yet. Always returns a dict.
    """
    user = await get_user(user_id)

    if user is None:
        await upsert_user(
            user_id,
            {
                "first_name": first_name,
                "username": username,
            },
        )
        user = await get_user(user_id)

    return user


def _level_for_xp(xp: int) -> int:
    """
    XP -> level curve. Placeholder: 100 xp per level.
    Tune this to whatever progression you actually want
    (e.g. an increasing threshold per level).
    """
    return (xp // 100) + 1


async def add_xp(user_id: int, amount: int) -> dict:
    """
    Increment a user's XP, recompute their level if it changed,
    and return the updated user document.
    """
    user = await get_db().users.find_one_and_update(
        {"user_id": user_id},
        {"$inc": {"xp": amount}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )

    new_level = _level_for_xp(user.get("xp", 0))

    if new_level != user.get("level", 1):
        await get_db().users.update_one(
            {"user_id": user_id},
            {"$set": {"level": new_level}},
        )
        user["level"] = new_level

    return user

async def _warm_sticker_cache():
    global _sticker_cache, _sticker_cache_built

    try:
        docs = await get_db().stickers.find(
            {},
            {"file_id": 1, "emoji": 1, "set_name": 1},
        ).sort("uses", DESCENDING).limit(_MAX_CACHE).to_list(_MAX_CACHE)

        _sticker_cache = docs
        _sticker_cache_built = True

        log.info("🎴 Sticker cache warmed: %d stickers", len(_sticker_cache))

    except Exception as e:
        log.warning("Sticker cache warm failed: %s", e)


async def get_user(user_id: int) -> dict | None:
    return await get_db().users.find_one({"user_id": user_id})


async def upsert_user(user_id: int, data: dict):
    data = dict(data or {})
    data.pop("user_id", None)

    await get_db().users.update_one(
        {"user_id": user_id},
        {
            "$set": data,
            "$setOnInsert": {
                "user_id": user_id,
                "joined": datetime.utcnow(),
                "total_messages": 0,
                "active_chats": [],
                "xp": 0,
                "rank_score": 0,
                # NEW
    "balance": 500,
    "reputation": 0,
    "level": 1,
    "title": None,
    "background": "default",
    "achievements": [],
    "daily_streak": 0,
    "last_daily": None,
    "married_to": None,
    "married_since": None,
            },
        },
        upsert=True,
    )


async def increment_user_messages(user_id: int, chat_id: int):
    from pymongo import ReturnDocument as _RD

    updated = await get_db().users.find_one_and_update(
        {"user_id": user_id},
        {
            "$inc": {
                "total_messages": 1,
                "messages": 1,
            },
            "$addToSet": {
                "active_chats": chat_id,
            },
            "$setOnInsert": {
                "user_id": user_id,
                "joined": datetime.utcnow(),
                "xp": 0,
                "rank_score": 0,
            },
        },
        upsert=True,
        return_document=_RD.AFTER,
    )

    if updated:
        try:
            from yuki.database.achievements import check_message_milestones
            check_message_milestones(user_id, updated.get("total_messages", 0))
        except Exception as e:
            log.debug("Achievement check failed: %s", e)

async def get_all_users() -> list[int]:
    cursor = get_db().users.find({}, {"user_id": 1})
    return [doc["user_id"] async for doc in cursor if doc.get("user_id")]


async def count_users() -> int:
    return await get_db().users.count_documents({})


async def get_group(chat_id: int) -> dict | None:
    return await get_db().groups.find_one({"chat_id": chat_id})


async def upsert_group(chat_id: int, data: dict):
    data = dict(data or {})
    data.pop("chat_id", None)

    await get_db().groups.update_one(
        {"chat_id": chat_id},
        {
            "$set": data,
            "$setOnInsert": {
                "chat_id": chat_id,
                "joined": datetime.utcnow(),
            },
        },
        upsert=True,
    )


async def count_groups() -> int:
    return await get_db().groups.count_documents({"active": True})


async def save_sticker(file_id: str, emoji: str = "", set_name: str = ""):
    global _sticker_cache

    if not file_id:
        return

    doc = {
        "file_id": file_id,
        "emoji": emoji,
        "set_name": set_name,
    }

    existing_ids = {s.get("file_id") for s in _sticker_cache}

    if file_id not in existing_ids:
        _sticker_cache.append(doc)

        if len(_sticker_cache) > _MAX_CACHE:
            _sticker_cache = _sticker_cache[-_MAX_CACHE:]

    try:
        await get_db().stickers.update_one(
            {"file_id": file_id},
            {
                "$set": {
                    "emoji": emoji,
                    "set_name": set_name,
                },
                "$inc": {
                    "uses": 1,
                },
                "$setOnInsert": {
                    "file_id": file_id,
                    "saved_at": datetime.utcnow(),
                },
            },
            upsert=True,
        )

    except Exception as e:
        log.debug("Sticker DB write failed: %s", e)


def get_cached_sticker(exclude_id: str = "", emoji_filter: str = "") -> str | None:
    if not _sticker_cache:
        return None

    pool = _sticker_cache

    if emoji_filter:
        filtered = [s for s in pool if s.get("emoji") == emoji_filter]
        if filtered:
            pool = filtered

    if exclude_id:
        pool = [s for s in pool if s.get("file_id") != exclude_id]

    if not pool:
        return None

    sample = pool[-100:] if len(pool) > 100 else pool
    return random.choice(sample).get("file_id")


async def get_random_sticker(exclude_id: str = "", emoji_filter: str = "") -> str | None:
    cached = get_cached_sticker(exclude_id=exclude_id, emoji_filter=emoji_filter)

    if cached:
        return cached

    try:
        query = {}

        if emoji_filter:
            query["emoji"] = emoji_filter

        if exclude_id:
            query["file_id"] = {"$ne": exclude_id}

        docs = await get_db().stickers.find(query).sort("uses", DESCENDING).limit(50).to_list(50)

        if docs:
            return random.choice(docs).get("file_id")

    except Exception as e:
        log.debug("DB sticker fallback failed: %s", e)

    return None


async def count_stickers() -> int:
    safe_count = await get_db().safe_stickers.count_documents({})

    if safe_count:
        return safe_count

    if _sticker_cache_built:
        return len(_sticker_cache)

    return await get_db().stickers.count_documents({})


def sticker_cache_size() -> int:
    return len(_sticker_cache)


async def save_chat_memory(chat_id: int, keyword: str, reply_text: str = "", reply_sticker: str = ""):
    kw = keyword.lower().strip()[:60]

    if not kw:
        return

    if chat_id not in _memory_cache:
        _memory_cache[chat_id] = {}

    _memory_cache[chat_id][kw] = {
        "reply_text": reply_text,
        "reply_sticker": reply_sticker,
    }

    try:
        await get_db().chat_memory.update_one(
            {
                "chat_id": chat_id,
                "keyword": kw,
            },
            {
                "$set": {
                    "reply_text": reply_text,
                    "reply_sticker": reply_sticker,
                },
                "$inc": {
                    "count": 1,
                },
                "$setOnInsert": {
                    "chat_id": chat_id,
                    "keyword": kw,
                },
            },
            upsert=True,
        )

    except Exception:
        pass


async def get_chat_memory(chat_id: int, keyword: str) -> dict | None:
    kw = keyword.lower().strip()[:60]

    if chat_id in _memory_cache and kw in _memory_cache[chat_id]:
        return _memory_cache[chat_id][kw]

    doc = await get_db().chat_memory.find_one({
        "chat_id": chat_id,
        "keyword": kw,
    })

    if doc:
        _memory_cache.setdefault(chat_id, {})[kw] = doc

    return doc


async def send_gift(sender_id: int, receiver_id: int, gift_id: str, gift_name: str, emoji: str):
    await get_db().gifts.insert_one({
        "sender_id": sender_id,
        "receiver_id": receiver_id,
        "gift_id": gift_id,
        "gift_name": gift_name,
        "emoji": emoji,
        "date": datetime.utcnow(),
    })


async def get_user_gifts(user_id: int) -> list:
    cursor = get_db().gifts.find(
        {"receiver_id": user_id},
    ).sort("date", DESCENDING).limit(20)

    return [doc async for doc in cursor]


async def count_all_gifts() -> int:
    return await get_db().gifts.count_documents({})


async def get_active_users(chat_id: int, limit: int = 20) -> list:
    cursor = get_db().users.find(
        {"active_chats": chat_id},
        {
            "user_id": 1,
            "first_name": 1,
            "username": 1,
            "total_messages": 1,
            "xp": 1,
            "rank_score": 1,
        },
    ).sort("total_messages", DESCENDING).limit(limit)

    return [doc async for doc in cursor]


async def get_maintenance() -> bool:
    doc = await get_db().settings.find_one({"key": "maintenance"})
    return doc.get("value", False) if doc else False


async def set_maintenance(value: bool):
    await get_db().settings.update_one(
        {"key": "maintenance"},
        {"$set": {"value": value}},
        upsert=True,
    )


async def log_message(chat_id: int, user_id: int, text: str = ""):
    try:
        await get_db().messages.insert_one({
            "chat_id": chat_id,
            "user_id": user_id,
            "text": text[:200] if text else "",
            "date": datetime.utcnow(),
        })

    except Exception as e:
        log.warning("log_message insert failed: %s", e)


async def count_messages_today() -> int:
    today = datetime.utcnow().replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )

    return await get_db().messages.count_documents({
        "date": {"$gte": today},
    })
