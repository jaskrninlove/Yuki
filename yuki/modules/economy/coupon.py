"""
Yuki Coupons
Copyright © Jass

/createcoupon — owner only, loot-box style redeem codes.
/redeem — anyone can claim, reward lands in their spendable 'balance'.
"""

import random
import string
from datetime import datetime, timedelta, timezone

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from yuki.core import config
from yuki.database.coupons import create_coupon, redeem_coupon
from yuki.utils.premium import reply


def _gen_code(length: int = 8) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(random.choice(alphabet) for _ in range(length))


async def create_coupon_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/createcoupon <amount> <max_uses> <minutes_valid> [custom_code]
    Owner only. Example: /createcoupon 500 50 60  -> 500 coins each, 50 people, valid 1 hour."""
    user = update.effective_user
    message = update.effective_message

    if not user or user.id != config.OWNER_ID:
        return await reply(message, ":warning: Owner-only command.")

    args = context.args
    if len(args) < 3:
        return await reply(
            message,
            """
:gift: <b>Usage</b>

<code>/createcoupon [amount] [max_uses] [minutes_valid] [code?]</code>

Example: <code>/createcoupon 500 50 60</code>
= 500 coins each, 50 people, valid 1 hour~
""",
        )

    try:
        amount = int(args[0])
        max_uses = int(args[1])
        minutes_valid = int(args[2])
    except ValueError:
        return await reply(message, ":warning: Amount, max uses, and minutes must all be numbers.")

    if amount <= 0 or max_uses <= 0 or minutes_valid <= 0:
        return await reply(message, ":warning: All values must be positive.")

    code = args[3].upper() if len(args) > 3 else _gen_code()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=minutes_valid)

    create_coupon(code, amount, max_uses, expires_at, user.id)

    await reply(
        message,
        f"""
:gift: <b>Coupon created!</b>

:dot2: <b>Code:</b> <code>{code}</code>
:gold: <b>Reward:</b> <code>{amount}</code> coins each
:users: <b>Max uses:</b> <code>{max_uses}</code>
:clock: <b>Valid for:</b> <code>{minutes_valid}</code> minute(s)

Share it — anyone can redeem with <code>/redeem {code}</code>~
""",
    )


async def redeem_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/redeem <code> — anyone can use this."""
    user = update.effective_user
    message = update.effective_message

    if not context.args:
        return await reply(message, "Usage: <code>/redeem CODE</code> :gift:")

    code = context.args[0].upper()
    ok, reason, amount = redeem_coupon(code, user.id)

    if ok:
        return await reply(
            message,
            f":sparkle: <b>Coupon redeemed!</b>\n\n+<code>{amount}</code> coins added to your balance~ :gold:",
        )

    messages = {
        "not_found": ":warning: That coupon code doesn't exist.",
        "expired": ":warning: This coupon has expired.",
        "already_used": ":warning: You've already redeemed this coupon.",
        "maxed_out": ":warning: This coupon has been fully claimed — better luck next time!",
    }
    await reply(message, messages.get(reason, ":warning: Couldn't redeem that coupon."))


CREATECOUPON = CommandHandler("createcoupon", create_coupon_cmd)
REDEEM = CommandHandler("redeem", redeem_cmd)
