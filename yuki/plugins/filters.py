"""
Yuki Bot - Custom Filters
/filter name text
/filter name by replying to text/sticker/photo/video/document
/remove name
/filters
"""

import html
import re

from telegram import Update
from telegram.ext import CommandHandler, MessageHandler, ContextTypes, filters

from yuki.core import database as db
from yuki.utils.helpers import admin_only


def normalize_name(name: str) -> str:
    return name.strip().lower()


async def save_filter(chat_id: int, name: str, data: dict):
    name = normalize_name(name)
    await db._db["filters"].update_one(
        {"chat_id": chat_id, "name": name},
        {"$set": {"chat_id": chat_id, "name": name, **data}},
        upsert=True,
    )


async def list_filters(chat_id: int):
    cursor = db._db["filters"].find({"chat_id": chat_id})
    return [x async for x in cursor]


@admin_only
async def filter_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat = update.effective_chat

    if not msg or not chat:
        return

    if chat.type == "private":
        await msg.reply_text("This command works in groups only.")
        return

    if not ctx.args:
        await msg.reply_text(
            "<b>Usage:</b>\n"
            "<code>/filter keyword reply text</code>\n\n"
            "Or reply to text/sticker/media:\n"
            "<code>/filter keyword</code>",
            parse_mode="HTML",
        )
        return

    keyword = normalize_name(ctx.args[0])
    reply = msg.reply_to_message

    if reply:
        if reply.sticker:
            data = {"type": "sticker", "file_id": reply.sticker.file_id}
        elif reply.photo:
            data = {"type": "photo", "file_id": reply.photo[-1].file_id, "caption": reply.caption_html or reply.caption or ""}
        elif reply.video:
            data = {"type": "video", "file_id": reply.video.file_id, "caption": reply.caption_html or reply.caption or ""}
        elif reply.animation:
            data = {"type": "animation", "file_id": reply.animation.file_id, "caption": reply.caption_html or reply.caption or ""}
        elif reply.document:
            data = {"type": "document", "file_id": reply.document.file_id, "caption": reply.caption_html or reply.caption or ""}
        elif reply.audio:
            data = {"type": "audio", "file_id": reply.audio.file_id, "caption": reply.caption_html or reply.caption or ""}
        elif reply.voice:
            data = {"type": "voice", "file_id": reply.voice.file_id}
        elif reply.text:
            data = {"type": "text", "text": reply.text_html or reply.text}
        else:
            await msg.reply_text("Unsupported replied message type.")
            return
    else:
        if len(ctx.args) < 2:
            await msg.reply_text(
                "Give reply text or reply to a message.\n\n"
                "<code>/filter hello Hello there</code>",
                parse_mode="HTML",
            )
            return

        data = {"type": "text", "text": " ".join(ctx.args[1:])}

    await save_filter(chat.id, keyword, data)

    await msg.reply_text(
        f"Saved filter: <code>{html.escape(keyword)}</code>",
        parse_mode="HTML",
    )


@admin_only
async def remove_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat = update.effective_chat

    if not msg or not chat:
        return

    if not ctx.args:
        await msg.reply_text("<b>Usage:</b>\n<code>/remove keyword</code>", parse_mode="HTML")
        return

    keyword = normalize_name(ctx.args[0])

    result = await db._db["filters"].delete_one(
        {"chat_id": chat.id, "name": keyword}
    )

    if result.deleted_count:
        await msg.reply_text(
            f"Removed filter: <code>{html.escape(keyword)}</code>",
            parse_mode="HTML",
        )
    else:
        await msg.reply_text("That filter does not exist.")


async def filters_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat = update.effective_chat

    if not msg or not chat:
        return

    saved = await list_filters(chat.id)

    if not saved:
        await msg.reply_text("No filters saved in this chat.")
        return

    text = "<b>Saved Filters</b>\n\n" + "\n".join(
        f"• <code>{html.escape(x.get('name', 'unknown'))}</code>"
        for x in saved
    )

    await msg.reply_text(text, parse_mode="HTML")


async def send_filter_reply(msg, data: dict):
    ftype = data.get("type")

    if ftype == "text":
        await msg.reply_text(data.get("text", ""), parse_mode="HTML", disable_web_page_preview=True)
    elif ftype == "sticker":
        await msg.reply_sticker(data.get("file_id"))
    elif ftype == "photo":
        await msg.reply_photo(data.get("file_id"), caption=data.get("caption") or None, parse_mode="HTML")
    elif ftype == "video":
        await msg.reply_video(data.get("file_id"), caption=data.get("caption") or None, parse_mode="HTML")
    elif ftype == "animation":
        await msg.reply_animation(data.get("file_id"), caption=data.get("caption") or None, parse_mode="HTML")
    elif ftype == "document":
        await msg.reply_document(data.get("file_id"), caption=data.get("caption") or None, parse_mode="HTML")
    elif ftype == "audio":
        await msg.reply_audio(data.get("file_id"), caption=data.get("caption") or None, parse_mode="HTML")
    elif ftype == "voice":
        await msg.reply_voice(data.get("file_id"))


async def filter_watch_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat = update.effective_chat

    if not msg or not chat or chat.type == "private":
        return

    text = msg.text or msg.caption or ""
    if not text or text.startswith("/"):
        return

    saved = await list_filters(chat.id)
    if not saved:
        return

    lower = text.lower().strip()

    for item in saved:
        keyword = item.get("name", "").lower().strip()
        if not keyword:
            continue

        if lower == keyword or re.search(rf"\b{re.escape(keyword)}\b", lower):
            await send_filter_reply(msg, item)
            return


filter_handler = CommandHandler("filter", filter_cmd)
remove_handler = CommandHandler("remove", remove_cmd)
filters_handler = CommandHandler("filters", filters_cmd)

filter_watch_h = MessageHandler(
    filters.TEXT & ~filters.COMMAND,
    filter_watch_handler,
)