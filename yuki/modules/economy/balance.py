"""
Yuki Balance
Copyright © Jass
"""

from telegram import Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
)

from yuki.database.economy import get, is_dead, get_kills
from yuki.utils.rank_helpers import get_global_rank, get_group_rank
from yuki.utils.premium import reply


# ==========================================================
# Balance
# ==========================================================

async def balance_cmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message
    chat = update.effective_chat

    if message.reply_to_message:
        target = message.reply_to_message.from_user
    else:
        target = update.effective_user

    eco = get(target.id)

    status = "Dead" if is_dead(target.id) else "Alive"
    kills = get_kills(target.id)

    global_rank = await get_global_rank(target.id)
    group_rank = await get_group_rank(chat.id, target.id) if chat.type != "private" else None
    group_rank_display = group_rank if group_rank else "—"

    await reply(
        message,
        f"""
:flower: <b>{target.full_name}'s Wallet</b>

<blockquote>:trophy: <b>Global Rank</b> <code>#{global_rank}</code>
:medal: <b>Group Rank</b> <code>#{group_rank_display}</code>
:shield: <b>Status</b> <code>{status}</code>
:crossed_swords: <b>Kills</b> <code>{kills:,}</code>

:bolt: <b>Balance</b> <code>{eco.get('balance', 0):,}</code>
:gem: <b>Withdrawable</b> <code>${eco.get('withdraw_balance', 0):,}</code></blockquote>

:sparkle: Keep chatting and completing
daily activities to earn more!
""",
    )


# ==========================================================
# Handler
# ==========================================================

BALANCE = CommandHandler(
    ["balance", "bal", "wallet"],
    balance_cmd,
)