"""
Yuki Bot - Ranking System
/top  — Group Top 10
/rank — My Rank
Today's ranking card — auto-updates every 24h per group
Daily milestone alerts: 500, 1000, 5000, 10000
Premium emoji supported.
"""

import html
import logging
from datetime import datetime

from telegram import Update, Bot
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes

from yuki.core import database as db
from yuki.core.config import RANKING_IMAGE
from yuki.utils.helpers import full_name
from yuki.utils.keyboards import rank_keyboard
from yuki.utils import premium

log = logging.getLogger("yuki.plugins.ranking")

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


# ─────────────────────────────────────────────
# Today's Ranking — live, per group
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

    lines = [
        f":chart: <b>Today's Top — {today_str}</b>",
        "<blockquote>",
    ]

    for i, row in enumerate(results):
        uid   = row["_id"]
        count = int(row["count"])
        medal = MEDALS[i] if i < len(MEDALS) else f"{i + 1}."
        name  = html.escape(_short_name(await _get_name(uid)))
        lines.append(f"{medal} <a href='tg://user?id={uid}'>{name}</a> — <b>{count:,}</b> msgs")

    lines.append("")
    lines.append("</blockquote>")
    lines.append(f"<i>Updates live every 24h :clock:</i>")

    return "\n".join(lines)


# ─────────────────────────────────────────────
# Group Top 10 (all time)
# ─────────────────────────────────────────────

async def build_group_top(chat_id: int) -> str:
    members = await db.get_active_users(chat_id, limit=10)

    if not members:
        return (
            ":trophy: <b>Top 10</b>\n"
            "<blockquote>No ranking data yet.\nStart chatting first!!</blockquote>"
        )

    lines = [":trophy: <b>Top 10</b>", "<blockquote>"]

    for i, member in enumerate(members):
        uid   = member.get("user_id")
        count = int(member.get("total_messages", 0))
        medal = MEDALS[i] if i < len(MEDALS) else f"{i + 1}."
        name  = html.escape(_short_name(await _get_name(uid, member.get("first_name", "Unknown"))))
        lines.append(f"{medal} <a href='tg://user?id={uid}'>{name}</a> — <b>{count:,}</b> msgs")

    lines.append("")
    lines.append("</blockquote>")
    return "\n".join(lines)


# ─────────────────────────────────────────────
# Global Top 10
# ─────────────────────────────────────────────

async def build_global_top() -> str:
    users = await db.get_db().users.find(
        {},
        {"user_id": 1, "first_name": 1, "full_name": 1, "total_messages": 1},
    ).sort("total_messages", -1).limit(10).to_list(10)

    if not users:
        return (
            ":signal: <b>Global Top 10</b>\n"
            "<blockquote>No global data yet!!</blockquote>"
        )

    lines = [":signal: <b>Global Top 10</b>", "<blockquote>"]

    for i, user in enumerate(users):
        uid   = user.get("user_id")
        count = int(user.get("total_messages", 0))
        medal = MEDALS[i] if i < len(MEDALS) else f"{i + 1}."
        name  = html.escape(_short_name(user.get("first_name") or user.get("full_name") or "Unknown"))
        lines.append(f"{medal} <a href='tg://user?id={uid}'>{name}</a> — <b>{count:,}</b> msgs")

    lines.append("")
    lines.append("</blockquote>")
    return "\n".join(lines)


# ─────────────────────────────────────────────
# My Rank
# ─────────────────────────────────────────────

async def build_my_rank(chat_id: int, user) -> str:
    members = await db.get_active_users(chat_id, limit=500)
    rank    = next((i + 1 for i, m in enumerate(members) if m.get("user_id") == user.id), None)

    data  = await db.get_user(user.id) or {}
    total = int(data.get("total_messages", 0))
    xp    = int(data.get("xp", 0))
    level = int(xp // 100)
    name  = html.escape(full_name(user))

    return (
        f":user: <b>{name}</b>\n\n"
        f"<blockquote>"
        f":trophy: Rank: <b>#{rank or '—'}</b>\n"
        f":chat: Messages: <b>{total:,}</b>\n"
        f":star: Level: <b>{level}</b>\n"
        f":sparkle: XP: <b>{xp:,}</b>\n\n"
        f"</blockquote>"
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
# Today's Ranking — send/update in group
# ─────────────────────────────────────────────

async def send_today_ranking(bot: Bot, chat_id: int):
    """
    Send today's ranking card to the group.
    If one was already sent today, edit it in place.
    Otherwise send a new one and store the message_id.
    """
    text   = await build_today_top(chat_id)
    markup = rank_keyboard("today")

    existing_id = _today_rank_msg.get(chat_id)

    if existing_id:
        try:
            if RANKING_IMAGE:
                await bot.edit_message_caption(
                    chat_id=chat_id,
                    message_id=existing_id,
                    caption=premium.render(text),
                    parse_mode="HTML",
                    reply_markup=markup,
                )
            else:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=existing_id,
                    text=premium.render(text),
                    parse_mode="HTML",
                    reply_markup=markup,
                    disable_web_page_preview=True,
                )
            return
        except Exception:
            # Message gone — send fresh
            _today_rank_msg.pop(chat_id, None)

    try:
        if RANKING_IMAGE:
            sent = await bot.send_photo(
                chat_id=chat_id,
                photo=RANKING_IMAGE,
                caption=premium.render(text),
                parse_mode="HTML",
                reply_markup=markup,
            )
        else:
            sent = await bot.send_message(
                chat_id=chat_id,
                text=premium.render(text),
                parse_mode="HTML",
                reply_markup=markup,
                disable_web_page_preview=True,
            )
        _today_rank_msg[chat_id] = sent.message_id
    except Exception as e:
        log.debug("Today ranking send failed: %s", e)


# ─────────────────────────────────────────────
# Commands
# ─────────────────────────────────────────────

async def top_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    msg  = update.effective_message

    if not chat or not msg:
        return

    if chat.type == "private":
        await premium.reply(msg, ":users: Use /top in a group.")
        return

    text = await build_group_top(chat.id)
    await _reply_ranking(msg, text, rank_keyboard("top"))


async def rank_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    msg  = update.effective_message

    if not chat or not user or not msg:
        return

    if chat.type == "private":
        await premium.reply(msg, ":users: Use /rank in a group.")
        return

    text = await build_my_rank(chat.id, user)
    await _reply_ranking(msg, text, rank_keyboard("rank"))


async def today_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Show today's ranking card manually."""
    chat = update.effective_chat
    msg  = update.effective_message

    if not chat or not msg:
        return

    if chat.type == "private":
        await premium.reply(msg, ":users: Use /today in a group.")
        return

    text = await build_today_top(chat.id)
    await _reply_ranking(msg, text, rank_keyboard("today"))


# ─────────────────────────────────────────────
# Callbacks
# ─────────────────────────────────────────────

async def rank_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user  = update.effective_user
    chat  = update.effective_chat

    if not query:
        return

    await query.answer()
    data = query.data

    if data == "rank_top":
        if not chat or chat.type == "private":
            await query.answer("Use this in a group.", show_alert=True)
            return
        text   = await build_group_top(chat.id)
        markup = rank_keyboard("top")

    elif data == "rank_me":
        if not chat or chat.type == "private":
            await query.answer("Use this in a group.", show_alert=True)
            return
        text   = await build_my_rank(chat.id, user)
        markup = rank_keyboard("rank")

    elif data == "rank_global":
        text   = await build_global_top()
        markup = rank_keyboard("top")

    elif data == "rank_today":
        if not chat or chat.type == "private":
            await query.answer("Use this in a group.", show_alert=True)
            return
        text   = await build_today_top(chat.id)
        markup = rank_keyboard("today")

    else:
        return

    await _edit_ranking(query, text, markup)


# ─────────────────────────────────────────────
# Daily Milestone Check — call from chat handler
# ─────────────────────────────────────────────

async def check_daily_milestones(bot: Bot, chat_id: int, chat_title: str = ""):
    try:
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        count = await db.get_db().messages.count_documents({
            "chat_id": chat_id,
            "date":    {"$gte": today_start},
        })

        key  = _today_key(chat_id)
        last = _milestone_cache.get(key, 0)

        for milestone in DAILY_MILESTONES:
            if last < milestone <= count:
                _milestone_cache[key] = milestone

                await premium.send(
                    bot,
                    chat_id,
                    DAILY_MILESTONE_MSGS[milestone],
                    disable_web_page_preview=True,
                )
                break

    except Exception as e:
        log.debug("Milestone check failed: %s", e)


# ─────────────────────────────────────────────
# Handlers
# ─────────────────────────────────────────────

top_cmd_h   = CommandHandler("top",   top_cmd)
rank_cmd_h  = CommandHandler("rank",  rank_cmd)
today_cmd_h = CommandHandler("today", today_cmd)
rank_cb_h   = CallbackQueryHandler(rank_callback, pattern=r"^rank_(top|me|global|today)$")