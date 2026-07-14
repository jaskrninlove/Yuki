"""
Yuki Rob
Copyright © Jass
"""

import random
from datetime import datetime, timezone

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from yuki.database.economy import (
    get,
    add,
    remove,
    set_pair_cooldown,
    pair_seconds_remaining,
    add_total_robbed,
    add_withdraw,
)

from yuki.utils.premium import reply
from yuki.utils.rewards import (
    rob,
    ROB_COOLDOWN,
    ROB_MIN_TARGET_BALANCE,
    ROB_FAIL_FINE,
    rob_milestone_bonus,
)


def _fmt(seconds: int) -> str:
    h, rem = divmod(seconds, 3600)
    m, _ = divmod(rem, 60)
    if h:
        return f"{h}h {m}m"
    return f"{m}m"


async def rob_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    sender = update.effective_user

    if not message.reply_to_message:
        return await reply(
            message,
            """
:warning: <b>Reply Required</b>

Reply to someone's message to rob them.

Example:
<code>/rob</code>
""",
        )

    target = message.reply_to_message.from_user

    if target.id == sender.id:
        return await reply(message, ":warning: You can't rob yourself silly~")

    if target.is_bot:
        return await reply(message, ":warning: Bots don't carry cash.")

    remaining = pair_seconds_remaining("rob", sender.id, target.id, ROB_COOLDOWN)
    if remaining:
        return await reply(
            message,
            f":clock: <b>Not Yet~</b>\n\nYou can rob <b>{target.full_name}</b> again in <code>{_fmt(remaining)}</code>.",
        )

    target_eco = get(target.id)
    target_balance = target_eco["balance"]

    if target_balance < ROB_MIN_TARGET_BALANCE:
        return await reply(
            message,
            f":warning: {target.full_name} is too broke to rob right now~",
        )

    set_pair_cooldown("rob", sender.id, target.id, datetime.now(timezone.utc))

    success, amount = rob(target_balance)

    if not success:
        fine = random.randint(*ROB_FAIL_FINE)
        remove(sender.id, fine)
        return await reply(
            message,
            f"""
:warning: <b>Rob Failed!</b>

Yuki caught you sneaking around~
You paid a fine of <code>{fine}</code> coins.
""",
        )

    remove(target.id, amount)
    add(sender.id, amount)

    total_before = get(sender.id).get("total_robbed", 0)
    add_total_robbed(sender.id, amount)
    total_after = total_before + amount

    bonus = rob_milestone_bonus(total_before, total_after)
    bonus_text = ""
    if bonus:
        add_withdraw(sender.id, bonus)
        bonus_text = f"\n\n:gift: <b>Milestone Reached!</b>\n<code>+${bonus}</code> added to your withdrawable balance~"

    await reply(
        message,
        f"""
:money: <b>Rob Successful!</b>

You stole <code>{amount:,}</code> coins from <b>{target.full_name}</b>~
{bonus_text}
""",
    )


ROB = CommandHandler("rob", rob_cmd)