"""
Yuki Database - Word Game
Copyright © Jass
"""

from __future__ import annotations

from datetime import datetime, timezone

from pymongo.collection import Collection

from yuki.core.config import DB

word_game_stats: Collection = DB.word_game_stats   # _id = user_id
word_game_active: Collection = DB.word_game_active  # _id = chat_id


# ==========================================================
# Active Puzzle (per chat)
# ==========================================================

def set_active_puzzle(chat_id: int, word: str, scrambled: str, message_id: int, reward: int):
    word_game_active.update_one(
        {"_id": chat_id},
        {"$set": {
            "word": word,
            "scrambled": scrambled,
            "message_id": message_id,
            "reward": reward,
            "sent_at": datetime.now(timezone.utc),
        }},
        upsert=True,
    )


def get_active_puzzle(chat_id: int):
    return word_game_active.find_one({"_id": chat_id})


def clear_active_puzzle(chat_id: int):
    word_game_active.delete_one({"_id": chat_id})


def all_active_chat_ids() -> list[int]:
    return [d["_id"] for d in word_game_active.find({}, {"_id": 1})]


# ==========================================================
# Stats (per user)
# ==========================================================

def _get_stats(user_id: int) -> dict:
    doc = word_game_stats.find_one({"_id": user_id})
    if doc:
        return doc
    return {"_id": user_id, "attempts": 0, "solved": 0, "coins_earned": 0}


def record_attempt(user_id: int):
    word_game_stats.update_one(
        {"_id": user_id},
        {"$inc": {"attempts": 1}},
        upsert=True,
    )


def record_solve(user_id: int, reward: int):
    word_game_stats.update_one(
        {"_id": user_id},
        {"$inc": {"attempts": 1, "solved": 1, "coins_earned": reward}},
        upsert=True,
    )


def get_stats(user_id: int) -> dict:
    return _get_stats(user_id)