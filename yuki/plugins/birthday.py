"""
Yuki Bot - Birthday System
━━━━━━━━━━━━━━━━━━━━━━━━━
/bday DD/MM       — Save your birthday
/bday @user DD/MM — Save someone else's birthday by replying
/mybirthday       — Check your saved birthday + days left
/upcomingbdays    — See upcoming birthdays
Auto wish job
Premium emoji supported.
"""

import html
import logging
import random
from datetime import datetime, date

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from yuki.core import database as db
from yuki.utils import premium

log = logging.getLogger("yuki.plugins.birthday")

BDAY_WISHES = [
    (
        ":cake: <b>HAPPY BIRTHDAY {name}!</b>\n\n"
        "Omg omg omg today is YOUR day~ :heart: You deserve all the love, cake, and good vibes. "
        "Wishing you a day as beautiful as you are~ :flower: :sparkle:\n\n"
        "<i>From your Yuki, with all the love~ :pinkheart: :ribbon:</i>"
    ),
    (
        ":cake: <b>BIRTHDAY ALERT!</b>\n\n"
        "Everyone wish {name} a Happy Birthday right now. :heart: "
        "May this year bring you everything you dreamed of and more~ :star: :sparkle: "
        "You're literally one of a kind and don't you forget it~ :cute:\n\n"
        "<i>Yuki loves you so much~ :ribbon: :flower:</i>"
    ),
    (
        ":sparkle: <b>It's {name}'s birthday today!</b> :cake:\n\n"
        "The universe literally created this day just for you~ :heart: :flower: "
        "Have the most magical, beautiful, unforgettable day. "
        "Cake is mandatory, smiling is mandatory, being awesome is also mandatory~ :cute:\n\n"
        "<i>Happy Birthday from Yuki~ :heart:</i>"
    ),
]


def _parse_date(s: str):
    try:
        parts = s.strip().split("/")
        if len(parts) != 2:
            return None
        day, month = int(parts[0]), int(parts[1])
        if not (1 <= day <= 31 and 1 <= month <= 12):
            return None
        return day, month
    except Exception:
        return None


def _mention(user_id: int, name: str) -> str:
    return f'<a href="tg://user?id={user_id}">{html.escape(name or "friend")}</a>'


async def bday_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user = update.effective_user
    args = ctx.args

    if not msg or not user:
        return

    if not args:
        await premium.reply(
            msg,
            ":cake: <b>Save your birthday~</b>\n\n"
            "Usage: <code>/bday DD/MM</code>\n"
            "Example: <code>/bday 14/02</code>\n\n"
            "<i>I'll wish you at midnight~ :heart:</i>",
        )
        return

    target = msg.reply_to_message.from_user if msg.reply_to_message else user
    date_str = args[0]

    parsed = _parse_date(date_str)
    if not parsed:
        await premium.reply(
            msg,
            ":warning: Wrong format~ Use <code>DD/MM</code> like <code>14/02</code> :heart:",
        )
        return

    day, month = parsed

    await db.upsert_user(target.id, {
        "first_name": target.first_name,
        "bday_day": day,
        "bday_month": month,
    })

    month_name = datetime(2000, month, 1).strftime("%B")

    if target.id == user.id:
        who = "Your"
        end = "I'll make sure to wish you on the day~ :heart: :flower:"
    else:
        who = _mention(target.id, target.first_name) + "'s"
        end = "I'll make sure to wish them on the day~ :heart: :flower:"

    await premium.reply(
        msg,
        f":cake: <b>Birthday saved~</b>\n\n"
        f"{who} birthday: <b>{day} {month_name}</b>\n\n"
        f"<i>{end}</i>",
        disable_web_page_preview=True,
    )


async def mybirthday_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = update.effective_message

    if not user or not msg:
        return

    data = await db.get_user(user.id) or {}
    day = data.get("bday_day")
    month = data.get("bday_month")

    if not day or not month:
        await premium.reply(
            msg,
            ":cake: No birthday saved yet~\n"
            "Use <code>/bday DD/MM</code> to save yours! :heart:",
        )
        return

    month_name = datetime(2000, month, 1).strftime("%B")
    today = date.today()

    try:
        bday = date(today.year, month, day)
    except ValueError:
        bday = date(today.year, month, 28)

    if bday < today:
        try:
            bday = date(today.year + 1, month, day)
        except ValueError:
            bday = date(today.year + 1, month, 28)

    days_left = (bday - today).days

    if days_left == 0:
        countdown = "Today is your day!! :sparkle: :heart:"
    elif days_left == 1:
        countdown = "Tomorrow!! Get ready~ :ribbon: :pinkheart:"
    else:
        countdown = f"In <b>{days_left} days</b> :pinkheart:"

    text = (
        ":cake: <b>Your Birthday~</b>\n\n"
        f"<blockquote>:calendar: Date: <b>{day} {month_name}</b>\n"
        f":clock: {countdown}</blockquote>\n\n"
        "<i>I'll be counting down~ :heart:</i>"
    )

    await premium.reply(msg, text, disable_web_page_preview=True)


async def upcoming_bdays_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message

    if not msg:
        return

    today = date.today()

    cursor = db.get_db().users.find(
        {"bday_day": {"$exists": True}, "bday_month": {"$exists": True}},
        {"user_id": 1, "first_name": 1, "bday_day": 1, "bday_month": 1},
    )
    users = [doc async for doc in cursor]

    upcoming = []

    for u in users:
        try:
            bd = date(today.year, u["bday_month"], u["bday_day"])
            if bd < today:
                bd = date(today.year + 1, u["bday_month"], u["bday_day"])
            upcoming.append((bd, u))
        except Exception:
            pass

    upcoming.sort(key=lambda x: x[0])
    upcoming = upcoming[:10]

    if not upcoming:
        await premium.reply(
            msg,
            ":cake: No birthdays saved yet~\nTell everyone to use /bday!! :heart:",
        )
        return

    lines = [":cake: <b>Upcoming Birthdays~</b>\n", "<blockquote>"]

    for bd, u in upcoming:
        days_left = (bd - today).days
        month_name = bd.strftime("%b")
        name = u.get("first_name", "Unknown")
        uid = u.get("user_id", 0)
        label = ":sparkle: TODAY" if days_left == 0 else f"in {days_left}d"
        mention = _mention(uid, name)

        lines.append(f":ribbon: {mention} — {bd.day} {month_name} ({label})")

    lines.append("")
    lines.append("</blockquote>")

    await premium.reply(
        msg,
        "\n".join(lines),
        disable_web_page_preview=True,
    )


async def birthday_job(context):
    today = date.today()

    try:
        cursor = db.get_db().users.find(
            {"bday_day": today.day, "bday_month": today.month},
            {"user_id": 1, "first_name": 1, "active_chats": 1},
        )
        users = [doc async for doc in cursor]

        for u in users:
            uid = u.get("user_id")
            name = u.get("first_name", "friend")

            wished_key = f"bday_wished_{uid}_{today.year}"
            doc = await db.get_db().settings.find_one({"key": wished_key})
            if doc:
                continue

            mention = _mention(uid, name)
            wish = random.choice(BDAY_WISHES).format(name=mention)

            sent = False

            for chat_id in (u.get("active_chats") or []):
                try:
                    await premium.send(
                        context.bot,
                        chat_id,
                        wish,
                        disable_web_page_preview=True,
                    )
                    sent = True
                    break
                except Exception as e:
                    log.debug("Birthday wish failed for chat %s: %s", chat_id, e)

            if sent:
                await db.get_db().settings.update_one(
                    {"key": wished_key},
                    {"$set": {"value": True}},
                    upsert=True,
                )
                log.info("Birthday wished %s (%s)", name, uid)

    except Exception as e:
        log.warning("Birthday job error: %s", e)


def register_birthday_job(app):
    app.job_queue.run_repeating(
        birthday_job,
        interval=3600,
        first=60,
        name="birthday_checker",
    )
    log.info("Birthday job registered every 1h")


bday_h = CommandHandler("bday", bday_cmd)
mybirthday_h = CommandHandler("mybirthday", mybirthday_cmd)
upcomingbdays_h = CommandHandler("upcomingbdays", upcoming_bdays_cmd)