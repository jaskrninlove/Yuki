"""
Yuki Bot - Help Handler
Paginated 11-page help menu with premium emoji support.
"""

import logging

from telegram import Update
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes

from yuki.utils.locale import get
from yuki.utils.keyboards import help_keyboard
from yuki.utils import premium

log = logging.getLogger("yuki.handlers.help")

TOTAL_PAGES = 11


async def help_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await _send_help(update, ctx, page=1, edit=False)


async def help_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return

    await query.answer()

    try:
        page = int(query.data.split(":")[1])
    except Exception:
        page = 1

    await _send_help(update, ctx, page=page, edit=True)


async def _send_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE, page: int, edit: bool):
    page = max(1, min(page, TOTAL_PAGES))

    text = get(f"help.page_{page}")
    markup = help_keyboard(page, TOTAL_PAGES)

    if edit and update.callback_query:
        query = update.callback_query

        try:
            await premium.edit_caption(
                query,
                text,
                reply_markup=markup,
            )
            return
        except Exception as e:
            log.debug("Help caption edit failed: %s", e)

        try:
            await premium.edit(
                query,
                text,
                reply_markup=markup,
                disable_web_page_preview=True,
            )
            return
        except Exception as e:
            log.debug("Help text edit failed: %s", e)
            return

    msg = update.effective_message
    if msg:
        await premium.reply(
            msg,
            text,
            reply_markup=markup,
            disable_web_page_preview=True,
        )


cmd_handler = CommandHandler("help", help_cmd)
callback_handler = CallbackQueryHandler(help_callback, pattern=r"^help:\d+$")