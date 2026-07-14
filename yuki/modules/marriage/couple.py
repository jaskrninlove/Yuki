"""
Yuki Marriage - Couple Profile
Copyright © Jass
"""

from datetime import datetime, timezone

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from yuki.database.marriage import is_married, get_partner_id, get_marriage
from yuki.utils.premium import reply


async def couple_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user

    if not is_married(user.id):
        return await reply(
            message,
            """
:ring: <b>You're Single~</b>

Use <code>/propose</code> (reply to someone) to find your special someone!
""",
        )

    partner_id = get_partner_id(user.id)
    marriage = get_marriage(user.id)

    try:
        partner = await context.bot.get_chat(partner_id)
        partner_name = partner.full_name
    except Exception:
        partner_name = "Unknown"

    married_since = marriage.get("married_since")
    love_points = marriage.get("love_points", 0)

    since_str = "Unknown"
    days = 0
    anniv_text = ""

    if married_since:
        if married_since.tzinfo is None:
            married_since = married_since.replace(tzinfo=timezone.utc)

        days = (datetime.now(timezone.utc) - married_since).days
        since_str = married_since.strftime("%d %b %Y")

        try:
            today = datetime.now(timezone.utc).date()
            anniv_this_year = married_since.date().replace(year=today.year)
            if anniv_this_year < today:
                anniv_this_year = anniv_this_year.replace(year=today.year + 1)
            days_to_anniv = (anniv_this_year - today).days

            if days_to_anniv == 0:
                anniv_text = ":tada: <b>Happy Anniversary Today!</b>"
            else:
                anniv_text = f":calendar: Anniversary in <code>{days_to_anniv}</code> days"
        except Exception:
            anniv_text = ""

    await reply(
        message,
        f"""
:ring: <b>Couple Profile</b>

<blockquote>
:user: <b>{user.full_name}</b> :heart: <b>{partner_name}</b>

:calendar: <b>Married Since</b> <code>{since_str}</code>
:hourglass: <b>Together For</b> <code>{days} days</code>
:sparkle: <b>Love Points</b> <code>{love_points:,}</code>

{anniv_text}
</blockquote>
""",
    )


COUPLE = CommandHandler(["couple", "marriage"], couple_cmd)