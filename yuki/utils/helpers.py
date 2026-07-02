"""
Yuki Bot - Helpers & Decorators
Reusable decorators for owner-only, admin-only, maintenance-mode checks.
"""

import logging
import functools
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import ContextTypes

from yuki.core import config
from yuki.core import database as db
from yuki.utils.locale import get

log = logging.getLogger("yuki.helpers")


# ── Access Guards ─────────────────────────────────────────────────────────────

def owner_only(func):
    """Restrict handler to bot owner."""
    @functools.wraps(func)
    async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or user.id != config.OWNER_ID:
            await update.effective_message.reply_text(get("errors.owner_only"), parse_mode="HTML")
            return
        return await func(update, ctx)
    return wrapper


def admin_only(func):
    """Restrict handler to group admins."""
    @functools.wraps(func)
    async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        chat = update.effective_chat
        user = update.effective_user
        if not chat or not user:
            return
        if chat.type == "private":
            return await func(update, ctx)
        member = await ctx.bot.get_chat_member(chat.id, user.id)
        if member.status not in ("administrator", "creator"):
            await update.effective_message.reply_text(get("errors.admin_only"), parse_mode="HTML")
            return
        return await func(update, ctx)
    return wrapper


def maintenance_check(func):
    """Block non-owner users during maintenance."""
    @functools.wraps(func)
    async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if await db.get_maintenance() and (not user or user.id != config.OWNER_ID):
            await update.effective_message.reply_text(get("errors.maintenance"), parse_mode="HTML")
            return
        return await func(update, ctx)
    return wrapper


def group_only(func):
    """Restrict handler to group chats."""
    @functools.wraps(func)
    async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        chat = update.effective_chat
        if not chat or chat.type == "private":
            await update.effective_message.reply_text(get("errors.group_only"), parse_mode="HTML")
            return
        return await func(update, ctx)
    return wrapper


# ── User Upsert ───────────────────────────────────────────────────────────────

async def ensure_user(user) -> None:
    """Save/update user info in DB silently."""
    if not user:
        return
    try:
        await db.upsert_user(user.id, {
            "first_name": user.first_name,
            "last_name":  user.last_name or "",
            "username":   user.username or "",
        })
    except Exception as e:
        log.debug("ensure_user failed: %s", e)


# ── Human Name Format ─────────────────────────────────────────────────────────

def full_name(user) -> str:
    if not user:
        return "Unknown"
    parts = [user.first_name or ""]
    if user.last_name:
        parts.append(user.last_name)
    return " ".join(parts).strip() or "Unknown"


def mention_html(user) -> str:
    return f'<a href="tg://user?id={user.id}">{full_name(user)}</a>'


# ── Uptime ────────────────────────────────────────────────────────────────────

_START_TIME = datetime.utcnow()


def get_uptime() -> str:
    delta = datetime.utcnow() - _START_TIME
    h, rem = divmod(int(delta.total_seconds()), 3600)
    m, s   = divmod(rem, 60)
    d      = delta.days
    if d:
        return f"{d}d {h % 24}h {m}m"
    return f"{h}h {m}m {s}s"


# ── Chunker ───────────────────────────────────────────────────────────────────

def chunk(lst: list, size: int = 3) -> list[list]:
    return [lst[i:i + size] for i in range(0, len(lst), size)]


# ── Anti-flood simple rate limiter ────────────────────────────────────────────

_last_called: dict[int, datetime] = {}


def rate_limit(seconds: int = 3):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
            user = update.effective_user
            if user:
                now  = datetime.utcnow()
                last = _last_called.get(user.id)
                if last and (now - last).total_seconds() < seconds:
                    return
                _last_called[user.id] = now
            return await func(update, ctx)
        return wrapper
    return decorator
