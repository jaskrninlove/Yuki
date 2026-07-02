"""
Yuki Bot - AFK System
/afk reason
/back
Auto-reply when AFK users are mentioned or replied to.
"""

import html
import time
from datetime import datetime

from telegram import Update
from telegram.ext import CommandHandler, MessageHandler, ContextTypes, filters

from yuki.core import database as db


def format_duration(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s"

    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m"

    hours = minutes // 60
    if hours < 24:
        return f"{hours}h {minutes % 60}m"

    days = hours // 24
    return f"{days}d {hours % 24}h"


async def set_afk(user_id: int, chat_id: int, reason: str):
    await db._db["afk"].update_one(
        {"user_id": user_id},
        {
            "$set": {
                "user_id": user_id,
                "chat_id": chat_id,
                "reason": reason,
                "since": int(time.time()),
            }
        },
        upsert=True,
    )


async def get_afk(user_id: int):
    return await db._db["afk"].find_one({"user_id": user_id})


async def remove_afk(user_id: int):
    return await db._db["afk"].delete_one({"user_id": user_id})


async def afk_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    if not msg or not user or not chat:
        return

    reason = " ".join(ctx.args).strip() or "AFK"

    await set_afk(user.id, chat.id, reason)

    await msg.reply_text(
        f"<b>{html.escape(user.full_name)}</b> is now AFK.\n\n"
        f"<b>Reason:</b> {html.escape(reason)}",
        parse_mode="HTML",
    )


async def back_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user = update.effective_user

    if not msg or not user:
        return

    data = await get_afk(user.id)

    if not data:
        await msg.reply_text("You are not AFK.")
        return

    since = int(data.get("since", time.time()))
    duration = format_duration(int(time.time()) - since)

    await remove_afk(user.id)

    await msg.reply_text(
        f"Welcome back, <b>{html.escape(user.full_name)}</b>.\n"
        f"You were AFK for <b>{duration}</b>.",
        parse_mode="HTML",
    )


async def afk_watch_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user = update.effective_user

    if not msg or not user:
        return

    # If AFK user sends normal message, remove AFK automatically
    if msg.text and not msg.text.startswith(("/afk", "/back")):
        own_afk = await get_afk(user.id)
        if own_afk:
            since = int(own_afk.get("since", time.time()))
            duration = format_duration(int(time.time()) - since)
            await remove_afk(user.id)

            await msg.reply_text(
                f"Welcome back, <b>{html.escape(user.full_name)}</b>.\n"
                f"You were AFK for <b>{duration}</b>.",
                parse_mode="HTML",
            )
            return

    checked_ids = set()

    # Reply target AFK check
    if msg.reply_to_message and msg.reply_to_message.from_user:
        checked_ids.add(msg.reply_to_message.from_user.id)

    # Mention entity AFK check
    if msg.entities:
        for ent in msg.entities:
            if ent.type == "text_mention" and ent.user:
                checked_ids.add(ent.user.id)

    for uid in checked_ids:
        if uid == user.id:
            continue

        data = await get_afk(uid)
        if not data:
            continue

        since = int(data.get("since", time.time()))
        duration = format_duration(int(time.time()) - since)
        reason = data.get("reason", "AFK")

        await msg.reply_text(
            f"That user is currently AFK.\n\n"
            f"<b>Reason:</b> {html.escape(reason)}\n"
            f"<b>Since:</b> {duration} ago",
            parse_mode="HTML",
        )
        break


afk_handler = CommandHandler("afk", afk_cmd)
back_handler = CommandHandler("back", back_cmd)

afk_watch_h = MessageHandler(
    filters.TEXT & ~filters.COMMAND,
    afk_watch_handler,
)