"""
One-off migration: backfill default fields onto user documents that were
created before these fields existed in upsert_user()'s $setOnInsert block.

$setOnInsert only applies to brand-new documents, so any user created
before a field was added never got it — hence KeyError('balance') etc.
on old docs.

Run once:
    python -m yuki.scripts.backfill_user_defaults
(adjust the import path below to match wherever you place this file)
"""

import asyncio

from yuki.core.database import connect, disconnect, get_db

# Match these to whatever's currently in upsert_user's $setOnInsert block
DEFAULTS = {
    "balance": 500,
    "reputation": 0,
    "level": 1,
    "xp": 0,
    "title": None,
    "background": "default",
    "achievements": [],
    "daily_streak": 0,
    "last_daily": None,
    "married_to": None,
    "married_since": None,
    "total_messages": 0,
    "active_chats": [],
    "rank_score": 0,
}


async def backfill():
    # adjust URI / db name to match your actual connect() call in main.py
    await connect("mongodb+srv://ChatSphereDB:RadheyMaa@chatspheredb.shxwz5d.mongodb.net/?retryWrites=true&w=majority", "yukidb")

    db = get_db()
    updated = 0

    for field, default in DEFAULTS.items():
        result = await db.users.update_many(
            {field: {"$exists": False}},
            {"$set": {field: default}},
        )
        if result.modified_count:
            print(f"Backfilled '{field}' on {result.modified_count} docs")
            updated += result.modified_count

    print(f"Done. {updated} field-writes applied.")
    await disconnect()


if __name__ == "__main__":
    asyncio.run(backfill())