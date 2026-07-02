"""
Yuki Bot - Premium Emoji Debug

Owner only.

Commands:
    /emojiid  (reply to any message containing Premium emoji)

Returns:
- custom_emoji_id
- emoji character
- offset
- length

Useful for building premium themed bots.
"""

import html

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from yuki.core.config import OWNER_ID


async def emojiid_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user = update.effective_user

    if not msg or not user:
        return

    if user.id != OWNER_ID:
        return

    target = msg.reply_to_message

    if not target:
        await msg.reply_text(
            "<b>Reply to a message containing Premium emoji.</b>",
            parse_mode="HTML",
        )
        return

    entities = []

    if target.entities:
        entities.extend(target.entities)

    if target.caption_entities:
        entities.extend(target.caption_entities)

    custom = [e for e in entities if e.type == "custom_emoji"]

    if not custom:
        await msg.reply_text(
            "<b>No Premium emoji found.</b>",
            parse_mode="HTML",
        )
        return

    source = target.text or target.caption or ""

    lines = [
        "🌸 <b>Premium Emoji Inspector</b>",
        "",
    ]

    for i, e in enumerate(custom, start=1):
        emoji = source[e.offset:e.offset + e.length]

        lines.append(
            f"<blockquote>"
            f"<b>Emoji #{i}</b>\n"
            f"Emoji : {html.escape(emoji)}\n"
            f"ID : <code>{e.custom_emoji_id}</code>\n"
            f"Offset : {e.offset}\n"
            f"Length : {e.length}"
            f"</blockquote>"
        )

    await msg.reply_text(
        "\n".join(lines),
        parse_mode="HTML",
    )


emojiid_handler = CommandHandler("emojiid", emojiid_cmd)