"""
Yuki Bot - Notes System
/savenote name text
/getnote name
/notes
/delnote name
"""

import html
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from yuki.core import database as db
from yuki.utils.helpers import admin_only


async def save_note(chat_id: int, name: str, text: str):
    await db._db["notes"].update_one(
        {"chat_id": chat_id, "name": name.lower()},
        {"$set": {"chat_id": chat_id, "name": name.lower(), "text": text}},
        upsert=True,
    )


async def get_note(chat_id: int, name: str):
    return await db._db["notes"].find_one({"chat_id": chat_id, "name": name.lower()})


@admin_only
async def savenote_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat = update.effective_chat

    if len(ctx.args) < 2 and not msg.reply_to_message:
        await msg.reply_text("Usage: /savenote name text\nOr reply to a message: /savenote name")
        return

    name = ctx.args[0].lower()

    if msg.reply_to_message:
        text = msg.reply_to_message.text or msg.reply_to_message.caption or ""
    else:
        text = " ".join(ctx.args[1:])

    if not text:
        await msg.reply_text("Note text cannot be empty.")
        return

    await save_note(chat.id, name, text)
    await msg.reply_text(f"Saved note: <code>{html.escape(name)}</code>", parse_mode="HTML")


async def getnote_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat = update.effective_chat

    if not ctx.args:
        await msg.reply_text("Usage: /getnote name")
        return

    name = ctx.args[0].lower()
    note = await get_note(chat.id, name)

    if not note:
        await msg.reply_text("Note not found.")
        return

    await msg.reply_text(
        note["text"],
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


async def notes_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat = update.effective_chat

    cursor = db._db["notes"].find({"chat_id": chat.id})
    notes = [n async for n in cursor]

    if not notes:
        await msg.reply_text("No notes saved in this chat.")
        return

    text = "<b>Saved Notes</b>\n\n" + "\n".join(
        f"• <code>{html.escape(n['name'])}</code>" for n in notes
    )

    await msg.reply_text(text, parse_mode="HTML")


@admin_only
async def delnote_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat = update.effective_chat

    if not ctx.args:
        await msg.reply_text("Usage: /delnote name")
        return

    name = ctx.args[0].lower()
    res = await db._db["notes"].delete_one({"chat_id": chat.id, "name": name})

    if res.deleted_count:
        await msg.reply_text(f"Deleted note: <code>{html.escape(name)}</code>", parse_mode="HTML")
    else:
        await msg.reply_text("Note not found.")


savenote_handler = CommandHandler("savenote", savenote_cmd)
getnote_handler = CommandHandler("getnote", getnote_cmd)
notes_handler = CommandHandler("notes", notes_cmd)
delnote_handler = CommandHandler("delnote", delnote_cmd)