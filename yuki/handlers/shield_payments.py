"""
Yuki Shield Payments
Copyright © Jass

Real-money (UPI) flow for /shield permanent — receives the payment
screenshot, forwards it to the owner with Approve/Reject buttons, and
activates the permanent shield on approval.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatType
from telegram.ext import CallbackQueryHandler, ContextTypes, MessageHandler, filters

from yuki.core import config
from yuki.database.economy import (
    get_pending_shield_payment,
    clear_pending_shield_payment,
    set_permanent_shield,
)
from yuki.utils.premium import render


async def handle_payment_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fires on any photo sent to Yuki in DM. If the sender has a pending
    /shield permanent request, forward the screenshot to the owner."""
    msg = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    if not msg or not msg.photo or not user or not chat or chat.type != ChatType.PRIVATE:
        return

    pending = get_pending_shield_payment(user.id)
    if not pending:
        return  # not waiting on a payment from this user — let other handlers run

    target_chat = config.LOG_GROUP_ID or config.OWNER_ID
    if not target_chat:
        await msg.reply_text("⚠️ Payment review isn't configured yet — ask the owner to set LOG_GROUP_ID or OWNER_ID.")
        return

    username_part = f" (@{user.username})" if user.username else ""
    caption = render(
        f":gift: <b>Permanent Shield payment request</b>\n\n"
        f":dot2: <b>From:</b> {user.first_name or 'friend'}{username_part}\n"
        f":id: <b>User ID:</b> <code>{user.id}</code>\n"
        f":dot2: <b>Amount:</b> ₹{config.PERMANENT_SHIELD_PRICE_INR}"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"shieldpay_ok:{user.id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"shieldpay_no:{user.id}"),
        ]
    ])

    try:
        await context.bot.send_photo(
            target_chat,
            photo=msg.photo[-1].file_id,
            caption=caption,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
    except Exception as exc:
        await msg.reply_text(f"⚠️ Couldn't send your screenshot to the owner — try again in a bit. ({exc})")
        return

    await msg.reply_text("🎁 Your request has been sent to the owner — sit tight, they'll check it soon~")


async def handle_shield_payment_decision(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Owner-only Approve/Reject buttons on the forwarded screenshot."""
    query = update.callback_query
    await query.answer()

    if not config.OWNER_ID or query.from_user.id != config.OWNER_ID:
        await query.answer("Owner only.", show_alert=True)
        return

    action, user_id_str = query.data.split(":", 1)
    target_user_id = int(user_id_str)

    if action == "shieldpay_ok":
        set_permanent_shield(target_user_id, True)
        clear_pending_shield_payment(target_user_id)
        try:
            await context.bot.send_message(
                target_user_id,
                render(":shield: <b>Permanent Shield protection is activated!</b> Your request has been approved~"),
                parse_mode="HTML",
            )
        except Exception:
            pass
        await query.edit_message_caption(caption=(query.message.caption or "") + "\n\n✅ Approved")
    else:
        clear_pending_shield_payment(target_user_id)
        try:
            await context.bot.send_message(
                target_user_id,
                render(":warning: Your payment couldn't be verified — please contact support if you think this is a mistake."),
                parse_mode="HTML",
            )
        except Exception:
            pass
        await query.edit_message_caption(caption=(query.message.caption or "") + "\n\n❌ Rejected")


SHIELD_PAYMENT_SCREENSHOT = MessageHandler(filters.PHOTO & filters.ChatType.PRIVATE, handle_payment_screenshot)
SHIELD_PAYMENT_DECISION = CallbackQueryHandler(handle_shield_payment_decision, pattern=r"^shieldpay_")
