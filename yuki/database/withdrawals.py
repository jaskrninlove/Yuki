"""
Yuki Database - Withdrawals
Copyright © Jass
"""

from __future__ import annotations

from datetime import datetime, timezone

from pymongo.collection import Collection

from yuki.core.config import DB

withdrawals: Collection = DB.withdrawals
counters: Collection = DB.counters

REWARD_TIERS = [
    (1000, "₹10 Cash"),
    (5000, "Telegram Username (ID)"),
    (10000, "₹100 Cash"),
    (20000, "Telegram Premium"),
]


def _next_request_id() -> int:
    doc = counters.find_one_and_update(
        {"_id": "withdrawal_request"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True,
    )
    return doc["seq"]


def eligible_tiers(balance: int):
    return [(cost, label) for cost, label in REWARD_TIERS if balance >= cost]


def create_request(user_id: int, tier_cost: int, tier_label: str, contact: str) -> int:
    req_id = _next_request_id()
    withdrawals.insert_one({
        "_id": req_id,
        "user_id": user_id,
        "tier_cost": tier_cost,
        "tier_label": tier_label,
        "contact": contact,
        "status": "pending",
        "created_at": datetime.now(timezone.utc),
        "resolved_at": None,
    })
    return req_id


def get_request(req_id: int):
    return withdrawals.find_one({"_id": req_id})


def set_status(req_id: int, status: str):
    withdrawals.update_one(
        {"_id": req_id},
        {"$set": {"status": status, "resolved_at": datetime.now(timezone.utc)}},
    )


def has_pending_request(user_id: int) -> bool:
    return withdrawals.find_one({"user_id": user_id, "status": "pending"}) is not None


def user_history(user_id: int, limit: int = 10):
    return list(
        withdrawals.find({"user_id": user_id}).sort("created_at", -1).limit(limit)
    )