"""
Yuki Word Grid — Rankings
Copyright © Jass
"""

from __future__ import annotations
import logging
log = logging.getLogger("yuki.wordgrid.rankings")
from telegram import Update
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes

from yuki.database.wordgrid_stats import group_ranking, global_ranking, today_ranking, my_points
from yuki.utils.keyboards import wordgrid_rankings_keyboard
from yuki.utils.premium import reply, edit

MEDALS = [":gold:", ":silver:", ":bronze:"] + [f":rank: {i}." for i in range(4, 11)]


def _format_list(entries: list) -> str:
    if not entries:
        return "<i>No data yet~ Play /newgrid to get on the board!</i>"

    lines = []
    for i, entry in enumerate(entries):
        medal = MEDALS[i] if i < len(MEDALS) else f":rank: {i + 1}."
        lines.append(f"{medal} <b>{entry['name']}</b> — <code>{entry['points']}</code> pts")
    return "<blockquote>" + "\n".join(lines) + "</blockquote>"


async def wordgridrankings_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat = update.effective_chat

    entries = group_ranking(chat.id) if chat.type != "private" else global_ranking()
    title = ":grid: <b>Word Grid — Group Rankings</b>" if chat.type != "private" else ":grid: <b>Word Grid — Global Rankings</b>"

    text = f"{title}\n\n{_format_list(entries)}"

    await reply(msg, text, reply_markup=wordgrid_rankings_keyboard(), disable_web_page_preview=True)


async def wordgridrankings_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat = update.effective_chat
    user = update.effective_user

    await query.answer()
    action = query.data

    if action == "wgrank_group":
        if chat.type == "private":
            await query.answer("This only works in groups~", show_alert=True)
            return
        entries = group_ranking(chat.id)
        text = f":grid: <b>Word Grid — Group Rankings</b>\n\n{_format_list(entries)}"

    elif action == "wgrank_global":
        entries = global_ranking()
        text = f":grid: <b>Word Grid — Global Rankings</b>\n\n{_format_list(entries)}"

    elif action == "wgrank_today":
        if chat.type == "private":
            await query.answer("This only works in groups~", show_alert=True)
            return
        entries = today_ranking(chat.id)
        text = f":grid: <b>Word Grid — Today's Rankings</b>\n\n{_format_list(entries)}"

    elif action == "wgrank_me":
        stats = my_points(user.id)
        text = (
            f":grid: <b>{user.full_name}'s Word Grid Stats</b>\n\n"
            f"<blockquote>"
            f":sparkle: <b>Total Points</b> <code>{stats['total_points']}</code>\n"
            f":check: <b>Words Found</b> <code>{stats['words_found']}</code>"
            f"</blockquote>"
        )

    else:
        return

    try:
        await edit(query, text, reply_markup=wordgrid_rankings_keyboard(), disable_web_page_preview=True)
    except Exception as e:
        if "not modified" not in str(e).lower():
            log.warning("Wordgrid rankings edit failed: %s", e)


WORDGRID_RANKINGS_CMD = CommandHandler("wordgridrankings", wordgridrankings_cmd)
WORDGRID_RANKINGS_CB = CallbackQueryHandler(
    wordgridrankings_callback,
    pattern=r"^wgrank_(group|global|today|me)$",
)