"""
Yuki Translate
Copyright © Jass
"""

from __future__ import annotations

import html
import logging

import httpx

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from yuki.utils.premium import reply

log = logging.getLogger("yuki.translate")

# Google's free public translate endpoint (same one browser extensions use).
# No API key needed, but it's an unofficial endpoint — Google could change/
# rate-limit it without notice. If that ever happens, this is the one place
# to swap in the official Cloud Translation API instead.
GOOGLE_TRANSLATE_URL = "https://translate.googleapis.com/translate_a/single"

MAX_CHARS = 3000


async def _google_translate(text: str, target_lang: str = "en") -> str | None:
    params = {
        "client": "gtx",
        "sl": "auto",
        "tl": target_lang,
        "dt": "t",
        "q": text[:MAX_CHARS],
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(GOOGLE_TRANSLATE_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        # data[0] is a list of [translated_chunk, original_chunk, ...] segments
        translated = "".join(seg[0] for seg in data[0] if seg and seg[0])
        detected_lang = data[2] if len(data) > 2 else None

        return translated, detected_lang

    except Exception as e:
        log.warning("Google Translate request failed: %s", e)
        return None, None


async def translate_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message

    if not message.reply_to_message:
        return await reply(
            message,
            """
:sparkle: <b>Translate</b>

Reply to any message with <code>/tr</code> to translate it to English.
""",
        )

    target = message.reply_to_message
    text = target.text or target.caption

    if not text:
        return await reply(message, ":warning: That message has no text to translate.")

    translated, detected_lang = await _google_translate(text, "en")

    if not translated:
        return await reply(message, ":warning: Translation failed, please try again.")

    lang_line = f"<i>Detected: {html.escape(detected_lang)}</i>\n\n" if detected_lang else ""

    await reply(
        message,
        f""":sparkle: <b>Translation</b>

{lang_line}<blockquote>{html.escape(translated)}</blockquote>""",
    )


TRANSLATE_CMD = CommandHandler(["tr", "translate"], translate_cmd)