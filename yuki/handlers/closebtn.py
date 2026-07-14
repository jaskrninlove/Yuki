"""
Yuki — Generic Close Button Handler
Handles callback_data="close" used across rankings/profile keyboards.
"""

import logging

from telegram import Update
from telegram.ext import CallbackQueryHandler, ContextTypes

log = logging.getLogger("yuki.close")


async def close_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        await query.message.delete()
        return
    except Exception as e:
        log.debug("Message delete failed, falling back to edit: %s", e)

    try:
        await query.edit_message_text("Closed.")
    except Exception:
        try:
            await query.edit_message_caption("Closed.")
        except Exception as e:
            log.warning("Close fallback also failed: %s", e)


CLOSE_HANDLER = CallbackQueryHandler(close_callback, pattern=r"^close$")