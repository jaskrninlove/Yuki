"""
Yuki Shield
Copyright © Jass
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

from yuki.core import config
from yuki.database.economy import (
    get,
    remove,
    set_shield,
    has_shield,
    has_permanent_shield,
    shield_remaining,
    set_pending_shield_payment,
)

from yuki.utils import premium
from yuki.utils.premium import reply
from yuki.utils.rewards import SHIELD_COST, SHIELD_DURATION


def _fmt(seconds: int) -> str:
    h, rem = divmod(seconds, 3600)
    m, _ = divmod(rem, 60)
    if h:
        return f"{h}h {m}m"
    return f"{m}m"


def _shop_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"4-Hour Shield — {SHIELD_COST} coins", callback_data="yshield_temp")],
        [InlineKeyboardButton(f"Permanent Shield — ₹{config.PERMANENT_SHIELD_PRICE_INR}", callback_data="yshield_perm")],
    ])


async def shield_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/shield — opens Yuki's Protection Shop with two buttons, same
    layout style as Kai's shop."""
    message = update.effective_message
    user = update.effective_user

    if has_permanent_shield(user.id):
        return await reply(
            message,
            """
:shield: <b>Already Permanently Protected!</b>

No one can ever touch you~ 🌸
""",
        )

    if has_shield(user.id):
        remaining = shield_remaining(user.id)
        if remaining:
            return await reply(
                message,
                f"""
:shield: <b>Already Protected!</b>

Your shield is still active for <code>{_fmt(remaining)}</code>.
""",
            )

    text = f"""
:shield: <b>Yuki's Protection Shop</b>

Pick how you'd like to stay protected from kills & robs~ 🌸

:dot2: <b>4-Hour Shield</b> — {SHIELD_COST} coins (from your wallet)
:dot2: <b>Permanent Shield</b> — ₹{config.PERMANENT_SHIELD_PRICE_INR} (real payment, one-time, forever)
"""
    await reply(message, text, reply_markup=_shop_keyboard())


async def shield_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the two shop buttons: yshield_temp / yshield_perm."""
    query = update.callback_query
    await query.answer()
    user = query.from_user

    if has_permanent_shield(user.id):
        return await premium.edit(query, ":shield: You already have a permanent shield — you're covered forever~ 🌸")

    if query.data == "yshield_temp":
        if has_shield(user.id):
            remaining = shield_remaining(user.id)
            if remaining:
                return await premium.edit(query, f":shield: You're already protected for <code>{_fmt(remaining)}</code> more.")

        eco = get(user.id)
        if eco["balance"] < SHIELD_COST:
            return await premium.edit(
                query,
                f":warning: You need <code>{SHIELD_COST}</code> coins for a shield. You have <code>{eco['balance']:,}</code>.",
            )

        remove(user.id, SHIELD_COST)
        until = datetime.now(timezone.utc) + timedelta(seconds=SHIELD_DURATION)
        set_shield(user.id, until)

        await premium.edit(
            query,
            f"""
:shield: <b>Shield Activated!</b>

You're protected from both <code>/kill</code> and <code>/rob</code> for <code>{_fmt(SHIELD_DURATION)}</code>~

:gold: <code>-{SHIELD_COST}</code> coins spent
""",
        )
        return

    if query.data == "yshield_perm":
        set_pending_shield_payment(user.id, user.first_name or "friend", user.username)

        text = f"""
:shield: <b>Permanent Shield — ₹{config.PERMANENT_SHIELD_PRICE_INR}</b>

Pay <code>₹{config.PERMANENT_SHIELD_PRICE_INR}</code> to:
:dot2: UPI ID: <code>{config.UPI_ID or 'not set — ask the owner'}</code>

Once paid, send a screenshot of the payment right here 📸 — Yuki will pass it
straight to the owner for a quick check~
"""
        if config.UPI_QR_IMAGE:
            qr_path = Path(config.UPI_QR_IMAGE)
            try:
                if qr_path.is_file():
                    with open(qr_path, "rb") as qr_file:
                        await query.message.reply_photo(photo=qr_file, caption=text, parse_mode="HTML")
                else:
                    await query.message.reply_photo(photo=config.UPI_QR_IMAGE, caption=text, parse_mode="HTML")
                return
            except Exception:
                pass

        await query.message.reply_text(text, parse_mode="HTML")


SHIELD = CommandHandler("shield", shield_cmd)
SHIELD_CB = CallbackQueryHandler(shield_callback, pattern=r"^yshield_")
