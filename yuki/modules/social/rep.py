from datetime import datetime, timedelta, timezone

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from yuki.database.reputation import (
    get,
    add,
    given,
    set_last,
)

from yuki.utils.premium import reply


COOLDOWN = timedelta(hours=12)


async def rep_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):

    message = update.effective_message
    sender = update.effective_user

    if not message.reply_to_message:

        return await reply(
            message,
            """
:warning: Reply to someone's message.

Example

<code>/rep</code>
""",
        )

    target = message.reply_to_message.from_user

    if target.id == sender.id:

        return await reply(
            message,
            ":warning: You can't give reputation to yourself.",
        )

    sender_data = get(sender.id)

    now = datetime.now(timezone.utc)

    last = sender_data.get("last_rep")

    if last:

        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)

        remain = (last + COOLDOWN) - now

        if remain.total_seconds() > 0:

            hrs = int(remain.total_seconds() // 3600)

            return await reply(
                message,
                f"""
:clock: You already gave reputation.

Try again in

<code>{hrs} hour(s)</code>
""",
            )

    add(target.id, target.full_name)

    given(sender.id)

    set_last(sender.id, now)

    await reply(
        message,
        f"""
:heart: <b>Reputation Given</b>

<b>{target.full_name}</b>

received

<code>+1 Reputation</code>

Thanks for spreading kindness 🌸
""",
    )


REP = CommandHandler(
    "rep",
    rep_cmd,
)