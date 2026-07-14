"""
Yuki Rankings Helpers
Copyright © Jass
"""
from yuki.core import database as core_db
from yuki.database.reputation import reputation as rep_collection
from yuki.core.database import (
    highest_level,
    most_active,
    global_stats,
    get_by_id,
)
from yuki.database.reputation import top as rep_top
from yuki.database.economy import total_wealth, richest as economy_richest


def _medal(i: int) -> str:
    if i == 1:
        return "🥇"
    if i == 2:
        return "🥈"
    if i == 3:
        return "🥉"
    return f"{i}."


# ==========================================================
# Richest
# ==========================================================

async def richest_text() -> str:
    entries = economy_richest()

    lines = []
    rank = 1

    for entry in entries:
        uid = entry.get("_id")
        if uid is None:
            continue

        user = await get_by_id(uid)
        name = user.get("name") if user else None
        if not name:
            continue

        lines.append(
            f"{_medal(rank)} <b>{name}</b> — ${entry.get('balance', 0):,}"
        )
        rank += 1

    body = "\n".join(lines) if lines else "No data available."

    return f"""
:gold: <b>Richest Members</b>

<blockquote>Fortune favors those who stay active.</blockquote>

<blockquote>{body}</blockquote>
"""


# ==========================================================
# Levels
# ==========================================================

async def levels_text() -> str:
    users = await highest_level()

    lines = []
    rank = 1

    for user in users:
        if not user.get("name"):
            continue

        lines.append(
            f"{_medal(rank)} <b>{user['name']}</b> — Level {user.get('level', 1)} · {user.get('xp', 0):,} XP"
        )
        rank += 1

    body = "\n".join(lines) if lines else "No data available."

    return f"""
:star: <b>Highest Levels</b>

<blockquote>Experience is earned one message at a time.</blockquote>

<blockquote>{body}</blockquote>
"""


# ==========================================================
# Reputation
# ==========================================================

async def reputation_text() -> str:
    entries = rep_top()

    lines = []
    rank = 1

    for entry in entries:
        uid = (
            entry.get("_id")
            or entry.get("user_id")
            or entry.get("id")
        )

        user = await get_by_id(uid)

        if not user:
            continue

        name = user.get("name")

        if not name:
            continue

        lines.append(
            f"{_medal(rank)} <b>{name}</b> — {entry.get('rep', 0)} Rep"
        )
        rank += 1

    body = "\n".join(lines) if lines else "No data available."

    return f"""
:heart: <b>Most Respected Members</b>

<blockquote>Respect is worth more than gold.</blockquote>

<blockquote>{body}</blockquote>
"""


# ==========================================================
# Activity
# ==========================================================

async def activity_text() -> str:
    users = await most_active()

    lines = []
    rank = 1

    for user in users:
        if not user.get("name"):
            continue

        lines.append(
            f"{_medal(rank)} <b>{user['name']}</b> — {user.get('total_messages', 0):,} messages"
        )
        rank += 1

    body = "\n".join(lines) if lines else "No data available."

    return f"""
:chat: <b>Most Active Members</b>

<blockquote>Every message leaves a footprint.</blockquote>

<blockquote>{body}</blockquote>
"""


# ==========================================================
# Statistics
# ==========================================================

async def stats_text() -> str:
    stats = await global_stats()

    total_money = total_wealth()
    total_rep = sum(d.get("rep", 0) for d in rep_collection.find({}, {"rep": 1}))

    return f"""
:chart: <b>Global Statistics</b>

<blockquote>A quick look at Yuki's growing universe.</blockquote>

:users: <b>Total Users</b> <code>{stats['users']:,}</code>
:chat: <b>Total Messages</b> <code>{stats['messages']:,}</code>
:gold: <b>Total Wealth</b> <code>${total_money:,}</code>
:star: <b>Total Levels</b> <code>{stats['levels']:,}</code>
:heart: <b>Total Reputation</b> <code>{total_rep:,}</code>
:ring: <b>Married Users</b> <code>{stats['married']:,}</code>
"""

# ==========================================================
# Love
# ==========================================================

async def love_text() -> str:
    from yuki.database.marriage import top_love

    entries = top_love()

    lines = []
    rank = 1

    for entry in entries:
        u1 = await get_by_id(entry.get("user1"))
        u2 = await get_by_id(entry.get("user2"))

        name1 = u1.get("name") if u1 else "Unknown"
        name2 = u2.get("name") if u2 else "Unknown"

        lines.append(
            f"{_medal(rank)} <b>{name1}</b> :heart: <b>{name2}</b> — {entry.get('love_points', 0):,} pts"
        )
        rank += 1

    body = "\n".join(lines) if lines else "No couples yet~"

    return f"""
:heart: <b>Top Couples</b>

<blockquote>Love conquers all~</blockquote>

<blockquote>{body}</blockquote>
"""


# ==========================================================
# Referrals
# ==========================================================

async def referral_text() -> str:
    from yuki.database.referral import top_referrers

    entries = top_referrers()

    lines = []
    rank = 1

    for entry in entries:
        uid = entry.get("_id")
        user = await get_by_id(uid)
        name = user.get("name") if user else None

        if not name:
            continue

        lines.append(
            f"{_medal(rank)} <b>{name}</b> — {entry.get('count', 0):,} referrals"
        )
        rank += 1

    body = "\n".join(lines) if lines else "No referrals yet~"

    return f"""
:refer: <b>Top Referrers</b>

<blockquote>Sharing is caring~</blockquote>

<blockquote>{body}</blockquote>
"""