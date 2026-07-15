"""
Yuki Bot - Owner, Admin & Moderation Commands
Premium emoji supported.
"""

import asyncio
import html
import logging
from datetime import datetime, timedelta
from pathlib import Path

from telegram import Update, ChatPermissions, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes

from yuki.core import config, database as db
from yuki.core.config import UPDATES_CHANNEL, SUPPORT_LINK
from yuki.utils.locale import get
from yuki.utils.keyboards import (
    stats_keyboard,
    active_keyboard,
    profile_keyboard,
    maintenance_keyboard,
    owner_keyboard,
    pbtn,
)
from yuki.utils.helpers import (
    owner_only,
    admin_only,
    ensure_user,
    full_name,
    mention_html,
)
from yuki.utils import premium

log = logging.getLogger("yuki.handlers.admin")
LOG_FILE = Path("logs/yuki.log")


def updates_keyboard():
    return InlineKeyboardMarkup([
        [
            pbtn("Updates", url=UPDATES_CHANNEL, style="primary"),
            pbtn("Support", url=SUPPORT_LINK, style="success"),
        ]
    ])


def _target_from_reply_or_args(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message

    if msg.reply_to_message and msg.reply_to_message.from_user:
        return msg.reply_to_message.from_user

    if ctx.args:
        raw = ctx.args[0]
        if raw.isdigit():
            class Target:
                id = int(raw)
                full_name = raw
                first_name = raw
                username = None
            return Target()

    return None


async def _save_chat_prefix(chat_id: int, prefix: str):
    await db.get_db().chat_settings.update_one(
        {"chat_id": chat_id},
        {"$set": {"prefix": prefix}, "$setOnInsert": {"chat_id": chat_id}},
        upsert=True,
    )


async def _announce_maintenance(bot, enabled: bool):
    if enabled:
        text = (
            ":settings: <b>Yuki Maintenance Mode</b>\n\n"
            "<blockquote>"
            "Yuki is taking a tiny beauty nap for improvements.\n"
            "Some features may pause for a little while."
            "</blockquote>\n\n"
            "<i>I’ll be back soon, cuter and smoother than before. :heart:</i>"
        )
    else:
        text = (
            ":success: <b>Yuki is back online!</b>\n\n"
            "<blockquote>"
            "Maintenance is complete and all systems are ready again.\n"
            "Thank you for waiting so patiently."
            "</blockquote>\n\n"
            "<i>Let’s make the chat alive again. :flower:</i>"
        )

    users = await db.get_all_users()
    groups_cursor = db.get_db().groups.find({"active": True}, {"chat_id": 1})
    groups = [g["chat_id"] async for g in groups_cursor if g.get("chat_id")]

    sent = 0
    failed = 0

    for chat_id in groups + users:
        try:
            await premium.send(
                bot,
                chat_id,
                text,
                reply_markup=updates_keyboard(),
                disable_web_page_preview=True,
            )
            sent += 1
            await asyncio.sleep(0.04)
        except Exception:
            failed += 1

    return sent, failed


async def stats_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await _send_stats(update, ctx, edit=False)


async def stats_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
    await _send_stats(update, ctx, edit=True)


async def _send_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE, edit: bool):
    users = int(await db.count_users())
    groups = int(await db.count_groups())
    messages = int(await db.count_messages_today())
    gifts = int(await db.count_all_gifts())
    stickers = int(await db.count_stickers())

    text = get(
        "stats.response",
        users=users,
        groups=groups,
        messages=messages,
        gifts=gifts,
        stickers=stickers,
    )

    markup = stats_keyboard()

    if edit and update.callback_query:
        try:
            await premium.edit(update.callback_query, text, reply_markup=markup)
            return
        except Exception as e:
            log.debug("Stats edit failed: %s", e)

    await premium.reply(
        update.effective_message,
        text,
        reply_markup=markup,
        disable_web_page_preview=True,
    )


@admin_only
async def active_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    msg = update.effective_message

    if not chat or not msg:
        return

    if chat.type == "private":
        await premium.reply(msg, ":users: This works in groups only.")
        return

    members = await db.get_active_users(chat.id, limit=15)

    if not members:
        await premium.reply(
            msg,
            ":clock: <b>No active users yet.</b>\n\n"
            "<i>Start chatting to appear here.</i>",
        )
        return

    lines = []
    for i, m in enumerate(members, 1):
        name = html.escape(str(m.get("first_name") or m.get("username") or "Unknown"))
        msgs = int(m.get("total_messages", 0))
        uid = m.get("user_id")
        medal = ":gold:" if i == 1 else ":silver:" if i == 2 else ":bronze:" if i == 3 else f"<b>{i}.</b>"

        if uid:
            lines.append(f"{medal} <a href='tg://user?id={uid}'>{name}</a> — <code>{msgs}</code> msgs")
        else:
            lines.append(f"{medal} {name} — <code>{msgs}</code> msgs")

    text = get(
        "active.response",
        group=html.escape(chat.title or "this group"),
        user_list="\n".join(lines),
        count=len(members),
    )

    await premium.reply(
        msg,
        text,
        reply_markup=active_keyboard(),
        disable_web_page_preview=True,
    )


@admin_only
async def ban_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat = update.effective_chat
    target = _target_from_reply_or_args(update, ctx)

    if not target:
        await premium.reply(msg, ":reply: Reply to a user or use <code>/ban user_id</code>")
        return

    try:
        await ctx.bot.ban_chat_member(chat.id, target.id)
        await premium.reply(msg, f":warning: Banned {mention_html(target)}", disable_web_page_preview=True)
    except Exception as e:
        await premium.reply(msg, f":warning: Failed to ban: <code>{html.escape(str(e))}</code>")


@admin_only
async def unban_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat = update.effective_chat
    target = _target_from_reply_or_args(update, ctx)

    if not target:
        await premium.reply(msg, ":reply: Reply to a user or use <code>/unban user_id</code>")
        return

    try:
        await ctx.bot.unban_chat_member(chat.id, target.id, only_if_banned=True)
        await premium.reply(msg, f":success: Unbanned <code>{target.id}</code>")
    except Exception as e:
        await premium.reply(msg, f":warning: Failed to unban: <code>{html.escape(str(e))}</code>")


@admin_only
async def mute_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat = update.effective_chat
    target = _target_from_reply_or_args(update, ctx)

    if not target:
        await premium.reply(msg, ":reply: Reply to a user or use <code>/mute user_id</code>")
        return

    until = datetime.utcnow() + timedelta(days=365)

    try:
        await ctx.bot.restrict_chat_member(
            chat.id,
            target.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until,
        )
        await premium.reply(msg, f":warning: Muted {mention_html(target)}", disable_web_page_preview=True)
    except Exception as e:
        await premium.reply(msg, f":warning: Failed to mute: <code>{html.escape(str(e))}</code>")


@admin_only
async def unmute_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat = update.effective_chat
    target = _target_from_reply_or_args(update, ctx)

    if not target:
        await premium.reply(msg, ":reply: Reply to a user or use <code>/unmute user_id</code>")
        return

    try:
        await ctx.bot.restrict_chat_member(
            chat.id,
            target.id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_audios=True,
                can_send_documents=True,
                can_send_photos=True,
                can_send_videos=True,
                can_send_video_notes=True,
                can_send_voice_notes=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
                can_change_info=False,
                can_invite_users=True,
                can_pin_messages=False,
                can_manage_topics=False,
            ),
        )
        await premium.reply(msg, f":success: Unmuted {mention_html(target)}", disable_web_page_preview=True)
    except Exception as e:
        await premium.reply(msg, f":warning: Failed to unmute: <code>{html.escape(str(e))}</code>")


@admin_only
async def setprefix_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat = update.effective_chat

    if not chat or chat.type == "private":
        await premium.reply(msg, ":users: This command works in groups only.")
        return

    if not ctx.args:
        await premium.reply(msg, "Usage: <code>/setprefix !</code>")
        return

    prefix = ctx.args[0].strip()[:5]
    await _save_chat_prefix(chat.id, prefix)

    await premium.reply(
        msg,
        f":success: Prefix saved for this group: <code>{html.escape(prefix)}</code>\n\n"
        "<i>Note: slash commands still work normally.</i>",
    )


@owner_only
async def logs_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message

    if not LOG_FILE.exists():
        await premium.reply(msg, "No log file found.")
        return

    lines = LOG_FILE.read_text(encoding="utf-8", errors="ignore").splitlines()
    tail = "\n".join(lines[-35:]) or "No logs."

    if len(tail) > 3500:
        tail = tail[-3500:]

    await premium.reply(
        msg,
        f":book: <b>Recent Logs</b>\n\n<pre>{html.escape(tail)}</pre>",
    )


@admin_only
async def groupstats_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat = update.effective_chat

    if not chat or chat.type == "private":
        await premium.reply(msg, ":users: This command works in groups only.")
        return

    try:
        member_count = await ctx.bot.get_chat_member_count(chat.id)
    except Exception:
        member_count = "—"

    message_count = await db.get_db().messages.count_documents({"chat_id": chat.id})
    active_count = await db.get_db().users.count_documents({"active_chats": chat.id})
    top_users = await db.get_active_users(chat.id, limit=5)

    lines = []
    for i, user_doc in enumerate(top_users, 1):
        name = html.escape(user_doc.get("first_name") or user_doc.get("username") or "Unknown")
        msgs = int(user_doc.get("total_messages", 0))
        lines.append(f"{i}. {name} — <b>{msgs}</b> msgs")

    text = (
        ":chart: <b>Group Stats</b>\n\n"
        "<blockquote>"
        f":users: Members: <b>{member_count}</b>\n"
        f":chat: Logged Messages: <b>{message_count}</b>\n"
        f":star: Active Users: <b>{active_count}</b>"
        "</blockquote>\n\n"
        "<b>Top Users</b>\n"
        f"{chr(10).join(lines) if lines else 'No active users yet.'}"
    )

    await premium.reply(msg, text, disable_web_page_preview=True)


@admin_only
async def resetdata_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat = update.effective_chat
    user = update.effective_user

    if ctx.args and ctx.args[0].lower() == "all":
        if not user or user.id != config.OWNER_ID:
            await premium.reply(msg, ":crown: Owner only for global reset.")
            return

        await db.get_db().messages.delete_many({})
        await db.get_db().users.update_many({}, {"$set": {"total_messages": 0, "xp": 0, "rank_score": 0}})
        await premium.reply(msg, ":success: Global ranking/message data reset.")
        return

    if not chat or chat.type == "private":
        await premium.reply(msg, "Use this in a group or use <code>/resetdata all</code> as owner.")
        return

    await db.get_db().messages.delete_many({"chat_id": chat.id})
    await db.get_db().users.update_many(
        {"active_chats": chat.id},
        {
            "$pull": {"active_chats": chat.id},
            "$set": {"total_messages": 0, "xp": 0, "rank_score": 0},
        },
    )

    await premium.reply(msg, ":success: This group’s activity/ranking data has been reset.")


@owner_only
async def _broadcast_targets(mode: str):
    users = []
    groups = []

    if mode in ("users", "both"):
        users = await db.get_all_users()

    if mode in ("groups", "both"):
        groups_cursor = db.get_db().groups.find({"active": True}, {"chat_id": 1})
        groups = [g["chat_id"] async for g in groups_cursor if g.get("chat_id")]

    return users, groups


async def _copy_to(bot, chat_id: int, source_chat_id: int, message_id: int, reply_markup):
    from telegram.error import RetryAfter, Forbidden, BadRequest, TelegramError

    try:
        await bot.copy_message(
            chat_id=chat_id,
            from_chat_id=source_chat_id,
            message_id=message_id,
            reply_markup=reply_markup,
        )
        return "ok"

    except RetryAfter as e:
        await asyncio.sleep(e.retry_after + 1)
        return await _copy_to(bot, chat_id, source_chat_id, message_id, reply_markup)

    except Forbidden:
        return "blocked"

    except BadRequest as e:
        msg_text = str(e).lower()
        if "chat not found" in msg_text or "peer_id_invalid" in msg_text:
            return "deleted"
        return "error"

    except TelegramError:
        return "error"

    except Exception:
        return "error"


@owner_only
async def broadcast_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message

    if not msg:
        return

    if not msg.reply_to_message:
        await premium.reply(
            msg,
            ":signal: <b>Broadcast Usage</b>\n\n"
            "<blockquote>"
            "Reply to any message with:\n\n"
            "<code>/broadcast users</code>\n"
            "<code>/broadcast groups</code>\n"
            "<code>/broadcast both</code>\n\n"
            "Supports text, photos, videos, documents, stickers, "
            "audio, voice notes, captions and inline buttons — "
            "original formatting is fully preserved."
            "</blockquote>",
        )
        return

    mode = "both"
    if ctx.args:
        mode = ctx.args[0].lower()

    if mode not in ("users", "groups", "both"):
        await premium.reply(
            msg,
            ":warning: <b>Invalid Mode</b>\n\n"
            "Use <code>/broadcast users</code>, <code>/broadcast groups</code>, "
            "or <code>/broadcast both</code>.",
        )
        return

    replied = msg.reply_to_message
    users, groups = await _broadcast_targets(mode)
    targets = list(groups) + list(users)

    if not targets:
        await premium.reply(msg, f":warning: No recipients found for mode <code>{mode}</code>.")
        return

    status = await premium.reply(
        msg,
        f":signal: <b>Broadcast In Progress</b>\n\n"
        f"<blockquote>"
        f"Mode: <code>{mode}</code>\n"
        f"Users: <code>{len(users)}</code>\n"
        f"Groups: <code>{len(groups)}</code>\n"
        f"Total: <code>{len(targets)}</code>"
        f"</blockquote>",
    )

    stats = {"ok": 0, "blocked": 0, "deleted": 0, "error": 0}

    for index, chat_id in enumerate(targets, start=1):
        result = await _copy_to(
            ctx.bot, chat_id, replied.chat_id, replied.message_id, replied.reply_markup
        )
        stats[result] += 1

        if index % 25 == 0 or index == len(targets):
            failed = stats["blocked"] + stats["deleted"] + stats["error"]
            try:
                await status.edit_text(
                    premium.render(
                        f":signal: <b>Broadcast In Progress</b>\n\n"
                        f"<blockquote>"
                        f"Progress: <code>{index}/{len(targets)}</code>\n"
                        f"Delivered: <code>{stats['ok']}</code>\n"
                        f"Failed: <code>{failed}</code>"
                        f"</blockquote>"
                    ),
                    parse_mode="HTML",
                )
            except Exception:
                pass

        await asyncio.sleep(0.05)

    failed = stats["blocked"] + stats["deleted"] + stats["error"]

    await status.edit_text(
        premium.render(
            f":success: <b>Broadcast Completed</b>\n\n"
            f"<blockquote>"
            f"Mode: <code>{mode}</code>\n"
            f"Total Targets: <code>{len(targets)}</code>\n\n"
            f"Delivered: <code>{stats['ok']}</code>\n"
            f"Blocked Bot: <code>{stats['blocked']}</code>\n"
            f"Deleted/Invalid: <code>{stats['deleted']}</code>\n"
            f"Other Errors: <code>{stats['error']}</code>"
            f"</blockquote>"
        ),
        parse_mode="HTML",
    )
    
@owner_only
async def maintenance_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    current = await db.get_maintenance()

    if not ctx.args:
        await premium.reply(
            msg,
            f":settings: <b>Maintenance Mode</b>\n\n"
            f"Current: {'ON' if current else 'OFF'}\n\n"
            f"Use:\n<code>/maintenance on</code>\n<code>/maintenance off</code>",
            reply_markup=maintenance_keyboard(current),
        )
        return

    action = ctx.args[0].lower()
    if action not in ("on", "off"):
        await premium.reply(msg, "Usage: <code>/maintenance on</code> or <code>/maintenance off</code>")
        return

    new_val = action == "on"
    await db.set_maintenance(new_val)

    status = await msg.reply_text("Broadcasting maintenance update...")
    sent, failed = await _announce_maintenance(ctx.bot, new_val)

    await status.edit_text(
        premium.render(
            f":success: Maintenance {'ON' if new_val else 'OFF'}.\n\n"
            f"Sent: <b>{sent}</b>\n"
            f"Failed: <b>{failed}</b>"
        ),
        parse_mode="HTML",
    )


async def maintenance_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = update.effective_user

    if not query or not user:
        return

    if user.id != config.OWNER_ID:
        await query.answer("Owner only.", show_alert=True)
        return

    action = query.data.split(":")[1]
    new_val = action == "on"

    await db.set_maintenance(new_val)
    await query.answer(f"Maintenance {'ON' if new_val else 'OFF'}")

    await query.edit_message_text("Broadcasting maintenance update...")

    sent, failed = await _announce_maintenance(ctx.bot, new_val)

    await premium.edit(
        query,
        f":success: Maintenance {'ON' if new_val else 'OFF'}.\n\n"
        f"Sent: <b>{sent}</b>\n"
        f"Failed: <b>{failed}</b>",
        reply_markup=maintenance_keyboard(new_val),
    )


async def owner_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if not query:
        return

    await query.answer()

    text = get("owner_panel.caption", owner=config.OWNER_USERNAME)

    try:
        await premium.edit_caption(query, text, reply_markup=owner_keyboard())
    except Exception:
        await premium.edit(query, text, reply_markup=owner_keyboard())


stats_cmd_h = CommandHandler("stats", stats_cmd)
stats_cb_h = CallbackQueryHandler(stats_callback, pattern="^stats$")

active_cmd_h = CommandHandler("active", active_cmd)

ban_cmd_h = CommandHandler("ban", ban_cmd)
unban_cmd_h = CommandHandler("unban", unban_cmd)
mute_cmd_h = CommandHandler("mute", mute_cmd)
unmute_cmd_h = CommandHandler("unmute", unmute_cmd)

setprefix_cmd_h = CommandHandler("setprefix", setprefix_cmd)
logs_cmd_h = CommandHandler("logs", logs_cmd)
groupstats_cmd_h = CommandHandler("groupstats", groupstats_cmd)
resetdata_cmd_h = CommandHandler("resetdata", resetdata_cmd)

broadcast_cmd_h = CommandHandler("broadcast", broadcast_cmd)

maintenance_cmd_h = CommandHandler("maintenance", maintenance_cmd)
maintenance_cb_h = CallbackQueryHandler(maintenance_callback, pattern=r"^maintenance:(on|off)$")

owner_cb_h = CallbackQueryHandler(owner_callback, pattern="^owner$")

leaderboard_cmd_h = CommandHandler("disabled_leaderboard", lambda *_: None)
