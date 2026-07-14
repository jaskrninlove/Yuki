"""
Yuki Referral - /refer
Copyright © Jass
"""

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from yuki.database.referral import get_referral_count, next_milestone, MAX_REFERRALS
from yuki.utils.premium import reply


async def refer_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user
    bot_username = (await context.bot.get_me()).username

    link = f"https://t.me/{bot_username}?start=ref_{user.id}"
    count = get_referral_count(user.id)
    threshold, reward = next_milestone(count)

    progress_text = (
        f":gift: Next reward at <code>{threshold}</code> refers: <code>${reward}</code>"
        if threshold else
        f":tada: You've hit the max referral cap ({MAX_REFERRALS})~"
    )

    await reply(
        message,
        f"""
:link: <b>Your Referral Link</b>

<blockquote>{link}</blockquote>

Share this with friends! When they start Yuki
through your link, you get closer to rewards~

:users: <b>Total Referrals</b> <code>{count}/{MAX_REFERRALS}</code>
{progress_text}
""",
        disable_web_page_preview=True,
    )


REFER = CommandHandler("refer", refer_cmd)