"""
Yuki Crime
Copyright © Jass
"""

from datetime import datetime, timedelta, timezone

from telegram import Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
)

from yuki.database.economy import (
    add,
    remove,
    get,
    set_cooldown,
)

from yuki.utils.premium import reply
from yuki.utils.rewards import crime


COOLDOWN = timedelta(minutes=20)


SUCCESS_MESSAGES = [
    "You hacked an abandoned ATM.",
    "You found an unlocked treasure vault.",
    "You escaped with a mysterious briefcase.",
    "You sold rare anime merchandise on the black market.",
    "A rich collector paid you for a secret artifact.",
]

FAIL_MESSAGES = [
    "The police caught you immediately.",
    "Your plan completely failed.",
    "Someone reported your suspicious activity.",
    "You accidentally robbed an undercover officer.",
    "You slipped while escaping and got caught.",
]


# ==========================================================
# Crime
# ==========================================================

async def crime_cmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message
    user = update.effective_user

    eco = get(user.id)

    now = datetime.now(timezone.utc)

    last = eco.get("last_crime")

    if last:

        remaining = (last + COOLDOWN) - now

        if remaining.total_seconds() > 0:

            mins = int(remaining.total_seconds() // 60)
            secs = int(remaining.total_seconds() % 60)

            return await reply(
                message,
                f"""
:clock: <b>Lay Low...</b>

The authorities are still watching.

Try again in

<code>{mins}m {secs}s</code>
""",
            )

    success, amount = crime()

    set_cooldown(
        user.id,
        "last_crime",
        now,
    )

    import random

    if success:

        add(user.id, amount)

        text = random.choice(SUCCESS_MESSAGES)

        return await reply(
            message,
            f"""
:mask: <b>Crime Successful</b>

<blockquote>{text}</blockquote>

:gold: Reward

<code>✦ +{amount:,}</code>
""",
        )

    remove(user.id, amount)

    text = random.choice(FAIL_MESSAGES)

    await reply(
        message,
        f"""
:warning: <b>Crime Failed</b>

<blockquote>{text}</blockquote>

:gold: Fine

<code>✦ -{amount:,}</code>
""",
    )


CRIME = CommandHandler(
    "crime",
    crime_cmd,
)