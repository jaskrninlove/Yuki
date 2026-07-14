"""
Yuki Marriage - Propose
Copyright © Jass
"""

from datetime import datetime, timedelta, timezone

from telegram import Update
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes

from yuki.database.marriage import is_married, create_marriage
from yuki.utils.premium import reply, edit
from yuki.utils.keyboards import propose_keyboard

PROPOSAL_EXPIRY = 5 * 60  # 5 minutes

_pending: dict[int, dict] = {}  # target_id -> {"from": proposer_id, "expires": datetime}


def _cleanup_expired():
    now = datetime.now(timezone.utc)
    expired = [uid for uid, p in _pending.items() if p["expires"] < now]
    for uid in expired:
        _pending.pop(uid, None)


async def propose_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    sender = update.effective_user

    if not message.reply_to_message:
        return await reply(
            message,
            """
:ring: <b>Propose to Someone~</b>

Reply to their message and use <code>/propose</code>
""",
        )

    target = message.reply_to_message.from_user

    if target.id == sender.id:
        return await reply(message, ":warning: You can't propose to yourself silly~")

    if target.is_bot:
        return await reply(message, ":warning: Yuki says bots can't fall in love (yet~)")

    if is_married(sender.id):
        return await reply(message, ":warning: You're already married~ Use /divorce first.")

    if is_married(target.id):
        return await reply(message, f":warning: {target.full_name} is already married to someone else~")

    _cleanup_expired()

    if target.id in _pending:
        return await reply(message, f":warning: {target.full_name} already has a pending proposal~")

    _pending[target.id] = {
        "from": sender.id,
        "expires": datetime.now(timezone.utc) + timedelta(seconds=PROPOSAL_EXPIRY),
    }

    await reply(
        message,
        f"""
:ring: <b>A Proposal!</b>

<b>{sender.full_name}</b> is down on one knee for <b>{target.full_name}</b>~

<blockquote>Will you accept this promise? 💍</blockquote>

<i>{target.full_name}, the choice is yours~</i>
""",
        reply_markup=propose_keyboard(sender.id, target.id),
    )


async def propose_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    clicker = update.effective_user

    await query.answer()

    action, proposer_id, target_id = query.data.split(":")
    proposer_id, target_id = int(proposer_id), int(target_id)

    if clicker.id != target_id:
        await query.answer("This isn't your proposal to answer~", show_alert=True)
        return

    _cleanup_expired()
    pending = _pending.get(target_id)

    if not pending or pending["from"] != proposer_id:
        await edit(query, ":warning: This proposal has expired~", reply_markup=None)
        return

    _pending.pop(target_id, None)

    if action == "marry_reject":
        await edit(
            query,
            ":broken_heart: <b>Proposal Declined</b>\n\n<i>Maybe next time~</i>",
            reply_markup=None,
        )
        return

    if is_married(proposer_id) or is_married(target_id):
        await edit(
            query,
            ":warning: One of you got married to someone else already~",
            reply_markup=None,
        )
        return

    success = create_marriage(proposer_id, target_id)

    if not success:
        await edit(query, ":warning: Something went wrong, please try again~", reply_markup=None)
        return

    from yuki.database.achievements import award_marriage
    award_marriage(proposer_id)
    award_marriage(target_id)

    await edit(
        query,
        """
:tada: <b>Congratulations!</b>

You two are now married~ 💍💕

<i>Use /couple to see your relationship profile.</i>
""",
        reply_markup=None,
    )


PROPOSE = CommandHandler("propose", propose_cmd)
PROPOSE_CB = CallbackQueryHandler(propose_callback, pattern=r"^marry_(accept|reject):\d+:\d+$")