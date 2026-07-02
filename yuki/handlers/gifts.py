"""
Yuki Bot - Gift System
Send cute gifts to other users with beautiful UI.
Premium emoji supported.
"""

import logging

from telegram import Update
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes

from yuki.core import database as db
from yuki.utils.keyboards import gift_keyboard, my_gifts_keyboard
from yuki.utils.helpers import mention_html
from yuki.utils import premium

log = logging.getLogger("yuki.handlers.gifts")

GIFTS = [
    {"name": "Ring", "id": "ring", "emoji": ":ring:", "desc": "A sparkling promise~"},
    {"name": "Bouquet", "id": "bouquet", "emoji": ":bouquet:", "desc": "Fresh flowers just for you!"},
    {"name": "Teddy", "id": "teddy", "emoji": ":teddy:", "desc": "Warm hugs anytime~"},
    {"name": "Rose", "id": "rose", "emoji": ":rose:", "desc": "A classic symbol of love"},
    {"name": "Cake", "id": "cake", "emoji": ":cake2:", "desc": "Sweet treats for you!"},
    {"name": "Ribbon", "id": "ribbon", "emoji": ":ribbon2:", "desc": "A surprise wrapped with love"},
    {"name": "Star", "id": "star", "emoji": ":star2:", "desc": "You're a star to me!"},
    {"name": "Song", "id": "song", "emoji": ":music:", "desc": "A melody just for you"},
    {"name": "Choco", "id": "choco", "emoji": ":choco:", "desc": "Sweet like you!"},
    {"name": "Lollipop", "id": "lolly", "emoji": ":lollipop:", "desc": "Life is sweet with you~"},
    {"name": "Crown", "id": "crown", "emoji": ":crown2:", "desc": "Because you're royalty~"},
    {"name": "Unicorn", "id": "unicorn", "emoji": ":unicorn:", "desc": "Magical just like you!"},
]

GIFT_MAP = {g["id"]: g for g in GIFTS}


def receiver_mention(receiver_id: int, label: str = "this cutie") -> str:
    return f'<a href="tg://user?id={receiver_id}">{label}</a>'


async def _send_receiver_dm(bot, receiver_id: int, sender_mention: str, gift: dict) -> bool:
    text = (
        f"{gift['emoji']} <b>You received a gift!</b>\n\n"
        "<blockquote>"
        f"{sender_mention} sent you <b>{gift['name']}</b>\n"
        f"{gift['desc']}"
        "</blockquote>\n\n"
        "<i>Open Yuki and check your profile with /me or /mygift :heart:</i>"
    )

    try:
        await premium.send(
            bot,
            receiver_id,
            text,
            disable_web_page_preview=True,
        )
        return True
    except Exception as e:
        log.debug("Gift receiver DM failed: %s", e)
        return False


async def gift_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    sender = update.effective_user

    if not msg or not sender:
        return

    target = None

    if msg.reply_to_message:
        target = msg.reply_to_message.from_user
    elif ctx.args:
        await premium.reply(
            msg,
            ":mail: <b>Reply to the person you want to gift!</b>\n\n"
            "Usage: Reply to their message and type <code>/gift</code>",
        )
        return

    if not target:
        await premium.reply(
            msg,
            ":gift: <b>Who should I gift?</b>\n\n"
            "Reply to someone's message and use <code>/gift</code>~",
        )
        return

    if target.id == sender.id:
        await premium.reply(
            msg,
            ":sad: You can't gift yourself silly~ gift someone else! :heart:",
        )
        return

    if target.is_bot:
        await premium.reply(
            msg,
            ":cute: Hehe bots don't need gifts~ choose a human bestie :heart:",
        )
        return

    text = (
        f":gift: <b>Choose a gift for {mention_html(target)}~</b>\n\n"
        "<blockquote>"
        "Pick something sweet and Yuki will deliver it beautifully."
        "</blockquote>\n\n"
        "<i>If their DM is closed, I'll tag them here too. :sparkle:</i>"
    )

    await premium.reply(
        msg,
        text,
        reply_markup=gift_keyboard(GIFTS, target.id, 1),
        disable_web_page_preview=True,
    )

    ctx.user_data["gift_sender"] = sender
    ctx.user_data["gift_target"] = target


async def gift_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    sender = update.effective_user
    chat = update.effective_chat

    if not query or not sender:
        return

    await query.answer()

    try:
        _, gift_id, receiver_id_raw = query.data.split(":")
        receiver_id = int(receiver_id_raw)
    except Exception:
        await query.answer("Invalid gift data.", show_alert=True)
        return

    gift = GIFT_MAP.get(gift_id)
    if not gift:
        await query.answer("Gift not found.", show_alert=True)
        return

    await db.send_gift(
        sender.id,
        receiver_id,
        gift["id"],
        gift["name"],
        gift["emoji"],
    )

    sender_mention = mention_html(sender)
    recv_mention = receiver_mention(receiver_id)

    dm_sent = await _send_receiver_dm(ctx.bot, receiver_id, sender_mention, gift)

    group_text = (
        f"{gift['emoji']} <b>Gift Delivered!</b>\n\n"
        "<blockquote>"
        f"{sender_mention} sent <b>{gift['name']}</b> to {recv_mention}.\n"
        f"{gift['desc']}"
        "</blockquote>\n\n"
    )

    if dm_sent:
        group_text += "<i>I also delivered it in their DM. :heart:</i>"
    else:
        group_text += (
            "<i>I couldn't DM them yet.</i>\n"
            "<i>They need to start me first, then check /mygift or /me. :flower:</i>"
        )

    try:
        await premium.edit(
            query,
            group_text,
            disable_web_page_preview=True,
        )
    except Exception as e:
        log.debug("Gift edit failed: %s", e)
        try:
            await premium.send(
                ctx.bot,
                chat.id,
                group_text,
                disable_web_page_preview=True,
            )
        except Exception:
            pass

    if not dm_sent and chat and chat.type != "private":
        try:
            await premium.send(
                ctx.bot,
                chat.id,
                f":mail: {recv_mention}, you got a <b>{gift['name']}</b> from {sender_mention}!\n\n"
                f"<blockquote>{gift['desc']}</blockquote>\n\n"
                "<i>Start me in DM and use /mygift or /me to see your gift box. :heart:</i>",
                disable_web_page_preview=True,
            )
        except Exception as e:
            log.debug("Gift group mention failed: %s", e)


async def my_gifts_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = update.effective_message

    if not user or not msg:
        return

    gifts = await db.get_user_gifts(user.id)

    if not gifts:
        await premium.reply(
            msg,
            ":gift: <b>Your Gift Box is Empty~</b>\n\n"
            "<i>No gifts yet! Maybe drop a hint? :cute:</i>",
            reply_markup=my_gifts_keyboard(),
        )
        return

    GIFT_PREMIUM = {
        "Ring": ":ring:",
        "Bouquet": ":bouquet:",
        "Teddy": ":teddy:",
        "Teddy Bear": ":teddy:",
        "Rose": ":rose:",
        "Cake": ":cake2:",
        "Ribbon": ":ribbon2:",
        "Star": ":star2:",
        "Song": ":music:",
        "Choco": ":choco:",
        "Lollipop": ":lollipop:",
        "Crown": ":crown2:",
        "Unicorn": ":unicorn:",
    }

    lines = []

    for g in gifts[:15]:
        gift_name = g.get("gift_name") or g.get("name") or "Gift"
        emoji = GIFT_PREMIUM.get(gift_name, ":gift:")
        lines.append(f"{emoji} <b>{gift_name}</b>")

    gift_list = "\n".join(lines)

    text = (
        ":ribbon: <b>Your Gift Collection</b>\n\n"
        f"<blockquote>{gift_list}</blockquote>\n\n"
        f":gift: <b>Total Gifts:</b> <code>{len(gifts)}</code>"
    )

    await premium.reply(
        msg,
        text,
        reply_markup=my_gifts_keyboard(),
        disable_web_page_preview=True,
    )

async def cancel_gift(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if not query:
        return

    await query.answer("Cancelled")

    try:
        await query.delete_message()
    except Exception:
        pass


async def gift_page_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if not query:
        return

    await query.answer()

    try:
        _, page_raw, target_id_raw = query.data.split(":")
        page = int(page_raw)
        target_id = int(target_id_raw)
    except Exception:
        await query.answer("Invalid page.", show_alert=True)
        return

    text = query.message.caption or query.message.text or ":gift: <b>Choose a gift~</b>"

    try:
        await premium.edit_caption(
            query,
            text,
            reply_markup=gift_keyboard(GIFTS, target_id, page),
        )
        return
    except Exception:
        pass

    try:
        await premium.edit(
            query,
            text,
            reply_markup=gift_keyboard(GIFTS, target_id, page),
            disable_web_page_preview=True,
        )
    except Exception as e:
        log.debug("Gift page edit failed: %s", e)


gift_page_cb_handler = CallbackQueryHandler(gift_page_callback, pattern=r"^giftpage:\d+:\d+$")
gift_cmd_handler = CommandHandler("gift", gift_cmd)
mygift_cmd_handler = CommandHandler("mygift", my_gifts_cmd)
gift_cb_handler = CallbackQueryHandler(gift_callback, pattern=r"^gift:[^:]+:\d+$")
cancel_gift_handler = CallbackQueryHandler(cancel_gift, pattern="^cancel_gift$")