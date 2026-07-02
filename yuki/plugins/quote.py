"""
Yuki Bot - /qt /quote Command
Generate quote stickers from replied messages.
"""

import base64
import logging
import os
import tempfile

import httpx
from telegram import Update
from telegram.error import BadRequest, TimedOut, NetworkError, RetryAfter
from telegram.ext import CommandHandler, ContextTypes

from yuki.core.config import QUOTLY_API
from yuki.utils.helpers import full_name

log = logging.getLogger("yuki.plugins.quote")


def _build_quotly_payload(user, text: str, avatar_url: str | None = None) -> dict:
    return {
        "type": "quote",
        "format": "webp",
        "backgroundColor": "#1a1a2e",
        "width": 512,
        "height": 256,
        "scale": 2,
        "messages": [
            {
                "entities": [],
                "avatar": True,
                "from": {
                    "id": user.id,
                    "name": full_name(user),
                    "photo": {"url": avatar_url} if avatar_url else None,
                },
                "text": text[:1000],
                "replyMessage": {},
            }
        ],
    }


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


async def _get_avatar_url(ctx, user) -> str | None:
    try:
        photos = await ctx.bot.get_user_profile_photos(user.id, limit=1)
        if photos.total_count > 0:
            file = await ctx.bot.get_file(photos.photos[0][-1].file_id)
            return file.file_path
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
    tmp_path = None

    try:
        processing = await msg.reply_text("Creating quote sticker...")

        avatar_url = await _get_avatar_url(ctx, user)
        payload = _build_quotly_payload(user, text, avatar_url)

        timeout = httpx.Timeout(connect=10.0, read=35.0, write=20.0, pool=10.0)

        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(QUOTLY_API, json=payload)
            resp.raise_for_status()
            data = resp.json()

        if not data.get("ok"):
            raise ValueError(f"Quotly API returned error: {data}")

        img_b64 = data.get("result", {}).get("image")
        if not img_b64:
            raise ValueError("No image returned from Quotly API")

        img_bytes = base64.b64decode(img_b64)

        with tempfile.NamedTemporaryFile(suffix=".webp", delete=False) as f:
            f.write(img_bytes)
            tmp_path = f.name

        await _safe_delete(processing)

        try:
            with open(tmp_path, "rb") as f:
                await msg.reply_sticker(
                    sticker=f,
                    read_timeout=60,
                    write_timeout=60,
                    connect_timeout=30,
                    pool_timeout=30,
                )
        except (TimedOut, NetworkError, RetryAfter) as e:
            log.warning("Sticker send failed once, retrying: %s", e)
            await msg.reply_document(
                document=open(tmp_path, "rb"),
                filename="quote.webp",
                caption="Sticker upload timed out, sent as file instead.",
                read_timeout=60,
                write_timeout=60,
                connect_timeout=30,
                pool_timeout=30,
            )

        log.info("Quote sticker generated for user %s", user.id)

    except httpx.TimeoutException:
        log.warning("Quotly API timeout")
        await _safe_edit(
            processing,
            "Quote service took too long to respond. Please try again.",
        )

    except Exception as e:
        log.exception("Quote generation failed: %s", e)
        await _safe_edit(
            processing,
            "Couldn't generate the quote sticker right now. Please try again later.",
        )

    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


qt_handler = CommandHandler("qt", quote_cmd)
quote_handler = CommandHandler("quote", quote_cmd)