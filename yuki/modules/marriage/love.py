"""
Yuki Marriage - Love
Copyright © Jass
"""

import random
from datetime import datetime, timezone

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from yuki.database.marriage import (
    is_married,
    add_love,
    get_love,
    get_last_love,
    set_last_love,
)
from yuki.utils.premium import reply

LOVE_MIN = 10
LOVE_MAX = 40
LOVE_COOLDOWN = 24 * 3600


async def love_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user

    if not is_married(user.id):
        return await reply(message, ":warning: You need to be married to use /love~ Try /propose first!")

    last = get_last_love(user.id)
    now = datetime.now(timezone.utc)

    if last:
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        elapsed = (now - last).total_seconds()
        if elapsed < LOVE_COOLDOWN:
            remaining = int(LOVE_COOLDOWN - elapsed)
            h, rem = divmod(remaining, 3600)
            m, _ = divmod(rem, 60)
            return await reply(
                message,
                f":clock: <b>Already Claimed</b>\n\nCome back in <code>{h}h {m}m</code>~",
            )

    points = random.randint(LOVE_MIN, LOVE_MAX)
    add_love(user.id, points)
    set_last_love(user.id, now)

    total = get_love(user.id)

    await reply(
        message,
        f"""
:heart: <b>Love Grows~</b>

You added <code>+{points}</code> love points today!

:sparkle: <b>Total Love Points</b> <code>{total:,}</code>
""",
    )


LOVE = CommandHandler("love", love_cmd)