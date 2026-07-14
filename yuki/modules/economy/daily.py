"""
Yuki Daily Reward
Copyright © Jass
"""

from datetime import datetime, timezone

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from yuki.database.economy import (
    add,
    add_withdraw,
    get,
    set_daily,
)

from yuki.utils.premium import reply
from yuki.utils.rewards import daily_reward, daily_streak_bonus


async def daily_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):

    message = update.effective_message
    user = update.effective_user

    eco = get(user.id)

    today = datetime.now(timezone.utc).date()

    last = eco["last_daily"]

    if last:
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)

    if last and last.date() == today:

        return await reply(
            message,
            """
:warning: <b>Daily Already Claimed</b>

Come back tomorrow for another blessing. 🌸
""",
        )

    streak = eco["daily_streak"]

    if last:

        if (today - last.date()).days == 1:
            streak += 1
        else:
            streak = 1

    else:
        streak = 1

    reward = daily_reward()
    bonus = daily_streak_bonus(streak)

    add(user.id, reward)

    if bonus:
        add_withdraw(user.id, bonus)

    set_daily(
        user.id,
        streak,
        datetime.now(timezone.utc),
    )

    bonus_text = ""

    if bonus:
        label = "Monthly" if streak % 30 == 0 else "Weekly"
        bonus_text = (
            f"\n\n:gift: <b>{label} Streak Bonus!</b>\n"
            f"<code>+${bonus}</code> added to your withdrawable balance~"
        )

    await reply(
        message,
        f"""
:flower: <b>Daily Blessing</b>

Yuki secretly saved today's reward for you~

:gold: <b>Reward</b> <code>{reward:,}</code> $

:fire: <b>Streak</b> <code>{streak} Day{'s' if streak > 1 else ''}</code>
{bonus_text}
""",
    )


DAILY = CommandHandler(
    "daily",
    daily_cmd,
)