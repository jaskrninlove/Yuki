"""
Yuki Marriage - Divorce
Copyright © Jass
"""

from telegram import Update
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes

from yuki.database.marriage import is_married, get_partner_id, divorce as do_divorce
from yuki.utils.premium import reply, edit
from yuki.utils.keyboards import divorce_confirm_keyboard


async def divorce_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user

    if not is_married(user.id):
        return await reply(message, ":warning: You're not married to anyone~")

    await reply(
        message,
        """
:broken_heart: <b>Are You Sure?</b>

This will end your marriage and reset your love points.
This action cannot be undone.
""",
        reply_markup=divorce_confirm_keyboard(user.id),
    )


async def divorce_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    clicker = update.effective_user

    await query.answer()

    _, requester_id = query.data.split(":")
    requester_id = int(requester_id)

    if clicker.id != requester_id:
        await query.answer("This isn't your confirmation~", show_alert=True)
        return

    if not is_married(requester_id):
        await edit(query, ":warning: You're not married to anyone~", reply_markup=None)
        return

    partner_id = get_partner_id(requester_id)
    do_divorce(requester_id)

    try:
        partner = await context.bot.get_chat(partner_id)
        partner_name = partner.full_name
    except Exception:
        partner_name = "your ex-partner"

    await edit(
        query,
        f":broken_heart: <b>Divorced</b>\n\nYou and {partner_name} have gone your separate ways.",
        reply_markup=None,
    )


DIVORCE = CommandHandler("divorce", divorce_cmd)
DIVORCE_CB = CallbackQueryHandler(divorce_callback, pattern=r"^divorce_confirm:\d+$")