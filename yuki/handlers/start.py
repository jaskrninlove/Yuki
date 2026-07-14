"""
Yuki Bot - Start Handler
Beautiful start message with inline keyboard.
"""

import logging
from datetime import datetime

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from yuki.core.config import START_IMAGE, LOG_GROUP_ID
from yuki.utils.locale import get
from yuki.utils.keyboards import start_keyboard
from yuki.utils.helpers import ensure_user, full_name
from yuki.utils import premium
from yuki.core import database as db
from yuki.core.database import get_user
from yuki.database.referral import record_referral, milestone_reward, get_referral_count
from yuki.database.economy import add_withdraw

log = logging.getLogger("yuki.handlers.start")

START_TIME = datetime.now()


def get_uptime() -> str:
    delta = datetime.now() - START_TIME
    total = int(delta.total_seconds())

    hours = total // 3600
    minutes = (total % 3600) // 60
    seconds = total % 60

    return f"{hours}h:{minutes}m:{seconds}s"


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    msg = update.effective_message

    if not user or not chat or not msg:
        return
    
    is_new_user = (await get_user(user.id)) is None

    if is_new_user and chat.type == "private" and ctx.args:
        payload = ctx.args[0]
        if payload.startswith("ref_"):
            try:
                referrer_id = int(payload[4:])
            except ValueError:
                referrer_id = None

            if referrer_id:
                old_count = get_referral_count(referrer_id)
                recorded = record_referral(referrer_id, user.id)

                if recorded:
                    new_count = old_count + 1
                    
                    from yuki.database.achievements import check_referral_milestones
                    check_referral_milestones(referrer_id, new_count)

                    bonus = milestone_reward(old_count, new_count)

                    if bonus:
                        add_withdraw(referrer_id, bonus)
                        try:
                            await premium.send(
                                ctx.bot,
                                referrer_id,
                                f":tada: <b>Referral Milestone!</b>\n\n"
                                f"You've referred <code>{new_count}</code> friends!\n"
                                f":gift: <code>+${bonus}</code> added to your withdrawable balance~",
                            )
                        except Exception:
                            pass

    await ensure_user(user)

    is_group = chat.type != "private"

    caption = get("start.caption", name=full_name(user))

    # Group Start
    if is_group:
        caption = (
            ":bot: <b>Yuki is online.</b>\n\n"
            "<blockquote>"
            f":clock: <b>Uptime:</b> <code>{get_uptime()}</code>\n"
            ":success: <b>Status:</b> Ready"
            "</blockquote>"
        )

    markup = start_keyboard(is_group=is_group)

    # Send start message
    try:
        await premium.reply_photo(
            msg,
            photo=START_IMAGE,
            caption=caption,
            reply_markup=markup,
        )
    except Exception as e:
        log.debug("Start photo failed, using text fallback: %s", e)

        await premium.reply(
            msg,
            caption,
            reply_markup=markup,
            disable_web_page_preview=True,
        )

    log.info(
        "Start — user %s (%s) in %s",
        user.id,
        full_name(user),
        chat.id,
    )

    # ─────────────────────────────────────────────
    # Logger (Private Start)
    # ─────────────────────────────────────────────
    if chat.type == "private" and LOG_GROUP_ID:
        try:
            is_premium = getattr(user, "is_premium", False)

            # These functions should exist in database.py
            total_users = await db.count_users()
            total_groups = await db.count_groups()

            logger_text = (
                ":heart: <b>New User Started Yuki</b>\n\n"
                "<blockquote>"
                f":user: <b>Name:</b> {full_name(user)}\n"
                f":id: <b>User ID:</b> <code>{user.id}</code>\n"
                f":mail: <b>Username:</b> @{user.username or 'None'}\n"
                f":gold: <b>Premium:</b> {'Yes' if is_premium else 'No'}\n"
                f":settings: <b>Language:</b> {user.language_code or 'Unknown'}\n"
                f":chat: <b>Started In:</b> Private\n"
                f":users: <b>Total Users:</b> <code>{total_users:,}</code>\n"
                f":group: <b>Total Groups:</b> <code>{total_groups:,}</code>\n"
                f":clock: <b>Time:</b> <code>{datetime.now().strftime('%d %b %Y • %H:%M')}</code>"
                "</blockquote>"
            )

            await premium.send(
                ctx.bot,
                LOG_GROUP_ID,
                logger_text,
                disable_web_page_preview=True,
            )

        except Exception as e:
            log.warning("Failed to send PM start log: %s", e)


handler = CommandHandler("start", start)