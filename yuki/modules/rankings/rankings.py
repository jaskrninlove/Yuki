"""
Yuki Rankings
Copyright © Jass

Single entrypoint: /rankings, /halloffame
Single callback handler: rk_*
All views edit the same message in place (hub <-> sub-pages via Back).
"""

import html
import logging
from datetime import datetime

from telegram import Update, Bot
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes

from yuki.core import database as db
from yuki.core.config import RANKING_IMAGE
from yuki.utils.helpers import full_name
from yuki.utils.keyboards import rankings_keyboard, rankings_back_keyboard
from yuki.utils import premium

log = logging.getLogger("yuki.plugins.rankings")

MEDALS = [":gold:", ":silver:", ":bronze:"] + [f"{i}." for i in range(4, 11)]

DAILY_MILESTONES = [500, 1000, 5000, 10000]

DAILY_MILESTONE_MSGS = {
    500: (
        ":trophy: <b>500 messages today!!</b>\n\n"
        "<blockquote>this group is actually so alive right now "
        "and I love it :heart:</blockquote>"
    ),
    1000: (
        ":sparkle: <b>1,000 messages today!!</b>\n\n"
        "<blockquote>okay you all are way too chatty "
        "and honestly?? same :flower:</blockquote>"
    ),
    5000: (
        ":crown: <b>5,000 messages today!!</b>\n\n"
        "<blockquote>besties this is actually insane "
        "Yuki is so proud of this group :heart:</blockquote>"
    ),
    10000: (
        ":star: <b>10,000 messages today!!</b>\n\n"
        "<blockquote>no way... this group is literally legendary now "
        "I can't even :sparkle:</blockquote>"
    ),
}

_milestone_cache: dict[str, int] = {}

# Track pinned today-ranking message per chat {chat_id: message_id}
_today_rank_msg: dict[int, int] = {}

HUB_TEXT = """
:trophy: <b>Yuki Hall of Fame</b>

<blockquote>Every message, level, and coin brings you closer to becoming a legend.:crown:</blockquote>

Choose a category below :sparkle:
"""


# ─────────────────────────────────────────────
# Small helpers
# ─────────────────────────────────────────────

def _today_key(chat_id: int) -> str:
    return f"{chat_id}:{datetime.utcnow().strftime('%Y-%m-%d')}"


def _short_name(name: str, limit: int = 18) -> str:
    name = name or "Unknown"
    return name if len(name) <= limit else name[:limit - 1] + "…"


async def _get_name(uid: int, fallback: str = "Unknown") -> str:
    data = await db.get_user(uid)
    if data:
        return data.get("first_name") or data.get("full_name") or fallback
    return fallback


def _group_only_guard(chat) -> bool:
    return bool(chat) and chat.type != "private"


# ─────────────────────────────────────────────
# Builders — each returns rendered HTML text
# ─────────────────────────────────────────────

async def build_today_top(chat_id: int) -> str:
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    pipeline = [
        {"$match": {"chat_id": chat_id, "date": {"$gte": today_start}}},
        {"$group": {"_id": "$user_id", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10},
    ]

    try:
        results = await db.get_db().messages.aggregate(pipeline).to_list(10)
    except Exception:
        results = []

    today_str = datetime.utcnow().strftime("%d %b %Y")

    if not results:
        return (
            f":chart: <b>Today's Top — {today_str}</b>\n\n"
            "<blockquote>No messages today yet.\nStart chatting!!</blockquote>"
        )

    lines = [f":chart: <b>Today's Top — {today_str}</b>", "<blockquote>"]
    for i, row in enumerate(results):
        uid, count = row["_id"], int(row["count"])
        medal = MEDALS[i] if i < len(MEDALS) else f"{i + 1}."
        name = html.escape(_short_name(await _get_name(uid)))
        lines.append(f"{medal} <a href='tg://user?id={uid}'>{name}</a> — <b>{count:,}</b> msgs")
    lines += ["", "</blockquote>", "<i>Updates live every 24h :clock:</i>"]
    return "\n".join(lines)


async def build_group_top(chat_id: int, title: str = ":trophy: <b>Chat Top 10</b>") -> str:
    """All-time message leaderboard for this chat. Reused for both
    'Chat Top' and 'Activity' until a dedicated activity score exists."""
    members = await db.get_active_users(chat_id, limit=10)

    if not members:
        return f"{title}\n<blockquote>No ranking data yet.\nStart chatting first!!</blockquote>"

    lines = [title, "<blockquote>"]
    for i, member in enumerate(members):
        uid = member.get("user_id")
        count = int(member.get("total_messages", 0))
        medal = MEDALS[i] if i < len(MEDALS) else f"{i + 1}."
        name = html.escape(_short_name(await _get_name(uid, member.get("first_name", "Unknown"))))
        lines.append(f"{medal} <a href='tg://user?id={uid}'>{name}</a> — <b>{count:,}</b> msgs")
    lines += ["", "</blockquote>"]
    return "\n".join(lines)


async def build_global_top() -> str:
    users = await db.get_db().users.find(
        {}, {"user_id": 1, "first_name": 1, "full_name": 1, "total_messages": 1},
    ).sort("total_messages", -1).limit(10).to_list(10)

    if not users:
        return ":signal: <b>Global Top 10</b>\n<blockquote>No global data yet!!</blockquote>"

    lines = [":signal: <b>Global Top 10</b>", "<blockquote>"]
    for i, user in enumerate(users):
        uid = user.get("user_id")
        count = int(user.get("total_messages", 0))
        medal = MEDALS[i] if i < len(MEDALS) else f"{i + 1}."
        name = html.escape(_short_name(user.get("first_name") or user.get("full_name") or "Unknown"))
        lines.append(f"{medal} <a href='tg://user?id={uid}'>{name}</a> — <b>{count:,}</b> msgs")
    lines += ["", "</blockquote>"]
    return "\n".join(lines)


async def build_levels() -> str:
    users = await db.get_db().users.find(
        {"xp": {"$gt": 0}}, {"user_id": 1, "first_name": 1, "full_name": 1, "xp": 1},
    ).sort("xp", -1).limit(10).to_list(10)

    if not users:
        return ":star: <b>Top Levels</b>\n<blockquote>No level data yet!!</blockquote>"

    lines = [":star: <b>Top Levels</b>", "<blockquote>"]
    for i, user in enumerate(users):
        uid = user.get("user_id")
        xp = int(user.get("xp", 0))
        level = xp // 100
        medal = MEDALS[i] if i < len(MEDALS) else f"{i + 1}."
        name = html.escape(_short_name(user.get("first_name") or user.get("full_name") or "Unknown"))
        lines.append(f"{medal} <a href='tg://user?id={uid}'>{name}</a> — Lv <b>{level}</b> ({xp:,} xp)")
    lines += ["", "</blockquote>"]
    return "\n".join(lines)


async def build_richest() -> str:
    """Reads 'coins'/'balance' if an economy plugin has set them."""
    users = await db.get_db().users.find(
        {"$or": [{"coins": {"$gt": 0}}, {"balance": {"$gt": 0}}]},
        {"user_id": 1, "first_name": 1, "full_name": 1, "coins": 1, "balance": 1},
    ).sort([("coins", -1), ("balance", -1)]).limit(10).to_list(10)

    if not users:
        return ":gold: <b>Richest Members</b>\n<blockquote>No economy data yet!!</blockquote>"

    lines = [":gold: <b>Richest Members</b>", "<blockquote>"]
    for i, user in enumerate(users):
        uid = user.get("user_id")
        coins = int(user.get("coins") or user.get("balance") or 0)
        medal = MEDALS[i] if i < len(MEDALS) else f"{i + 1}."
        name = html.escape(_short_name(user.get("first_name") or user.get("full_name") or "Unknown"))
        lines.append(f"{medal} <a href='tg://user?id={uid}'>{name}</a> — <b>{coins:,}</b> coins")
    lines += ["", "</blockquote>"]
    return "\n".join(lines)


async def build_reputation() -> str:
    """Reads 'reputation' if a reputation plugin has set it."""
    users = await db.get_db().users.find(
        {"reputation": {"$gt": 0}},
        {"user_id": 1, "first_name": 1, "full_name": 1, "reputation": 1},
    ).sort("reputation", -1).limit(10).to_list(10)

    if not users:
        return ":heart: <b>Most Respected</b>\n<blockquote>No reputation data yet!!</blockquote>"

    lines = [":heart: <b>Most Respected</b>", "<blockquote>"]
    for i, user in enumerate(users):
        uid = user.get("user_id")
        rep = int(user.get("reputation", 0))
        medal = MEDALS[i] if i < len(MEDALS) else f"{i + 1}."
        name = html.escape(_short_name(user.get("first_name") or user.get("full_name") or "Unknown"))
        lines.append(f"{medal} <a href='tg://user?id={uid}'>{name}</a> — <b>{rep:,}</b> rep")
    lines += ["", "</blockquote>"]
    return "\n".join(lines)


async def build_my_rank(chat_id: int, user) -> str:
    members = await db.get_active_users(chat_id, limit=500)
    rank = next((i + 1 for i, m in enumerate(members) if m.get("user_id") == user.id), None)

    data = await db.get_user(user.id) or {}
    total = int(data.get("total_messages", 0))
    xp = int(data.get("xp", 0))
    level = xp // 100
    name = html.escape(full_name(user))

    return (
        f":user: <b>{name}</b>\n\n"
        f"<blockquote>"
        f":trophy: Rank: <b>#{rank or '—'}</b>\n"
        f":chat: Messages: <b>{total:,}</b>\n"
        f":star: Level: <b>{level}</b>\n"
        f":sparkle: XP: <b>{xp:,}</b>\n\n"
        f"</blockquote>"
    )


async def build_stats() -> str:
    dbh = db.get_db()
    try:
        total_users = await dbh.users.count_documents({})
        total_msgs = await dbh.messages.estimated_document_count()
        total_groups = await dbh.chats.count_documents({"type": {"$ne": "private"}}) \
            if "chats" in await dbh.list_collection_names() else 0
    except Exception:
        total_users = total_msgs = total_groups = 0

    return (
        ":chart: <b>Global Statistics</b>\n\n"
        "<blockquote>"
        f":users: Total Users: <b>{total_users:,}</b>\n"
        f":chat: Total Messages: <b>{total_msgs:,}</b>\n"
        f":signal: Total Groups: <b>{total_groups:,}</b>\n"
        "</blockquote>"
    )


# ─────────────────────────────────────────────
# Reply / Edit helpers
# ─────────────────────────────────────────────

async def _reply_ranking(msg, text: str, markup):
    if RANKING_IMAGE:
        try:
            await premium.reply_photo(msg, photo=RANKING_IMAGE, caption=text, reply_markup=markup)
            return
        except Exception as e:
            log.debug("Ranking photo failed: %s", e)
    await premium.reply(msg, text, reply_markup=markup, disable_web_page_preview=True)


async def _edit_ranking(query, text: str, markup):
    try:
        await premium.edit_caption(query, text, reply_markup=markup)
        return
    except Exception:
        pass
    try:
        await premium.edit(query, text, reply_markup=markup, disable_web_page_preview=True)
    except Exception:
        pass


# ─────────────────────────────────────────────
# Today's Ranking — live card, sent/updated by scheduler
# ─────────────────────────────────────────────

async def send_today_ranking(bot: Bot, chat_id: int):
    text = await build_today_top(chat_id)
    markup = rankings_back_keyboard()

    existing_id = _today_rank_msg.get(chat_id)

    if existing_id:
        try:
            if RANKING_IMAGE:
                await bot.edit_message_caption(
                    chat_id=chat_id, message_id=existing_id,
                    caption=premium.render(text), parse_mode="HTML", reply_markup=markup,
                )
            else:
                await bot.edit_message_text(
                    chat_id=chat_id, message_id=existing_id,
                    text=premium.render(text), parse_mode="HTML",
                    reply_markup=markup, disable_web_page_preview=True,
                )
            return
        except Exception:
            _today_rank_msg.pop(chat_id, None)

    try:
        if RANKING_IMAGE:
            sent = await bot.send_photo(
                chat_id=chat_id, photo=RANKING_IMAGE,
                caption=premium.render(text), parse_mode="HTML", reply_markup=markup,
            )
        else:
            sent = await bot.send_message(
                chat_id=chat_id, text=premium.render(text), parse_mode="HTML",
                reply_markup=markup, disable_web_page_preview=True,
            )
        _today_rank_msg[chat_id] = sent.message_id
    except Exception as e:
        log.debug("Today ranking send failed: %s", e)


# ─────────────────────────────────────────────
# Command — single entrypoint
# ─────────────────────────────────────────────

async def rankings_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg:
        return
    await _reply_ranking(msg, HUB_TEXT, rankings_keyboard())


# ─────────────────────────────────────────────
# Callback — single handler for every rk_* button
# ─────────────────────────────────────────────

SECTION_BUILDERS = {
    "rk_rich": lambda chat, user: build_richest(),
    "rk_level": lambda chat, user: build_levels(),
    "rk_rep": lambda chat, user: build_reputation(),
    "rk_stats": lambda chat, user: build_stats(),
    "rk_globaltop": lambda chat, user: build_global_top(),
}

GROUP_ONLY_BUILDERS = {
    "rk_active": lambda chat, user: build_group_top(chat.id, ":chat: <b>Most Active</b>"),
    "rk_top": lambda chat, user: build_group_top(chat.id, ":trophy: <b>Chat Top 10</b>"),
    "rk_rank": lambda chat, user: build_my_rank(chat.id, user),
    "rk_today": lambda chat, user: build_today_top(chat.id),
}


async def rankings_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = update.effective_user
    chat = update.effective_chat
    if not query:
        return
    await query.answer()
    data = query.data

    if data.startswith("rk_home"):
        origin = data.split(":", 1)[1] if ":" in data else None
        ctx.user_data["rk_origin"] = origin  # "profile" or None
        await _edit_ranking(query, HUB_TEXT, rankings_keyboard())
        return

    if data == "rk_back":
        origin = ctx.user_data.pop("rk_origin", None)
        if origin == "profile":
            # hand off to your profile module's edit-in-place renderer here
            pass
        await _edit_ranking(query, HUB_TEXT, rankings_keyboard())
        return
    # ... rest unchanged

# ─────────────────────────────────────────────
# Daily Milestone Check — call from chat handler
# ─────────────────────────────────────────────

async def check_daily_milestones(bot: Bot, chat_id: int, chat_title: str = ""):
    try:
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        count = await db.get_db().messages.count_documents({
            "chat_id": chat_id, "date": {"$gte": today_start},
        })

        key = _today_key(chat_id)
        last = _milestone_cache.get(key, 0)

        for milestone in DAILY_MILESTONES:
            if last < milestone <= count:
                _milestone_cache[key] = milestone
                await premium.send(bot, chat_id, DAILY_MILESTONE_MSGS[milestone], disable_web_page_preview=True)
                break
    except Exception as e:
        log.debug("Milestone check failed: %s", e)


# ─────────────────────────────────────────────
# Handlers
# ─────────────────────────────────────────────

RANKINGS = CommandHandler(["rankings", "halloffame"], rankings_cmd)
RANKINGS_CB = CallbackQueryHandler(
    rankings_callback,
    pattern=r"^rk_(rich|level|rep|active|top|globaltop|rank|today|stats|back|home(:\w+)?)$",
)