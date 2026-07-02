"""
Yuki Bot - Ping & Health Handlers
Premium emoji supported.
"""

import logging
import time
import psutil

from telegram import Update
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes

from yuki.core import database as db
from yuki.utils.locale import get
from yuki.utils.keyboards import back_keyboard
from yuki.utils.helpers import get_uptime
from yuki.utils import premium

log = logging.getLogger("yuki.handlers.ping")


async def ping(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    start = time.monotonic()

    msg = await update.effective_message.reply_text("Pinging...")
    latency = round((time.monotonic() - start) * 1000)

    text = get("ping.response", latency=latency)

    try:
        rendered = premium.render(text)
        await msg.edit_text(rendered, parse_mode="HTML")
    except Exception as e:
        log.debug("Ping edit failed: %s", e)


async def ping_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return

    start = time.monotonic()
    latency = round((time.monotonic() - start) * 1000 + 10)

    await query.answer(f"{latency}ms")

    text = get("ping.response", latency=latency)

    try:
        await premium.edit(
            query,
            text,
            reply_markup=back_keyboard(),
        )
    except Exception as e:
        log.debug("Ping callback edit failed: %s", e)


async def health(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message

    mem = psutil.Process().memory_info().rss // (1024 * 1024)

    try:
        await db.get_db().command("ping")
        db_status = ":success: Connected"
    except Exception:
        db_status = ":warning: Disconnected"

    text = get(
        "health.response",
        db_status=db_status,
        memory=mem,
        uptime=get_uptime(),
    )

    await premium.reply(
        msg,
        text,
        disable_web_page_preview=True,
    )


ping_cmd = CommandHandler("ping", ping)
ping_cb = CallbackQueryHandler(ping_callback, pattern="^ping$")
health_cmd = CommandHandler("health", health)