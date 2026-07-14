"""
Yuki Bot - /qt /quote Command
Generate quote stickers from replied messages, rendered locally.
"""

import logging

from telegram import Update
from telegram.error import BadRequest, TimedOut, NetworkError, RetryAfter
from telegram.ext import CommandHandler, ContextTypes

from yuki.utils.helpers import full_name
from yuki.utils.quote_render import render_quote

log = logging.getLogger("yuki.plugins.quote")


async def _safe_edit(message, text: str):
    try:
        if message:
            await message.edit_text(text)
    except BadRequest as e:
        if "Message to edit not found" in str(e):
            return
        if "Message is not modified" in str(e):
            return
    except Exception:
        pass


async def _safe_delete(message):
    try:
        if message:
            await message.delete()
    except Exception:
        pass


async def _get_avatar_bytes(ctx, user) -> bytes | None:
    try:
        photos = await ctx.bot.get_user_profile_photos(user.id, limit=1)
        if photos.total_count > 0:
            file = await ctx.bot.get_file(photos.photos[0][-1].file_id)
            return bytes(await file.download_as_bytearray())
    except Exception:
        pass
    return None


async def quote_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg:
        return

    target = msg.reply_to_message

    if not target:
        await msg.reply_text(
            "Reply to a text message and use <code>/qt</code> or <code>/quote</code>.",
            parse_mode="HTML",
        )
        return

    text = target.text or target.caption
    if not text:
        await msg.reply_text(
            "Reply to a text message or caption to create a quote sticker.",
            parse_mode="HTML",
        )
        return

    user = target.from_user or update.effective_user
    if not user:
        return

    processing = None

    try:
        processing = await msg.reply_text("Creating quote sticker...")

        avatar_bytes = await _get_avatar_bytes(ctx, user)
        webp_bytes = render_quote(full_name(user), text, avatar_bytes)

        await _safe_delete(processing)

        import io
        sticker_buf = io.BytesIO(webp_bytes)
        sticker_buf.name = "quote.webp"

        try:
            await msg.reply_sticker(
                sticker=sticker_buf,
                read_timeout=60,
                write_timeout=60,
                connect_timeout=30,
                pool_timeout=30,
            )
        except (TimedOut, NetworkError, RetryAfter) as e:
            log.warning("Sticker send failed once, retrying as document: %s", e)
            sticker_buf.seek(0)
            await msg.reply_document(
                document=sticker_buf,
                filename="quote.webp",
                caption="Sticker upload timed out, sent as file instead.",
                read_timeout=60,
                write_timeout=60,
                connect_timeout=30,
                pool_timeout=30,
            )

        log.info("Quote sticker generated for user %s", user.id)

    except Exception as e:
        log.exception("Quote generation failed: %s", e)
        await _safe_edit(
            processing,
            "Couldn't generate the quote sticker right now. Please try again later.",
        )


qt_handler = CommandHandler("qt", quote_cmd)
quote_handler = CommandHandler("quote", quote_cmd)