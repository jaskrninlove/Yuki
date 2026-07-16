"""
Yuki Bot - New Commands Help Handler
Paginated 4-page menu for newly added features.
"""

import logging

from telegram import Update
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes

from yuki.utils.locale import get
from yuki.utils.keyboards import newcmds_keyboard
from yuki.utils import premium

log = logging.getLogger("yuki.handlers.newcommands")

TOTAL_PAGES = 4


async def newcmds_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await _send_newcmds(update, ctx, page=1, edit=False)


async def newcmds_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return

    await query.answer()

    try:
        page = int(query.data.split(":")[1])
    except Exception:
        page = 1

    await _send_newcmds(update, ctx, page=page, edit=True)


async def _send_newcmds(update: Update, ctx: ContextTypes.DEFAULT_TYPE, page: int, edit: bool):
    page = max(1, min(page, TOTAL_PAGES))

    text = get(f"newcmds.page_{page}")
    markup = newcmds_keyboard(page, TOTAL_PAGES)

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
            log.debug("Newcmds caption edit failed: %s", e)

        try:
            await premium.edit(
                query,
                text,
                reply_markup=markup,
                disable_web_page_preview=True,
            )
            return
        except Exception as e:
            log.debug("Newcmds text edit failed: %s", e)
            return

    msg = update.effective_message
    if msg:
        await premium.reply(
            msg,
            text,
            reply_markup=markup,
            disable_web_page_preview=True,
        )


cmd_handler = CommandHandler("newcommands", newcmds_cmd)
callback_handler = CallbackQueryHandler(newcmds_callback, pattern=r"^newcmds:\d+$")
