"""
Yuki Rankings Callbacks
Copyright © Jass
"""

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    ContextTypes,
)

from yuki.utils.premium import edit, edit_caption
from yuki.utils.keyboards import (
    rankings_keyboard,
    rankings_back_keyboard,
)

from .helpers import (
    richest_text,
    levels_text,
    reputation_text,
    activity_text,
    stats_text,
    love_text,
    referral_text,
)

from yuki.modules.rankings.rankings import (
    build_group_top,
    build_my_rank,
    build_today_top,
    build_global_top,
)


HUB_TEXT = """
:trophy: <b>Yuki Hall of Fame</b>

<blockquote>Every message, level, and coin brings you closer to becoming a legend.:crown:</blockquote>

Choose a category below :sparkle:
"""


async def _edit_ranking(query, text: str, markup):
    """Works whether the original message is a photo (caption) or plain text."""
    try:
        await edit_caption(query, text, reply_markup=markup)
        return
    except Exception:
        pass
    try:
        await edit(query, text, reply_markup=markup, disable_web_page_preview=True)
    except Exception:
        pass


# ==========================================================
# Rankings Callback
# ==========================================================

async def rankings_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    await query.answer()

    data = query.data
    chat = update.effective_chat
    user = update.effective_user

    # ================= HOME / PAGE SWITCH =================

    if data in ("rk_home", "rk_back"):
        await _edit_ranking(query, HUB_TEXT, rankings_keyboard(page=1))
        return

    if data.startswith("rk_page:"):
        page = int(data.split(":")[1])
        await _edit_ranking(query, HUB_TEXT, rankings_keyboard(page=page))
        return

    # ================= WEALTH =================

    if data == "rk_rich":
        await _edit_ranking(query, await richest_text(), rankings_back_keyboard())
        return

    # ================= LEVEL =================

    if data == "rk_level":
        await _edit_ranking(query, await levels_text(), rankings_back_keyboard())
        return

    # ================= REP =================

    if data == "rk_rep":
        await _edit_ranking(query, await reputation_text(), rankings_back_keyboard())
        return

    # ================= ACTIVITY =================

    if data == "rk_active":
        await _edit_ranking(query, await activity_text(), rankings_back_keyboard())
        return

    # ================= STATS =================

    if data == "rk_stats":
        await _edit_ranking(query, await stats_text(), rankings_back_keyboard())
        return

    # ================= LOVE =================

    if data == "rk_love":
        await _edit_ranking(query, await love_text(), rankings_back_keyboard())
        return

    # ================= REFERRALS =================

    if data == "rk_refer":
        await _edit_ranking(query, await referral_text(), rankings_back_keyboard())
        return

    # ================= CHAT TOP =================

    if data == "rk_top":
        if not chat or chat.type == "private":
            await query.answer("Use this in a group.", show_alert=True)
            return
        await _edit_ranking(query, await build_group_top(chat.id), rankings_back_keyboard())
        return

    # ================= MY RANK =================

    if data == "rk_rank":
        if not chat or chat.type == "private":
            await query.answer("Use this in a group.", show_alert=True)
            return
        await _edit_ranking(query, await build_my_rank(chat.id, user), rankings_back_keyboard())
        return

    # ================= TODAY =================

    if data == "rk_today":
        if not chat or chat.type == "private":
            await query.answer("Use this in a group.", show_alert=True)
            return
        await _edit_ranking(query, await build_today_top(chat.id), rankings_back_keyboard())
        return

    # ================= GLOBAL TOP =================

    if data == "rk_globaltop":
        await _edit_ranking(query, await build_global_top(), rankings_back_keyboard())
        return


# ==========================================================
# Handler
# ==========================================================

RANKINGS_CALLBACK = CallbackQueryHandler(
    rankings_callback,
    pattern=r"^rk_",
)