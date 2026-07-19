"""
Yuki Database - Word Grid Stats
Copyright © Jass
"""

from __future__ import annotations

from datetime import datetime, timezone

from pymongo.collection import Collection

from yuki.core.config import DB

wordgrid_log: Collection = DB.wordgrid_log  # one doc per solved word


def log_points(user_id: int, chat_id: int, name: str, points: int):
    wordgrid_log.insert_one({
        "user_id": user_id,
        "chat_id": chat_id,
        "name": name,
        "points": points,
        "date": datetime.now(timezone.utc),
    })


def _aggregate(match: dict, limit: int = 10):
    pipeline = [
        {"$match": match},
        {"$group": {
            "_id": "$user_id",
            "points": {"$sum": "$points"},
            "name": {"$last": "$name"},
        }},
        {"$sort": {"points": -1}},
        {"$limit": limit},
    ]
    return list(wordgrid_log.aggregate(pipeline))


def group_ranking(chat_id: int, limit: int = 10):
    return _aggregate({"chat_id": chat_id}, limit)


def global_ranking(limit: int = 10):
    return _aggregate({}, limit)


def today_ranking(chat_id: int, limit: int = 10):
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    return _aggregate({"chat_id": chat_id, "date": {"$gte": today_start}}, limit)


def my_points(user_id: int) -> dict:
    group_total = list(wordgrid_log.aggregate([
        {"$match": {"user_id": user_id}},
        {"$group": {"_id": None, "total": {"$sum": "$points"}}},
    ]))
    total = group_total[0]["total"] if group_total else 0

    words_found = wordgrid_log.count_documents({"user_id": user_id})

    return {"total_points": total, "words_found": words_found}