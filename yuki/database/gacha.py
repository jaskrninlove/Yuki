"""
Yuki Database - Gacha
Copyright © Jass
"""

from __future__ import annotations

from pymongo.collection import Collection

from yuki.core.config import DB

gacha_collection: Collection = DB.gacha_collection  # _id = user_id


def get_collection(user_id: int) -> dict:
    doc = gacha_collection.find_one({"_id": user_id})
    if doc:
        return doc
    return {"_id": user_id, "companions": {}, "total_pulls": 0}


def add_companion(user_id: int, companion_id: str):
    gacha_collection.update_one(
        {"_id": user_id},
        {
            "$inc": {
                f"companions.{companion_id}": 1,
                "total_pulls": 1,
            }
        },
        upsert=True,
    )


def get_companion_count(user_id: int, companion_id: str) -> int:
    doc = get_collection(user_id)
    return doc.get("companions", {}).get(companion_id, 0)


def unlocked_count(user_id: int) -> int:
    doc = get_collection(user_id)
    return len(doc.get("companions", {}))

def has_claimed_completion(user_id: int) -> bool:
    doc = get_collection(user_id)
    return doc.get("completion_claimed", False)


def mark_completion_claimed(user_id: int):
    gacha_collection.update_one(
        {"_id": user_id},
        {"$set": {"completion_claimed": True}},
        upsert=True,
    )