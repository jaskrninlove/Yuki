"""
Yuki Profile
Copyright © Jass
"""

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from yuki.core.database import get_user as user_id
from yuki.database.economy import get as get_economy, is_dead, get_kills
from yuki.database.reputation import get as get_reputation
from yuki.database.marriage import is_married, get_partner_id
from yuki.database.achievements import count as achievement_count
from yuki.utils.rank_helpers import get_global_rank, get_group_rank

from yuki.utils.premium import reply
from yuki.utils.xp import (
    progress_bar,
    xp_required,
    xp_in_level,
)

from yuki.utils.premium import render
from yuki.utils.keyboards import profile_keyboard


# ==========================================================
# Profile
# ==========================================================

async def profile_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat = update.effective_chat

    target = (
        message.reply_to_message.from_user
        if message.reply_to_message
        else update.effective_user
    )

    user = await user_id(target.id)
    user = user or {}

    eco = get_economy(target.id)
    rep = get_reputation(target.id)

    partner = "Single"

    if is_married(target.id):
        partner_id = get_partner_id(target.id)
        try:
            member = await context.bot.get_chat(partner_id)
            partner = member.full_name
        except Exception:
            partner = "Unknown"

    joined = user.get("joined")
    joined_str = joined.strftime("%d %b %Y") if joined else "Unknown"

    level = user.get("level", 1)
    xp = user.get("xp", 0)

    status = "Dead" if is_dead(target.id) else "Alive"
    kills = get_kills(target.id)

    global_rank = await get_global_rank(target.id)
    group_rank = await get_group_rank(chat.id, target.id) if chat.type != "private" else None
    group_rank_display = group_rank if group_rank else "—"

    text = f"""
:flower: <b>{target.full_name}</b>'s Profile: 

<blockquote>:trophy: <b>Global Rank</b> <code>#{global_rank}</code>
:medal: <b>Group Rank</b> <code>#{group_rank_display}</code>
:shield: <b>Status</b> <code>{status}</code>
:crossed_swords: <b>Kills</b> <code>{kills:,}</code>

:star: <b>Level</b> <code>{level}</code>
:sparkle: <b>XP</b> <code>{xp_in_level(xp)} / {xp_required(level)}</code>
<code>{progress_bar(xp, level)}</code>

:gold: <b>Balance</b> <code>{eco.get('balance', 0):,}</code> $
:heart: <b>Reputation</b> <code>{rep.get('rep', 0)}</code>
:ring: <b>Partner</b> <code>{partner}</code>
:achievement: <b>Achievements</b> <code>{achievement_count(target.id)}</code>
:chat: <b>Messages</b> <code>{user.get('total_messages', 0):,}</code>
:calendar: <b>Joined</b> <code>{joined_str}</code>
</blockquote>
"""

    await reply(
        message,
        text,
        reply_markup=profile_keyboard(target.id == update.effective_user.id),
    )


# ==========================================================
# Handler
# ==========================================================

PROFILE = CommandHandler(
    ["profile", "me"],
    profile_cmd,
)