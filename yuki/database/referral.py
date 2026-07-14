"""
Yuki Database - Referral
Copyright © Jass
"""

from __future__ import annotations

from datetime import datetime, timezone

from pymongo.collection import Collection

from yuki.core.config import DB

referrals: Collection = DB.referrals       # _id = referred_user_id (unique, one-time)
referrer_stats: Collection = DB.referrer_stats  # _id = referrer_id, count of successful refers

MAX_REFERRALS = 50

MILESTONES = [
    (5, 2),
    (10, 5),
    (20, 12),
    (30, 18),
    (40, 25),
    (50, 35),
]


def has_been_referred(user_id: int) -> bool:
    return referrals.find_one({"_id": user_id}) is not None


def record_referral(referrer_id: int, referred_id: int) -> bool:
    """Returns True if this referral was newly recorded (i.e. counted)."""
    if referrer_id == referred_id:
        return False

    if has_been_referred(referred_id):
        return False

    stats = referrer_stats.find_one({"_id": referrer_id})
    current_count = stats.get("count", 0) if stats else 0

    if current_count >= MAX_REFERRALS:
        return False

    try:
        referrals.insert_one({
            "_id": referred_id,
            "referrer_id": referrer_id,
            "date": datetime.now(timezone.utc),
        })
    except Exception:
        return False

    referrer_stats.update_one(
        {"_id": referrer_id},
        {"$inc": {"count": 1}},
        upsert=True,
    )

    return True


def get_referral_count(user_id: int) -> int:
    stats = referrer_stats.find_one({"_id": user_id})
    return stats.get("count", 0) if stats else 0


def milestone_reward(old_count: int, new_count: int) -> int:
    """Sum of all milestone rewards crossed between old_count and new_count."""
    total = 0
    for threshold, reward in MILESTONES:
        if old_count < threshold <= new_count:
            total += reward
    return total


def next_milestone(count: int):
    for threshold, reward in MILESTONES:
        if count < threshold:
            return threshold, reward
    return None, None


def top_referrers(limit: int = 10):
    return list(referrer_stats.find().sort("count", -1).limit(limit))