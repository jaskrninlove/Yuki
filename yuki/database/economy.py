"""
Yuki Database - Economy
Copyright © Jass
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pymongo.collection import Collection

from yuki.core.config import DB


economy: Collection = DB.economy
shield_requests: Collection = DB.shield_requests  # pending permanent-shield payments


# ==========================================================
# Default Economy
# ==========================================================

DEFAULT_BALANCE = 500


def default(user_id: int) -> dict:
    return {
        "_id": user_id,
        "balance": DEFAULT_BALANCE,
        "withdraw_balance": 0,
        "daily_streak": 0,
        "last_daily": None,
        "last_work": None,
        "last_crime": None,
        "last_rob": None,
        "last_kill": None,
        "shield_until": None,
        "permanent_shield": False,
        "kills": 0,
        "total_robbed": 0,
        "pvp_cooldowns": {},
        "dead_until": None,
    }


# ==========================================================
# Account
# ==========================================================

def get(user_id: int) -> dict:
    data = economy.find_one({"_id": user_id})

    if data:
        missing = {}
        for key, val in default(user_id).items():
            if key != "_id" and key not in data:
                missing[key] = val

        if missing:
            economy.update_one({"_id": user_id}, {"$set": missing})
            data.update(missing)

        return data

    data = default(user_id)
    economy.insert_one(data)

    return data


# ==========================================================
# Balance (spendable coins)
# ==========================================================

def balance(user_id: int) -> int:
    return get(user_id)["balance"]


def set_balance(user_id: int, amount: int):
    economy.update_one(
        {"_id": user_id},
        {"$set": {"balance": max(0, amount)}},
    )


def add(user_id: int, amount: int):
    get(user_id)
    economy.update_one(
        {"_id": user_id},
        {"$inc": {"balance": amount}},
    )


def remove(user_id: int, amount: int) -> bool:
    data = get(user_id)

    if data["balance"] < amount:
        return False

    economy.update_one(
        {"_id": user_id},
        {"$inc": {"balance": -amount}},
    )

    return True


# ==========================================================
# Withdraw Balance (real-money eligible)
# ==========================================================

def withdraw_balance(user_id: int) -> int:
    return get(user_id)["withdraw_balance"]


def add_withdraw(user_id: int, amount: int):
    get(user_id)
    economy.update_one(
        {"_id": user_id},
        {"$inc": {"withdraw_balance": amount}},
    )


def remove_withdraw(user_id: int, amount: int) -> bool:
    data = get(user_id)

    if data["withdraw_balance"] < amount:
        return False

    economy.update_one(
        {"_id": user_id},
        {"$inc": {"withdraw_balance": -amount}},
    )

    return True


# ==========================================================
# Transfer
# ==========================================================

def transfer(sender: int, receiver: int, amount: int) -> bool:
    if amount <= 0:
        return False

    if not remove(sender, amount):
        return False

    add(receiver, amount)

    return True


# ==========================================================
# Cooldowns (generic, single-key — used by /daily etc.)
# ==========================================================

def set_cooldown(user_id: int, key: str, value):
    get(user_id)
    economy.update_one(
        {"_id": user_id},
        {"$set": {key: value}},
    )


def cooldown(user_id: int, key: str):
    return get(user_id).get(key)


def seconds_remaining(user_id: int, key: str, duration_seconds: int) -> Optional[int]:
    """Returns remaining cooldown seconds, or None if ready to use."""
    last = get(user_id).get(key)

    if not last:
        return None

    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)

    elapsed = (datetime.now(timezone.utc) - last).total_seconds()
    remaining = duration_seconds - elapsed

    return int(remaining) if remaining > 0 else None


# ==========================================================
# PvP Cooldowns (per attacker+target pair — used by /kill, /rob)
# ==========================================================

def set_pair_cooldown(action: str, attacker_id: int, target_id: int, date):
    """Cooldown scoped to a specific (action, attacker, target) triple,
    so hitting cooldown on one target never blocks acting on another."""
    get(attacker_id)
    key = f"{action}:{target_id}"
    economy.update_one(
        {"_id": attacker_id},
        {"$set": {f"pvp_cooldowns.{key}": date}},
    )


def pair_seconds_remaining(action: str, attacker_id: int, target_id: int, duration_seconds: int) -> Optional[int]:
    data = get(attacker_id)
    cooldowns = data.get("pvp_cooldowns") or {}
    key = f"{action}:{target_id}"
    last = cooldowns.get(key)

    if not last:
        return None

    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)

    elapsed = (datetime.now(timezone.utc) - last).total_seconds()
    remaining = duration_seconds - elapsed

    return int(remaining) if remaining > 0 else None


# ==========================================================
# Shield (covers BOTH /kill and /rob — same flag, single source of truth)
# ==========================================================

def set_shield(user_id: int, until):
    """Setting a new temporary shield always overwrites any previous one
    — the timer resets, it never stacks."""
    get(user_id)
    economy.update_one(
        {"_id": user_id},
        {"$set": {"shield_until": until}},
    )


def has_shield(user_id: int) -> bool:
    data = get(user_id)

    if data.get("permanent_shield"):
        return True

    until = data.get("shield_until")

    if not until:
        return False

    if until.tzinfo is None:
        until = until.replace(tzinfo=timezone.utc)

    return until > datetime.now(timezone.utc)


def shield_remaining(user_id: int) -> Optional[int]:
    until = get(user_id).get("shield_until")

    if not until:
        return None

    if until.tzinfo is None:
        until = until.replace(tzinfo=timezone.utc)

    remaining = (until - datetime.now(timezone.utc)).total_seconds()
    return int(remaining) if remaining > 0 else None


# ==========================================================
# Permanent Shield
# ==========================================================

def set_permanent_shield(user_id: int, value: bool = True):
    """Activating a permanent shield also clears any leftover temporary
    shield_until — permanent supersedes it entirely."""
    get(user_id)
    economy.update_one(
        {"_id": user_id},
        {"$set": {"permanent_shield": value, "shield_until": None}},
    )


def has_permanent_shield(user_id: int) -> bool:
    return get(user_id).get("permanent_shield", False)


# ==========================================================
# Permanent Shield — pending REAL-MONEY (UPI) payment requests
# ==========================================================

def set_pending_shield_payment(user_id: int, name: str, username: Optional[str]):
    shield_requests.update_one(
        {"_id": user_id},
        {"$set": {"name": name, "username": username, "requested_at": datetime.now(timezone.utc)}},
        upsert=True,
    )


def get_pending_shield_payment(user_id: int):
    return shield_requests.find_one({"_id": user_id})


def clear_pending_shield_payment(user_id: int):
    shield_requests.delete_one({"_id": user_id})


# ==========================================================
# Kills / Robbery Stats
# ==========================================================

def add_kill(user_id: int):
    get(user_id)
    economy.update_one(
        {"_id": user_id},
        {"$inc": {"kills": 1}},
    )


def get_kills(user_id: int) -> int:
    return get(user_id).get("kills", 0)


def add_total_robbed(user_id: int, amount: int):
    get(user_id)
    economy.update_one(
        {"_id": user_id},
        {"$inc": {"total_robbed": amount}},
    )


def get_total_robbed(user_id: int) -> int:
    return get(user_id).get("total_robbed", 0)

# ==========================================================
# Death Protection (after being killed)
# ==========================================================

def set_dead(user_id: int, until):
    get(user_id)
    economy.update_one(
        {"_id": user_id},
        {"$set": {"dead_until": until}},
    )


def is_dead(user_id: int) -> bool:
    until = get(user_id).get("dead_until")

    if not until:
        return False

    if until.tzinfo is None:
        until = until.replace(tzinfo=timezone.utc)

    return until > datetime.now(timezone.utc)


def dead_remaining(user_id: int):
    until = get(user_id).get("dead_until")

    if not until:
        return None

    if until.tzinfo is None:
        until = until.replace(tzinfo=timezone.utc)

    remaining = (until - datetime.now(timezone.utc)).total_seconds()
    return int(remaining) if remaining > 0 else None

# ==========================================================
# Daily
# ==========================================================

def set_daily(user_id: int, streak: int, date):
    get(user_id)
    economy.update_one(
        {"_id": user_id},
        {"$set": {"daily_streak": streak, "last_daily": date}},
    )


def streak(user_id: int) -> int:
    return get(user_id)["daily_streak"]


# ==========================================================
# Leaderboard
# ==========================================================

def richest(limit: int = 10):
    return list(economy.find().sort("balance", -1).limit(limit))


def total_wealth() -> int:
    agg = list(
        economy.aggregate([
            {"$group": {"_id": None, "total": {"$sum": "$balance"}}}
        ])
    )
    return agg[0]["total"] if agg else 0
