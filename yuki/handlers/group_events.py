"""
Yuki Bot - Group Add/Remove Logger
Logs when Yuki is added to or removed from groups.
"""

import html
import logging
from datetime import datetime

from telegram import Update
from telegram.ext import ChatMemberHandler, ContextTypes

from yuki.core import database as db
from yuki.core.config import LOG_GROUP_ID
from yuki.utils import premium

log = logging.getLogger("yuki.handlers.group_events")


async def my_chat_member_update(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    event = update.my_chat_member
    if not event:
        return

    chat = event.chat
    old = event.old_chat_member.status
    new = event.new_chat_member.status
    actor = event.from_user

    if chat.type not in ("group", "supergroup"):
        return

    added = old in ("left", "kicked") and new in ("member", "administrator")
    removed = old in ("member", "administrator") and new in ("left", "kicked")

    if not added and not removed:
        return

    try:
        await db.upsert_group(chat.id, {
            "chat_id": chat.id,
            "title": chat.title or "",
            "username": chat.username or "",
            "type": chat.type,
            "active": added,
            "updated_at": datetime.utcnow(),
        })
    except Exception as e:
        log.debug("Group save failed: %s", e)

    if not LOG_GROUP_ID:
        log.warning("LOG_GROUP_ID not set, group event not sent.")
        return

    actor_name = html.escape(actor.full_name if actor else "Unknown")
    actor_id = actor.id if actor else "Unknown"

    if added:
        text = (
            ":success: <b>Yuki Added To Group</b>\n\n"
            "<blockquote>"
            f":chat: <b>Group:</b> {html.escape(chat.title or 'Unknown')}\n"
            f":id: <b>Group ID:</b> <code>{chat.id}</code>\n"
            f":user: <b>Added By:</b> {actor_name}\n"
            f":id: <b>User ID:</b> <code>{actor_id}</code>\n"
            f":clock: <b>Time:</b> <code>{datetime.utcnow().strftime('%d %b %Y, %H:%M UTC')}</code>"
            "</blockquote>"
        )
    else:
        text = (
            ":warning: <b>Yuki Removed From Group</b>\n\n"
            "<blockquote>"
            f":chat: <b>Group:</b> {html.escape(chat.title or 'Unknown')}\n"
            f":id: <b>Group ID:</b> <code>{chat.id}</code>\n"
            f":user: <b>Action By:</b> {actor_name}\n"
            f":id: <b>User ID:</b> <code>{actor_id}</code>\n"
            f":clock: <b>Time:</b> <code>{datetime.utcnow().strftime('%d %b %Y, %H:%M UTC')}</code>"
            "</blockquote>"
        )

    try:
        await premium.send(
            ctx.bot,
            LOG_GROUP_ID,
            text,
            disable_web_page_preview=True,
        )
    except Exception as e:
        log.warning("Failed to send group event log: %s", e)


group_event_handler = ChatMemberHandler(
    my_chat_member_update,
    ChatMemberHandler.MY_CHAT_MEMBER,
)