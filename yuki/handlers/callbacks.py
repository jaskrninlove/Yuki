"""
Yuki Bot - Callback Router
Premium emoji supported.
"""

import logging

from telegram import Update
from telegram.ext import CallbackQueryHandler, ContextTypes

from yuki.utils.locale import get
from yuki.utils.keyboards import start_keyboard, help_keyboard
from yuki.utils.helpers import full_name
from yuki.utils import premium

log = logging.getLogger("yuki.handlers.callbacks")

TOTAL_PAGES = 11


async def back_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return

    await query.answer()

    user = update.effective_user
    chat = update.effective_chat

    caption = get("start.caption", name=full_name(user) if user else "friend")
    markup = start_keyboard(is_group=chat.type != "private" if chat else False)

    try:
        await premium.edit_caption(
            query,
            caption,
            reply_markup=markup,
        )
        return
    except Exception as e:
        log.debug("Back start caption edit failed: %s", e)

    try:
        await premium.edit(
            query,
            caption,
            reply_markup=markup,
            disable_web_page_preview=True,
        )
    except Exception as e:
        log.debug("Back start text edit failed: %s", e)


async def help_router(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return

    await query.answer()

    data = query.data or "help:1"

    try:
        page = int(data.split(":")[1])
    except Exception:
        page = 1

    page = max(1, min(page, TOTAL_PAGES))

    text = get(f"help.page_{page}")

    if not text or text.startswith("help."):
        text = (
            ":book: <b>Yuki Help Menu</b>\n\n"
            f"<b>Page {page}</b>\n\n"
            "/start - Start Yuki\n"
            "/help - Show help\n"
            "/ping - Check bot speed\n"
            "/me - Your profile\n"
            "/gift - Send gift\n"
            "/mygift - Your gifts\n"
            "/qt - Make quote sticker\n"
            "/top - Top users"
        )

    markup = help_keyboard(page, TOTAL_PAGES)

    try:
        await premium.edit_caption(
            query,
            text,
            reply_markup=markup,
        )
        return
    except Exception as e:
        log.debug("Help router caption edit failed: %s", e)

    try:
        await premium.edit(
            query,
            text,
            reply_markup=markup,
            disable_web_page_preview=True,
        )
    except Exception as e:
        log.debug("Help router text edit failed: %s", e)


async def noop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()


async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return

    await query.answer("Cancelled")

    try:
        await query.delete_message()
    except Exception:
        pass


async def my_gifts_cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    from yuki.handlers.gifts import my_gifts_cmd
    await my_gifts_cmd(update, ctx)


async def leaderboard_cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    from yuki.plugins.ranking import top_cmd
    await top_cmd(update, ctx)


back_start_handler = CallbackQueryHandler(back_start, pattern="^back_start$")
help_router_handler = CallbackQueryHandler(help_router, pattern=r"^help:\d+$")
noop_handler = CallbackQueryHandler(noop, pattern="^noop$")
cancel_handler = CallbackQueryHandler(cancel, pattern="^cancel$")
my_gifts_cb_handler = CallbackQueryHandler(my_gifts_cb, pattern="^my_gifts$")
leaderboard_cb_h = CallbackQueryHandler(leaderboard_cb, pattern="^leaderboard$")