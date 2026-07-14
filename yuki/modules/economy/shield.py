"""
Yuki Shield
Copyright © Jass
"""

from datetime import datetime, timedelta, timezone

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from yuki.database.economy import (
    get,
    remove,
    remove_withdraw,
    set_shield,
    has_shield,
    has_permanent_shield,
    set_permanent_shield,
    shield_remaining,
)

from yuki.utils.premium import reply
from yuki.utils.rewards import SHIELD_COST, SHIELD_DURATION, PERMANENT_SHIELD_COST


def _fmt(seconds: int) -> str:
    h, rem = divmod(seconds, 3600)
    m, _ = divmod(rem, 60)
    if h:
        return f"{h}h {m}m"
    return f"{m}m"


async def shield_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user

    if has_permanent_shield(user.id):
        return await reply(
            message,
            """
:shield: <b>Already Permanently Protected!</b>

No one can ever touch you~ 🌸
""",
        )

    # /shield permanent
    if context.args and context.args[0].lower() == "permanent":
        eco = get(user.id)

        if eco["withdraw_balance"] < PERMANENT_SHIELD_COST:
            return await reply(
                message,
                f"""
:warning: <b>Not Enough Withdrawable Balance</b>

A permanent shield costs <code>${PERMANENT_SHIELD_COST}</code> from your withdrawable balance.
Your withdrawable balance: <code>${eco['withdraw_balance']:,}</code>
""",
            )

        remove_withdraw(user.id, PERMANENT_SHIELD_COST)
        set_permanent_shield(user.id, True)

        return await reply(
            message,
            f"""
:shield: <b>Permanent Shield Activated!</b>

You are now protected from <code>/kill</code> forever~

:warning: <i>In exchange, you can no longer use <code>/kill</code> on others.</i>

:gold: <code>-${PERMANENT_SHIELD_COST}</code> withdrawable balance spent
""",
        )

    # normal /shield
    if has_shield(user.id):
        remaining = shield_remaining(user.id)
        if remaining:
            return await reply(
                message,
                f"""
:shield: <b>Already Protected!</b>

Your shield is still active for <code>{_fmt(remaining)}</code>.
""",
            )

    eco = get(user.id)

    if eco["balance"] < SHIELD_COST:
        return await reply(
            message,
            f"""
:warning: <b>Not Enough Coins</b>

A shield costs <code>{SHIELD_COST}</code> coins.
Your balance: <code>{eco['balance']:,}</code>

<i>Tip: Use <code>/shield permanent</code> for permanent protection (costs withdrawable balance, but you give up your own <code>/kill</code> ability).</i>
""",
        )

    remove(user.id, SHIELD_COST)

    until = datetime.now(timezone.utc) + timedelta(seconds=SHIELD_DURATION)
    set_shield(user.id, until)

    await reply(
        message,
        f"""
:shield: <b>Shield Activated!</b>

You're protected from kills for <code>{_fmt(SHIELD_DURATION)}</code>~

:gold: <code>-{SHIELD_COST}</code> coins spent

<i>Tip: Use <code>/shield permanent</code> for permanent protection.</i>
""",
    )


SHIELD = CommandHandler("shield", shield_cmd)