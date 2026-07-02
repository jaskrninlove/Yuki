"""
Yuki Bot - Inline Whisper System
Usage: @yukichitbot secret message @username
Premium emoji + colored buttons supported.
"""

import re
import uuid
import html
import logging
from datetime import datetime

from telegram import (
    Update,
    InlineQueryResultArticle,
    InputTextMessageContent,
    InlineKeyboardMarkup,
)
from telegram.ext import InlineQueryHandler, CallbackQueryHandler, ContextTypes

from yuki.core import database as db
from yuki.utils.keyboards import pbtn, icon
from yuki.utils import premium

log = logging.getLogger("yuki.plugins.whisper")


async def save_whisper(data: dict):
    await db._db["whispers"].insert_one(data)


async def get_whisper(wid: str):
    return await db._db["whispers"].find_one({"wid": wid})


def parse_whisper(query: str):
    query = query.strip()

    match = re.search(r"@([A-Za-z0-9_]{5,32})\s*$", query)
    if not match:
        return None, None

    target_username = match.group(1).lower()
    text = query[:match.start()].strip()

    if not text:
        return None, None

    return text, target_username


async def whisper_inline(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query
    user = query.from_user
    raw = query.query.strip()

    text, target_username = parse_whisper(raw)

    if not text or not target_username:
        help_text = premium.render(
            ":settings: <b>Whisper format</b>\n\n"
            "<blockquote>"
            "@yukichitbot your secret message @username"
            "</blockquote>\n\n"
            "<i>The recipient must be in the same group.</i>"
        )

        result = InlineQueryResultArticle(
            id="help",
            title="Whisper message",
            description="Format: secret message @username",
            input_message_content=InputTextMessageContent(
                help_text,
                parse_mode="HTML",
                disable_web_page_preview=True,
            ),
        )

        await query.answer([result], cache_time=1, is_personal=True)
        return

    wid = uuid.uuid4().hex[:12]

    await save_whisper({
        "wid": wid,
        "sender_id": user.id,
        "sender_username": (user.username or "").lower(),
        "sender_name": user.full_name,
        "target_username": target_username,
        "text": text,
        "created_at": datetime.utcnow(),
    })

    public_text = premium.render(
        f":settings: <b>Whisper for @{html.escape(target_username)}</b>\n\n"
        "<blockquote>"
        "Only they can read the content."
        "</blockquote>"
    )

    keyboard = InlineKeyboardMarkup([
        [
            pbtn(
                "Read content",
                callback_data=f"whisper:{wid}",
                style="primary",
                icon=icon("search"),
            )
        ]
    ])

    result = InlineQueryResultArticle(
        id=wid,
        title=f"Whisper for @{target_username}",
        description="Only this user can read it",
        input_message_content=InputTextMessageContent(
            public_text,
            parse_mode="HTML",
            disable_web_page_preview=True,
        ),
        reply_markup=keyboard,
    )

    await query.answer([result], cache_time=1, is_personal=True)


async def whisper_read(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = update.effective_user

    if not query or not user:
        return

    wid = query.data.split(":", 1)[1]
    data = await get_whisper(wid)

    if not data:
        await query.answer("Whisper not found.", show_alert=True)
        return

    target_username = str(data.get("target_username", "")).lower().replace("@", "")
    viewer_username = (user.username or "").lower().replace("@", "")

    is_receiver = viewer_username == target_username
    is_sender = user.id == data.get("sender_id")

    if not is_receiver and not is_sender:
        await query.answer(
            f"This whisper is only for @{target_username}.",
            show_alert=True,
        )
        return

    secret = data.get("text", "Empty whisper.")

    await query.answer(
        secret[:190],
        show_alert=True,
    )


whisper_inline_handler = InlineQueryHandler(whisper_inline)
whisper_read_handler = CallbackQueryHandler(
    whisper_read,
    pattern=r"^whisper:[a-f0-9]+$",
)