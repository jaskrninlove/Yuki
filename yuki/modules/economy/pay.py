"""
Yuki Pay
Copyright © Jass
"""

from telegram import Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
)

from yuki.database.economy import (
    transfer,
    balance,
)

from yuki.utils.premium import reply


# ==========================================================
# /pay
# ==========================================================

async def pay_cmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message
    sender = update.effective_user

    if not message.reply_to_message:
        return await reply(
            message,
            """
:warning: <b>Reply Required</b>

Reply to someone's message.

Example:
<code>/pay 500</code>
""",
        )

    receiver = message.reply_to_message.from_user

    if receiver.id == sender.id:
        return await reply(
            message,
            """
:warning: <b>Nice Try~</b>

You can't pay yourself.
""",
        )

    if receiver.is_bot:
        return await reply(
            message,
            """
:warning: <b>Bots Don't Need Money</b>

Try paying a real person instead.
"""
        )

    if len(context.args) != 1:
        return await reply(
            message,
            """
:warning: <b>Invalid Usage</b>

Example

<code>/pay 1000</code>
"""
        )

    try:
        amount = int(context.args[0])
    except ValueError:
        return await reply(
            message,
            """
:warning: <b>Invalid Amount</b>

Please enter a valid number.
"""
        )

    if amount <= 0:
        return await reply(
            message,
            """
:warning: Amount must be greater than zero.
"""
        )

    if not transfer(
        sender.id,
        receiver.id,
        amount,
    ):
        return await reply(
            message,
            """
:warning: <b>Payment Failed</b>

Insufficient balance.
"""
        )

    remaining = balance(sender.id)

    await reply(
        message,
        f"""
:flower: <b>Transfer Complete</b>

<blockquote>You sent <code>{amount:,}</code> $
to: <b>{receiver.full_name}</b></blockquote>

:gold: Remaining Balance <code>{remaining:,}</code> $

:sparkle: Sharing is caring~
""",
    )


# ==========================================================
# Handler
# ==========================================================

PAY = CommandHandler(
    "pay",
    pay_cmd,
)