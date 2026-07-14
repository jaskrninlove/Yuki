"""
Yuki Leaderboard
Copyright © Jass
"""

from telegram import Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
)

from yuki.database.economy import richest

from yuki.utils.premium import reply


MEDALS = {
    1: ":gold:",
    2: ":silver:",
    3: ":bronze:",
}


async def leaderboard_cmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message

    users = richest(10)

    if not users:
        return await reply(
            message,
            """
:warning: No leaderboard data yet.
"""
        )

    text = """
:trophy: <b>Yuki Richest Players</b>

━━━━━━━━━━━━━━━━━━

"""

    for index, user in enumerate(users, start=1):

        try:
            member = await context.bot.get_chat(user["_id"])
            name = member.full_name
        except Exception:
            name = "Unknown User"

        medal = MEDALS.get(index, f"<b>{index}.</b>")

        text += (
            f"{medal} <b>{name}</b>\n"
            f"<code>✦ {user['balance']:,}</code>\n\n"
        )

    text += "━━━━━━━━━━━━━━━━━━\n:sparkle: Keep earning to climb the rankings!"

    await reply(message, text)


LEADERBOARD = CommandHandler(
    ["leaderboard", "lb", "rich"],
    leaderboard_cmd,
)