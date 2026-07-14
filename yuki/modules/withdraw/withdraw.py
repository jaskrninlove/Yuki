"""
Yuki Withdraw
Copyright © Jass
"""

from telegram import Update, ForceReply
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from yuki.core import config
from yuki.database.economy import get as get_economy, remove_withdraw
from yuki.database.withdrawals import (
    eligible_tiers,
    create_request,
    get_request,
    set_status,
    has_pending_request,
)
from yuki.utils.premium import reply, edit, send
from yuki.utils.keyboards import withdraw_tiers_keyboard, withdraw_admin_keyboard
from yuki.utils.helpers import full_name, mention_html


# ==========================================================
# /withdraw
# ==========================================================

async def withdraw_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user

    if update.effective_chat.type != "private":
        return await reply(message, ":warning: Please use /withdraw in my DM~")

    if has_pending_request(user.id):
        return await reply(
            message,
            ":clock: You already have a pending withdrawal request. Please wait for it to be resolved~",
        )

    eco = get_economy(user.id)
    balance = eco.get("withdraw_balance", 0)

    tiers = eligible_tiers(balance)

    if not tiers:
        return await reply(
            message,
            f"""
:warning: <b>Not Enough Points</b>

Your withdrawable balance: <code>{balance:,}</code> pts

Keep earning through daily streaks, kills, robs, and referrals!
""",
        )

    await reply(
        message,
        f"""
:gem: <b>Withdraw Rewards</b>

Your withdrawable balance: <code>{balance:,}</code> pts

Choose a reward tier below~
""",
        reply_markup=withdraw_tiers_keyboard(tiers),
    )


async def withdraw_tier_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = update.effective_user
    await query.answer()

    cost = int(query.data.split(":")[1])

    eco = get_economy(user.id)
    balance = eco.get("withdraw_balance", 0)

    if balance < cost:
        await edit(query, ":warning: Your balance changed, this tier is no longer available~", reply_markup=None)
        return

    context.user_data["withdraw_pending_cost"] = cost

    await edit(query, ":pencil: <b>Almost done!</b>\n\nSend your UPI ID / Telegram contact below so we can reach you.", reply_markup=None)

    await context.bot.send_message(
        chat_id=user.id,
        text="Reply with your UPI ID / contact info:",
        reply_markup=ForceReply(selective=True),
    )


async def withdraw_contact_capture(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user

    cost = context.user_data.get("withdraw_pending_cost")
    if not cost:
        return  # not in a withdraw flow, let other handlers process this message

    if not message.reply_to_message or "Reply with your UPI ID" not in (message.reply_to_message.text or ""):
        return

    context.user_data.pop("withdraw_pending_cost", None)

    eco = get_economy(user.id)
    balance = eco.get("withdraw_balance", 0)

    if balance < cost:
        await reply(message, ":warning: Your balance changed, this tier is no longer available~")
        return

    from yuki.database.withdrawals import REWARD_TIERS
    label = next((l for c, l in REWARD_TIERS if c == cost), "Reward")

    contact = message.text.strip()[:200]
    req_id = create_request(user.id, cost, label, contact)

    await reply(
        message,
        f"""
:success: <b>Request Submitted!</b>

:id: Request ID: <code>{req_id}</code>
:gift: Reward: <b>{label}</b>
:gem: Cost: <code>{cost:,}</code> pts

We'll review it soon. You'll be notified here once it's resolved~
""",
    )

    if config.LOG_GROUP_ID:
        try:
            await send(
                context.bot,
                config.LOG_GROUP_ID,
                f"""
:money: <b>New Withdrawal Request</b>

:id: Request ID: <code>{req_id}</code>
:user: User: {mention_html(user)} (<code>{user.id}</code>)
:gift: Reward: <b>{label}</b>
:gem: Cost: <code>{cost:,}</code> pts
:mail: Contact: <code>{contact}</code>
""",
                reply_markup=withdraw_admin_keyboard(req_id),
                disable_web_page_preview=True,
            )
        except Exception:
            pass


# ==========================================================
# Admin approve / reject
# ==========================================================

async def withdraw_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    admin = update.effective_user
    await query.answer()

    if admin.id != config.OWNER_ID:
        await query.answer("Owner only.", show_alert=True)
        return

    action, req_id_raw = query.data.split(":")
    req_id = int(req_id_raw)

    req = get_request(req_id)
    if not req:
        await edit(query, ":warning: Request not found~", reply_markup=None)
        return

    if req["status"] != "pending":
        await edit(query, f":warning: This request was already {req['status']}~", reply_markup=None)
        return

    if action == "wd_approve":
        success = remove_withdraw(req["user_id"], req["tier_cost"])

        if not success:
            await edit(query, ":warning: User no longer has enough balance for this~", reply_markup=None)
            set_status(req_id, "rejected")
            return

        set_status(req_id, "approved")

        await edit(
            query,
            f":success: <b>Approved</b>\n\nRequest <code>{req_id}</code> — {req['tier_label']}",
            reply_markup=None,
        )

        try:
            await send(
                context.bot,
                req["user_id"],
                f"""
:tada: <b>Withdrawal Approved!</b>

:gift: Reward: <b>{req['tier_label']}</b>
:id: Request ID: <code>{req_id}</code>

We'll be in touch shortly to deliver your reward~
""",
            )
        except Exception:
            pass

    elif action == "wd_reject":
        set_status(req_id, "rejected")

        await edit(
            query,
            f":warning: <b>Rejected</b>\n\nRequest <code>{req_id}</code> — {req['tier_label']}",
            reply_markup=None,
        )

        try:
            await send(
                context.bot,
                req["user_id"],
                f"""
:warning: <b>Withdrawal Rejected</b>

:id: Request ID: <code>{req_id}</code>

Contact support if you believe this is a mistake.
""",
            )
        except Exception:
            pass


# ==========================================================
# Handlers
# ==========================================================

WITHDRAW = CommandHandler("withdraw", withdraw_cmd)
WITHDRAW_TIER_CB = CallbackQueryHandler(withdraw_tier_pick, pattern=r"^wd_pick:\d+$")
WITHDRAW_CONTACT_CAPTURE = MessageHandler(
    filters.TEXT & filters.REPLY & filters.ChatType.PRIVATE,
    withdraw_contact_capture,
)
WITHDRAW_ADMIN_CB = CallbackQueryHandler(withdraw_admin_callback, pattern=r"^wd_(approve|reject):\d+$")