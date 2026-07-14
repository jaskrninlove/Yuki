"""
Yuki Database - Marriage
Copyright © Jass
"""

from __future__ import annotations

from datetime import datetime, timezone

from pymongo.collection import Collection

from yuki.core.config import DB

marriages: Collection = DB.marriages
married_users: Collection = DB.married_users


def _marriage_id(a: int, b: int) -> str:
    return f"{min(a, b)}_{max(a, b)}"


def is_married(user_id: int) -> bool:
    return married_users.find_one({"_id": user_id}) is not None


def _get_married_doc(user_id: int):
    doc = married_users.find_one({"_id": user_id})
    if doc and "last_love" not in doc:
        married_users.update_one({"_id": user_id}, {"$set": {"last_love": None}})
        doc["last_love"] = None
    return doc


def get_partner_id(user_id: int):
    doc = _get_married_doc(user_id)
    return doc.get("partner_id") if doc else None


def get_marriage(user_id: int):
    doc = _get_married_doc(user_id)
    if not doc:
        return None
    return marriages.find_one({"_id": doc["marriage_id"]})


def create_marriage(user1_id: int, user2_id: int) -> bool:
    """Atomic-ish two-phase insert: relies on unique _id in married_users
    to guarantee a user can never end up in two marriages at once."""
    if is_married(user1_id) or is_married(user2_id):
        return False

    mid = _marriage_id(user1_id, user2_id)
    now = datetime.now(timezone.utc)

    try:
        marriages.insert_one({
            "_id": mid,
            "user1": user1_id,
            "user2": user2_id,
            "married_since": now,
            "love_points": 0,
        })
    except Exception:
        return False

    try:
        married_users.insert_one({
            "_id": user1_id,
            "partner_id": user2_id,
            "marriage_id": mid,
            "married_since": now,
            "last_love": None,
        })
    except Exception:
        marriages.delete_one({"_id": mid})
        return False

    try:
        married_users.insert_one({
            "_id": user2_id,
            "partner_id": user1_id,
            "marriage_id": mid,
            "married_since": now,
            "last_love": None,
        })
    except Exception:
        married_users.delete_one({"_id": user1_id})
        marriages.delete_one({"_id": mid})
        return False

    return True


def divorce(user_id: int):
    doc = married_users.find_one({"_id": user_id})
    if not doc:
        return None

    partner_id = doc["partner_id"]
    mid = doc["marriage_id"]

    married_users.delete_one({"_id": user_id})
    married_users.delete_one({"_id": partner_id})
    marriages.delete_one({"_id": mid})

    return partner_id


def add_love(user_id: int, amount: int) -> bool:
    doc = married_users.find_one({"_id": user_id})
    if not doc:
        return False
    marriages.update_one({"_id": doc["marriage_id"]}, {"$inc": {"love_points": amount}})
    return True


def get_love(user_id: int) -> int:
    m = get_marriage(user_id)
    return m.get("love_points", 0) if m else 0


def get_last_love(user_id: int):
    doc = _get_married_doc(user_id)
    return doc.get("last_love") if doc else None


def set_last_love(user_id: int, date):
    married_users.update_one({"_id": user_id}, {"$set": {"last_love": date}})


def top_love(limit: int = 10):
    return list(marriages.find().sort("love_points", -1).limit(limit))