"""
Yuki Reputation Database
Copyright © Jass
"""

from pymongo.collection import Collection

from yuki.core.config import DB

reputation: Collection = DB.reputation


def get(user_id: int):
    data = reputation.find_one({"_id": user_id})

    if data:
        return data

    data = {
        "_id": user_id,
        "rep": 0,
        "given": 0,
        "last_rep": None,
    }

    reputation.insert_one(data)

    return data


def add(user_id: int, name: str = None):
    update = {"$inc": {"rep": 1}}
    if name:
        update["$set"] = {"name": name}
    reputation.update_one(
        {"_id": user_id},
        update,
        upsert=True,
    )


def given(user_id: int):
    reputation.update_one(
        {"_id": user_id},
        {"$inc": {"given": 1}},
        upsert=True,
    )


def set_last(user_id: int, date):
    reputation.update_one(
        {"_id": user_id},
        {"$set": {"last_rep": date}},
        upsert=True,
    )

def top(limit: int = 10):
    return list(
        reputation.find().sort("rep", -1).limit(limit)
    )