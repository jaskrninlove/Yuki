"""
Yuki Bot - Safe Sticker Library

Bot does NOT save random group stickers automatically.
Admin can manually add safe stickers using:
/addsticker  — reply to sticker
/stickers    — count saved stickers
/clearstickers — owner only

Auto-reply logic lives in yuki/handlers/chat.py — this file only
manages the sticker pool and exposes helpers to fetch from it.
"""

import random
import logging

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from yuki.core import database as db
from yuki.core.config import OWNER_ID
from yuki.utils.helpers import admin_only

log = logging.getLogger("yuki.plugins.stickers")


async def _stickers_col():
    return db.get_db()["safe_stickers"]


async def save_safe_sticker(file_id: str, emoji: str = "", set_name: str = ""):
    col = await _stickers_col()
    await col.update_one(
        {"file_id": file_id},
        {
            "$set": {
                "file_id": file_id,
                "emoji": emoji,
                "set_name": set_name,
            }
        },
        upsert=True,
    )


async def get_random_sticker() -> str | None:
    col = await _stickers_col()
    count = await col.count_documents({})

    if count <= 0:
        return None

    skip = random.randint(0, count - 1)
    doc = await col.find_one({}, skip=skip)

    return doc.get("file_id") if doc else None


@admin_only
async def addsticker_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message

    if not msg or not msg.reply_to_message or not msg.reply_to_message.sticker:
        await msg.reply_text("Reply to a sticker with /addsticker")
        return

    sticker = msg.reply_to_message.sticker

    await save_safe_sticker(
        sticker.file_id,
        emoji=sticker.emoji or "",
        set_name=sticker.set_name or "",
    )

    await msg.reply_text(
        "Sticker added to Yuki safe sticker pool.\n\n"
        f"Emoji: {sticker.emoji or 'None'}\n"
        f"Pack: {sticker.set_name or 'None'}"
    )


async def stickers_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    col = await _stickers_col()
    count = await col.count_documents({})

    await update.effective_message.reply_text(
        f"Yuki has {count} safe stickers saved."
    )


async def clearstickers_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not user or user.id != OWNER_ID:
        await update.effective_message.reply_text("Owner only.")
        return

    col = await _stickers_col()
    await col.delete_many({})

    await update.effective_message.reply_text("All safe stickers cleared.")


addsticker_handler = CommandHandler("addsticker", addsticker_cmd)
stickers_count_handler = CommandHandler("stickers", stickers_cmd)
clearstickers_handler = CommandHandler("clearstickers", clearstickers_cmd)
