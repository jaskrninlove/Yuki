"""
Yuki Database - Achievements
Copyright © Jass
"""

from __future__ import annotations

from pymongo.collection import Collection

from yuki.core.config import DB

achievements: Collection = DB.achievements  # _id = user_id, unlocked: [ids]


# ==========================================================
# Registry
# ==========================================================

MESSAGE_MILESTONES = [1000, 2500, 5000, 10000, 25000]
KILL_MILESTONES = [50, 100, 250, 500, 1000]
REFERRAL_MILESTONES = [5, 10, 20, 30, 40, 50]

REGISTRY = {"married": {"label": "Married", "icon": ":ring:"}}

for m in MESSAGE_MILESTONES:
    REGISTRY[f"msg_{m}"] = {"label": f"{m:,} Messages", "icon": ":chat:"}

for k in KILL_MILESTONES:
    REGISTRY[f"kill_{k}"] = {"label": f"{k:,} Kills", "icon": ":crossed_swords:"}

for r in REFERRAL_MILESTONES:
    REGISTRY[f"ref_{r}"] = {"label": f"{r:,} Referrals", "icon": ":link:"}


# ==========================================================
# Core
# ==========================================================

def get_unlocked(user_id: int) -> list[str]:
    doc = achievements.find_one({"_id": user_id})
    return doc.get("unlocked", []) if doc else []


def award(user_id: int, achievement_id: str) -> bool:
    """Returns True if newly awarded (wasn't already unlocked)."""
    if achievement_id not in REGISTRY:
        return False

    result = achievements.update_one(
        {"_id": user_id},
        {"$addToSet": {"unlocked": achievement_id}},
        upsert=True,
    )

    return result.modified_count > 0 or result.upserted_id is not None


def get_unlocked_details(user_id: int) -> list[dict]:
    ids = get_unlocked(user_id)
    return [{"id": i, **REGISTRY[i]} for i in ids if i in REGISTRY]


def count(user_id: int) -> int:
    return len(get_unlocked(user_id))


# ==========================================================
# Milestone checkers
# ==========================================================

def check_message_milestones(user_id: int, total_messages: int) -> list[str]:
    newly = []
    for m in MESSAGE_MILESTONES:
        if total_messages >= m:
            if award(user_id, f"msg_{m}"):
                newly.append(f"msg_{m}")
    return newly


def check_kill_milestones(user_id: int, kills: int) -> list[str]:
    newly = []
    for k in KILL_MILESTONES:
        if kills >= k:
            if award(user_id, f"kill_{k}"):
                newly.append(f"kill_{k}")
    return newly


def check_referral_milestones(user_id: int, referral_count: int) -> list[str]:
    newly = []
    for r in REFERRAL_MILESTONES:
        if referral_count >= r:
            if award(user_id, f"ref_{r}"):
                newly.append(f"ref_{r}")
    return newly


def award_marriage(user_id: int) -> bool:
    return award(user_id, "married")