"""
Yuki Database - Coupons
Copyright © Jass

Owner-created redeem codes — reward goes straight into the spendable
'balance' field (NOT withdraw_balance).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pymongo.collection import Collection

from yuki.core.config import DB
from yuki.database.economy import add  # adds to 'balance' specifically

coupons: Collection = DB.coupons


def create_coupon(code: str, amount: int, max_uses: int, expires_at, created_by: int):
    coupons.update_one(
        {"_id": code},
        {
            "$set": {
                "amount": amount,
                "max_uses": max_uses,
                "used_count": 0,
                "expires_at": expires_at,
                "created_by": created_by,
                "redeemed_by": [],
            }
        },
        upsert=True,
    )


def redeem_coupon(code: str, user_id: int) -> tuple[bool, str, Optional[int]]:
    """Returns (success, reason, amount). reason in:
    'not_found' | 'expired' | 'maxed_out' | 'already_used' | 'ok'"""
    now = datetime.now(timezone.utc)

    doc = coupons.find_one({"_id": code})
    if not doc:
        return False, "not_found", None

    expires_at = doc.get("expires_at")
    if expires_at:
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < now:
            return False, "expired", None

    if user_id in doc.get("redeemed_by", []):
        return False, "already_used", None

    if doc.get("used_count", 0) >= doc.get("max_uses", 0):
        return False, "maxed_out", None

    # Atomic claim — the $expr guard prevents a race condition from
    # letting more than max_uses people claim the last slot at once.
    result = coupons.update_one(
        {
            "_id": code,
            "redeemed_by": {"$ne": user_id},
            "$expr": {"$lt": ["$used_count", "$max_uses"]},
        },
        {"$inc": {"used_count": 1}, "$push": {"redeemed_by": user_id}},
    )
    if result.modified_count == 0:
        return False, "maxed_out", None  # lost the race — slot just got taken

    add(user_id, doc["amount"])  # goes into 'balance' field, not withdraw_balance
    return True, "ok", doc["amount"]
