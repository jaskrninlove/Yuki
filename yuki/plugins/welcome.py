"""
Yuki Bot - Premium Welcome / Goodbye / Rules System
/setwelcome, /setgoodbye, /setrules, /rules, /welcome, /goodbye
"""

import html
import logging
import re
import time
from datetime import datetime

from telegram import Update, InlineKeyboardMarkup, ChatMemberUpdated
from telegram.constants import ParseMode
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    ChatMemberHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from yuki.core import database as db
from yuki.core.config import SUPPORT_LINK, UPDATES_CHANNEL
from yuki.utils.helpers import admin_only
from yuki.utils.keyboards import pbtn, icon
from yuki.utils import premium

log = logging.getLogger("yuki.plugins.welcome")

_INTRO_CACHE: dict[int, float] = {}
_INTRO_COOLDOWN = 30

WAITING_WELCOME_TEXT: dict[int, int] = {}
WAITING_WELCOME_BUTTONS: dict[int, int] = {}
WAITING_RULES_TEXT: dict[int, int] = {}


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def premium_keyboard(rows: list[list]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(rows)


def parse_buttons(text: str):
    pattern = r"\[([^\[\]-]+?)\s*-\s*(https?://[^\]\s]+|t\.me/[^\]\s]+|@[A-Za-z0-9_]+)\]"
    matches = re.findall(pattern, text or "")
    clean_text = re.sub(pattern, "", text or "").strip()

    rows = []
    row = []

    for label, url in matches:
        label = label.strip()
        url = url.strip()

        if url.startswith("t.me/"):
            url = "https://" + url
        elif url.startswith("@"):
            url = "https://t.me/" + url[1:]

        row.append(
            pbtn(
                label[:64],
                url=url,
                style="primary",
                icon=icon("sparkle") or icon("filter"),
            )
        )

        if len(row) == 2:
            rows.append(row)
            row = []

    if row:
        rows.append(row)

    return clean_text, InlineKeyboardMarkup(rows) if rows else None


def _serialize_markup(markup) -> dict | None:
    """Store a native InlineKeyboardMarkup (e.g. one already attached to the
    replied-to message, including premium colored/icon buttons) as a plain
    dict so it can be saved in MongoDB and rebuilt later."""
    if not markup:
        return None
    return markup.to_dict()


def _deserialize_markup(data: dict | None, bot=None):
    """Rebuild an InlineKeyboardMarkup from what _serialize_markup produced."""
    if not data:
        return None
    try:
        return InlineKeyboardMarkup.de_json(data, bot)
    except Exception as e:
        log.debug("Failed to rebuild stored markup: %s", e)
        return None


def _capture_message_content(target):
    """
    Pull text (as HTML, preserving bold/blockquote/premium custom-emoji),
    photo file_id, and native reply_markup off a replied-to message.
    Returns (text_html, photo_file_id, markup_dict).
    """
    if not target:
        return "", None, None

    photo_file_id = None
    text_html = ""

    if target.photo:
        photo_file_id = target.photo[-1].file_id
        text_html = target.caption_html or target.caption or ""
    elif target.text:
        text_html = target.text_html or target.text
    elif target.caption:
        text_html = target.caption_html or target.caption

    markup_dict = _serialize_markup(target.reply_markup) if target.reply_markup else None

    return text_html, photo_file_id, markup_dict


def format_template(text: str, user, chat) -> str:
    name = html.escape(user.full_name if user else "User")
    first_name = html.escape(user.first_name if user else "User")
    surname = html.escape(user.last_name if user and user.last_name else "")
    username = f"@{user.username}" if user and user.username else "No username"
    mention = f'<a href="tg://user?id={user.id}">{name}</a>' if user else name

    now = datetime.now()

    return (text or "").format(
        ID=user.id if user else 0,
        NAME=first_name,
        SURNAME=surname,
        NAMESURNAME=name,
        LANG=getattr(user, "language_code", "Unknown") or "Unknown",
        DATE=now.strftime("%d %b %Y"),
        TIME=now.strftime("%H:%M"),
        WEEKDAY=now.strftime("%A"),
        MENTION=mention,
        USERNAME=username,
        GROUPNAME=html.escape(chat.title or "this group"),
        RULES="/rules",
        name=first_name,
        username=username,
        mention=mention,
        user_id=user.id if user else 0,
        chat_title=html.escape(chat.title or "this group"),
        chat_id=chat.id,
    )


async def get_chat_settings(chat_id: int):
    return await db.get_db().chat_settings.find_one({"chat_id": chat_id}) or {}


async def save_chat_settings(chat_id: int, data: dict):
    await db.get_db().chat_settings.update_one(
        {"chat_id": chat_id},
        {"$set": data, "$setOnInsert": {"chat_id": chat_id}},
        upsert=True,
    )


async def save_group(chat):
    if not chat or chat.type == "private":
        return

    await db.upsert_group(chat.id, {
        "title": chat.title or "",
        "type": chat.type,
        "username": chat.username or "",
        "active": True,
        "updated_at": datetime.utcnow(),
    })


# ─────────────────────────────────────────────
# Keyboards — all icons from keyboards.py BUTTON_ICONS
# icon() tokens used: welcome, filter, search, gift, settings,
#                     yes, no, sparkle(via premium), back, cancel,
#                     notes, afk, top, refresh
# ─────────────────────────────────────────────

def welcome_panel_keyboard(chat_id: int):
    return premium_keyboard([
        [
            pbtn("Text",    callback_data=f"welcome_set_text:{chat_id}",    style="primary", icon=icon("notes")),
            pbtn("Preview", callback_data=f"welcome_preview:{chat_id}",     style="primary", icon=icon("search")),
        ],
        [
            pbtn("Media",   callback_data=f"welcome_set_media:{chat_id}",   style="primary", icon=icon("gift")),
            pbtn("Buttons", callback_data=f"welcome_set_buttons:{chat_id}", style="primary", icon=icon("filter")),
        ],
        [
            pbtn("Enable",  callback_data=f"welcome_toggle:{chat_id}:on",  style="success", icon=icon("yes")),
            pbtn("Disable", callback_data=f"welcome_toggle:{chat_id}:off", style="danger",  icon=icon("no")),
        ],
        [
            pbtn("Full Preview", callback_data=f"welcome_preview:{chat_id}", style="success", icon=icon("top")),
        ],
        [
            pbtn("Close", callback_data="welcome_close", style="danger", icon=icon("cancel")),
        ],
    ])


def back_to_panel_keyboard(chat_id: int):
    return premium_keyboard([
        [
            pbtn("Back",   callback_data=f"welcome_back:{chat_id}", style="primary", icon=icon("back")),
            pbtn("Cancel", callback_data="welcome_close",           style="danger",  icon=icon("cancel")),
        ],
    ])


def success_back_keyboard(chat_id: int):
    return premium_keyboard([
        [
            pbtn("Back to Settings", callback_data=f"welcome_back:{chat_id}", style="success", icon=icon("back")),
        ],
    ])


def rules_keyboard_panel():
    return premium_keyboard([
        [
            pbtn("Support", url=SUPPORT_LINK,    style="primary", icon=icon("support")),
            pbtn("Updates", url=UPDATES_CHANNEL, style="primary", icon=icon("updates")),
        ],
    ])


def intro_keyboard():
    return premium_keyboard([
        [
            pbtn("Support", url=SUPPORT_LINK,    style="primary", icon=icon("support")),
            pbtn("Updates", url=UPDATES_CHANNEL, style="primary", icon=icon("updates")),
        ],
        [
            pbtn("Add Me", url="https://t.me/yukkichitbot?startgroup=true", style="success", icon=icon("add")),
        ],
    ])


# ─────────────────────────────────────────────
# Bot Added Intro
# ─────────────────────────────────────────────

async def send_intro_once(ctx: ContextTypes.DEFAULT_TYPE, chat):
    now = time.time()
    last = _INTRO_CACHE.get(chat.id, 0)

    if now - last < _INTRO_COOLDOWN:
        return

    _INTRO_CACHE[chat.id] = now

    text = (
        ":heart: <b>Thanks for adding Yuki!</b>\n\n"
        "<blockquote>"
        "I'm your cute AI bestie for welcome messages, rules, gifts, ranks, birthdays and group fun.\n\n"
        "Use <code>/setwelcome</code> to customize welcome messages."
        "</blockquote>\n\n"
        "<i>Yuki is ready to make this group alive. :sparkle:</i>"
    )

    try:
        await premium.send(
            ctx.bot,
            chat.id,
            text,
            reply_markup=intro_keyboard(),
            disable_web_page_preview=True,
        )
    except Exception as e:
        log.debug("Intro send failed: %s", e)


async def track_bot_chats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    result: ChatMemberUpdated = update.my_chat_member
    if not result:
        return

    chat = result.chat
    new = result.new_chat_member

    if new.user.id != ctx.bot.id:
        return

    status = new.status

    if status in ("member", "administrator"):
        await save_group(chat)
        log.info("Bot added/updated in group: %s (%s)", chat.title, chat.id)
        await send_intro_once(ctx, chat)

    elif status in ("kicked", "left"):
        await db.upsert_group(chat.id, {"active": False})
        log.info("Bot removed from group: %s (%s)", chat.title, chat.id)


async def auto_save_group(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if not chat or chat.type == "private":
        return

    try:
        await save_group(chat)

        if user and not user.is_bot:
            await db.upsert_user(user.id, {
                "first_name": user.first_name or user.full_name,
                "username": user.username or "",
            })
    except Exception as e:
        log.debug("Auto save group/user failed: %s", e)


# ─────────────────────────────────────────────
# Welcome Setup
# ─────────────────────────────────────────────

@admin_only
async def setwelcome_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat = update.effective_chat

    if not chat or chat.type == "private":
        await premium.reply(msg, ":users: This command works in groups only.")
        return

    await save_group(chat)

    data = await get_chat_settings(chat.id)
    enabled = data.get("welcome_enabled", True)
    has_text = bool(data.get("welcome_text"))
    has_media = bool(data.get("welcome_photo"))
    has_buttons = bool(data.get("welcome_buttons")) or bool(data.get("welcome_markup"))

    if msg.reply_to_message:
        target = msg.reply_to_message

        text_html, photo_file_id, native_markup_dict = _capture_message_content(target)
        clean_text, bracket_markup = parse_buttons(text_html)

        # Force replace old welcome text/media/buttons with the new replied message.
        update_data = {
            "welcome_enabled": True,
            "welcome_text": clean_text or "Welcome {MENTION} to <b>{GROUPNAME}</b>.",
            # Keep the raw bracket-syntax text too, for backward-compatible manual editing.
            "welcome_buttons": text_html if not native_markup_dict else "",
            # Native buttons captured directly off the replied message (colors/icons intact).
            "welcome_markup": native_markup_dict,
        }
        if photo_file_id:
            update_data["welcome_photo"] = photo_file_id

        await save_chat_settings(chat.id, update_data)

        await premium.reply(
            msg,
            ":success: <b>Welcome message updated!</b>\n\n"
            f"<blockquote>"
            f":group: <b>Group:</b> {html.escape(chat.title or 'Group')}\n"
            f":settings: <b>Status:</b> Enabled"
            f"</blockquote>",
            reply_markup=welcome_panel_keyboard(chat.id),
        )
        return

    on_icon = ":yes:" if enabled else ":no:"

    text = (
        ":welcome: <b>Welcome Settings</b>\n\n"
        f"<blockquote>"
        f":group: <b>Group:</b> {html.escape(chat.title or 'Group')}\n\n"
        f":notes: Text — <b>{'Set' if has_text else 'Not set'}</b>\n"
        f":gift: Media — <b>{'Set' if has_media else 'Not set'}</b>\n"
        f":filter: Buttons — <b>{'Set' if has_buttons else 'Not set'}</b>\n"
        f"{on_icon} Welcome — <b>{'ON' if enabled else 'OFF'}</b>"
        f"</blockquote>\n\n"
        "<i>Use the buttons below to customize Yuki welcome, "
        "or just reply to any message (with photo/buttons/premium emoji) "
        "with <code>/setwelcome</code> to copy it exactly.</i>"
    )

    await premium.reply(
        msg,
        text,
        reply_markup=welcome_panel_keyboard(chat.id),
        disable_web_page_preview=True,
    )


async def welcome_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = update.effective_user

    if not query or not user:
        return

    await query.answer()

    data = query.data

    # ── Close ──
    if data == "welcome_close":
        try:
            await query.message.delete()
        except Exception:
            try:
                await premium.edit(query, ":success: Welcome setup closed.")
            except Exception:
                pass
        return

    # ── Back to panel ──
    if data.startswith("welcome_back:"):
        chat_id = int(data.split(":")[1])

        WAITING_WELCOME_TEXT.pop(user.id, None)
        WAITING_WELCOME_BUTTONS.pop(user.id, None)

        try:
            chat = await ctx.bot.get_chat(chat_id)
        except Exception:
            chat = query.message.chat

        db_data = await get_chat_settings(chat_id)
        enabled   = db_data.get("welcome_enabled", True)
        has_text  = bool(db_data.get("welcome_text"))
        has_media = bool(db_data.get("welcome_photo"))
        has_btns  = bool(db_data.get("welcome_buttons")) or bool(db_data.get("welcome_markup"))

        on_icon = ":yes:" if enabled else ":no:"

        panel_text = (
            ":welcome: <b>Welcome Settings</b>\n\n"
            f"<blockquote>"
            f":group: <b>Group:</b> {html.escape(getattr(chat, 'title', 'Group') or 'Group')}\n\n"
            f":notes: Text — <b>{'Set' if has_text else 'Not set'}</b>\n"
            f":gift: Media — <b>{'Set' if has_media else 'Not set'}</b>\n"
            f":filter: Buttons — <b>{'Set' if has_btns else 'Not set'}</b>\n"
            f"{on_icon} Welcome — <b>{'ON' if enabled else 'OFF'}</b>"
            f"</blockquote>\n\n"
            "<i>Use the buttons below to customize Yuki welcome.</i>"
        )

        await premium.edit(
            query,
            panel_text,
            reply_markup=welcome_panel_keyboard(chat_id),
        )
        return

    parts  = data.split(":")
    action = parts[0]
    chat_id = int(parts[1]) if len(parts) > 1 and parts[1].lstrip("-").isdigit() else None

    if not chat_id:
        return

    # ── Set Text ──
    if action == "welcome_set_text":
        WAITING_WELCOME_TEXT[user.id] = chat_id
        WAITING_WELCOME_BUTTONS.pop(user.id, None)

        await premium.edit(
            query,
            ":notes: <b>Send your welcome text now!</b>\n\n"
            "<blockquote>"
            ":sparkle: Telegram HTML is supported.\n\n"
            "<b>Placeholders you can use:</b>\n"
            ":profile: <code>{NAME}</code> — first name\n"
            ":users: <code>{NAMESURNAME}</code> — full name\n"
            ":back: <code>{MENTION}</code> — clickable mention\n"
            ":settings: <code>{USERNAME}</code> — username\n"
            ":top: <code>{ID}</code> — user ID\n"
            ":group: <code>{GROUPNAME}</code> — group name\n"
            ":afk: <code>{DATE}</code> :refresh: <code>{TIME}</code>\n"
            ":rules: <code>{RULES}</code> — rules command"
            "</blockquote>\n\n"
            "<i>Just send your text below and I'll save it!</i>",
            reply_markup=back_to_panel_keyboard(chat_id),
        )
        return

    # ── Set Media ──
    if action == "welcome_set_media":
        await premium.edit(
            query,
            ":gift: <b>Set Welcome Media</b>\n\n"
            "<blockquote>"
            ":sparkle: Go to your group and reply to a photo with:\n"
            "<code>/setwelcome</code>\n\n"
            ":settings: The caption (with formatting, premium emoji and buttons) "
            "will become your welcome message automatically!"
            "</blockquote>\n\n"
            "<i>This keeps media quality and formatting perfect.</i>",
            reply_markup=back_to_panel_keyboard(chat_id),
        )
        return

    # ── Set Buttons ──
    if action == "welcome_set_buttons":
        WAITING_WELCOME_BUTTONS[user.id] = chat_id
        WAITING_WELCOME_TEXT.pop(user.id, None)

        await premium.edit(
            query,
            ":filter: <b>Send your URL buttons now!</b>\n\n"
            "<blockquote>"
            ":sparkle: <b>One button:</b>\n"
            "<code>[Support - https://t.me/xenorachatz]</code>\n\n"
            ":next: <b>Two buttons in one row:</b>\n"
            "<code>[Support - https://t.me/xenorachatz] [Updates - https://t.me/xenoraorg]</code>\n\n"
            ":global: <b>New row — send each on a new line:</b>\n"
            "<code>[Button1 - https://link]</code>\n"
            "<code>[Button2 - https://link]</code>\n\n"
            "<i>Tip: instead of typing this, you can just reply to a message "
            "that already has buttons with <code>/setwelcome</code> "
            "to copy them exactly.</i>"
            "</blockquote>\n\n"
            "<i>Just send the button format below!</i>",
            reply_markup=back_to_panel_keyboard(chat_id),
        )
        return

    # ── Preview ──
    if action == "welcome_preview":
        await send_welcome_preview(query, ctx, chat_id)
        return

    # ── Toggle ──
    if action == "welcome_toggle":
        status_arg = parts[2] if len(parts) > 2 else "on"
        enabled    = status_arg == "on"
        await save_chat_settings(chat_id, {"welcome_enabled": enabled})

        on_icon = ":yes:" if enabled else ":no:"
        await premium.edit(
            query,
            f"{on_icon} <b>Welcome {'enabled' if enabled else 'disabled'}.</b>\n\n"
            f"<i>Welcome messages are now <b>{'ON' if enabled else 'OFF'}</b> for this group.</i>",
            reply_markup=welcome_panel_keyboard(chat_id),
        )
        return


async def welcome_setup_text_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg  = update.effective_message
    user = update.effective_user

    if not msg or not user or not msg.text:
        return

    # ── Welcome Text ──
    if user.id in WAITING_WELCOME_TEXT:
        chat_id = WAITING_WELCOME_TEXT.pop(user.id)

        text_html = msg.text_html or msg.text

        # Overwrite — unset $set replaces the field fully
        await db.get_db().chat_settings.update_one(
            {"chat_id": chat_id},
            {
                "$set": {
                    "welcome_text":    text_html,
                    "welcome_enabled": True,
                },
                "$setOnInsert": {"chat_id": chat_id},
            },
            upsert=True,
        )

        await premium.reply(
            msg,
            ":yes: <b>Welcome text saved!</b>\n\n"
            "<blockquote>"
            ":sparkle: Your custom welcome message is all set.\n"
            ":settings: Welcome is now <b>enabled</b> for your group!"
            "</blockquote>\n\n"
            "<i>Hit Preview from settings to see how it looks!</i>",
            reply_markup=success_back_keyboard(chat_id),
        )
        return

    # ── Welcome Buttons ──
    if user.id in WAITING_WELCOME_BUTTONS:
        chat_id = WAITING_WELCOME_BUTTONS.pop(user.id)

        await db.get_db().chat_settings.update_one(
            {"chat_id": chat_id},
            {
                "$set": {
                    "welcome_buttons": msg.text,
                    "welcome_markup": None,  # manual bracket-text buttons override any captured native markup
                    "welcome_enabled": True,
                },
                "$setOnInsert": {"chat_id": chat_id},
            },
            upsert=True,
        )

        await premium.reply(
            msg,
            ":yes: <b>Welcome buttons saved!</b>\n\n"
            "<blockquote>"
            ":filter: Your URL buttons are set and ready.\n"
            ":sparkle: They will appear with every welcome message!"
            "</blockquote>\n\n"
            "<i>Hit Preview from settings to see how they look!</i>",
            reply_markup=success_back_keyboard(chat_id),
        )
        return

    # ── Rules Text ──
    if user.id in WAITING_RULES_TEXT:
        chat_id = WAITING_RULES_TEXT.pop(user.id)

        text_html = msg.text_html or msg.text
        markup_dict = _serialize_markup(msg.reply_markup) if msg.reply_markup else None

        await db.get_db().chat_settings.update_one(
            {"chat_id": chat_id},
            {
                "$set": {
                    "rules_text": text_html,
                    "rules_markup": markup_dict,
                },
                "$setOnInsert": {"chat_id": chat_id},
            },
            upsert=True,
        )

        await premium.reply(
            msg,
            ":yes: <b>Rules saved!</b>\n\n"
            "<blockquote>"
            ":rules: Group rules are now set.\n"
            ":global: Members can view them with <code>/rules</code>."
            "</blockquote>",
        )
        return


async def send_welcome_preview(query, ctx, chat_id: int):
    data = await get_chat_settings(chat_id)

    try:
        chat = await ctx.bot.get_chat(chat_id)
    except Exception:
        chat = query.message.chat

    user = query.from_user

    welcome_text = data.get("welcome_text") or "Welcome {MENTION} to <b>{GROUPNAME}</b>."
    welcome_photo = data.get("welcome_photo")
    buttons_raw   = data.get("welcome_buttons") or ""
    native_markup = _deserialize_markup(data.get("welcome_markup"), ctx.bot)

    final_text = format_template(welcome_text, user, chat)

    if native_markup:
        markup = native_markup
    else:
        final_text, markup = parse_buttons(final_text)

    final_text = premium.render(final_text)

    try:
        if welcome_photo:
            await ctx.bot.send_photo(
                query.message.chat_id,
                photo=welcome_photo,
                caption=final_text,
                parse_mode=ParseMode.HTML,
                reply_markup=markup,
            )
        else:
            await ctx.bot.send_message(
                query.message.chat_id,
                final_text,
                parse_mode=ParseMode.HTML,
                reply_markup=markup,
                disable_web_page_preview=True,
            )
        await query.answer(":sparkle: Preview sent!")
    except Exception as e:
        await query.answer("Preview failed.", show_alert=True)
        log.debug("Welcome preview failed: %s", e)


# ─────────────────────────────────────────────
# Goodbye / Rules
# ─────────────────────────────────────────────

@admin_only
async def setgoodbye_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg  = update.effective_message
    chat = update.effective_chat

    if chat.type == "private":
        await premium.reply(msg, ":users: This command works in groups only.")
        return

    await save_group(chat)

    target       = msg.reply_to_message
    raw_text     = " ".join(ctx.args).strip()

    if target:
        text_html, photo_file_id, markup_dict = _capture_message_content(target)
        text = text_html or raw_text
    else:
        text = raw_text
        photo_file_id = None
        markup_dict = None

    if not text and not photo_file_id:
        await premium.reply(
            msg,
            ":filter: <b>Set Goodbye</b>\n\n"
            "Reply to text/photo (with buttons/premium emoji) with <code>/setgoodbye</code>\n"
            "or use <code>/setgoodbye Goodbye {NAME}</code>",
        )
        return

    await save_chat_settings(chat.id, {
        "goodbye_enabled": True,
        "goodbye_text":    text,
        "goodbye_photo":   photo_file_id,
        "goodbye_markup":  markup_dict,
    })

    await premium.reply(msg, ":yes: <b>Goodbye message saved and enabled.</b>")


@admin_only
async def setrules_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg  = update.effective_message
    chat = update.effective_chat

    if chat.type == "private":
        await premium.reply(msg, ":users: This command works in groups only.")
        return

    await save_group(chat)

    target   = msg.reply_to_message
    raw_text = " ".join(ctx.args).strip()

    if target:
        text_html, photo_file_id, markup_dict = _capture_message_content(target)
        text = text_html or raw_text
    else:
        text = raw_text
        photo_file_id = None
        markup_dict = None

    if not text and not photo_file_id:
        await premium.reply(
            msg,
            ":rules: <b>Set Rules</b>\n\n"
            "Reply to rules text/photo (with buttons/premium emoji/formatting) "
            "with <code>/setrules</code>\n"
            "or use <code>/setrules Be kind. No spam.</code>",
        )
        return

    await save_chat_settings(chat.id, {
        "rules_text":   text,
        "rules_photo":  photo_file_id,
        "rules_markup": markup_dict,
    })
    await premium.reply(msg, ":yes: <b>Rules saved.</b>", reply_markup=rules_keyboard_panel())


async def rules_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg  = update.effective_message
    chat = update.effective_chat

    if not chat or chat.type == "private":
        await premium.reply(msg, ":users: This command works in groups only.")
        return

    data  = await get_chat_settings(chat.id)
    rules = data.get("rules_text")

    if not rules:
        await premium.reply(msg, ":rules: No rules have been set for this group.")
        return

    rules_photo  = data.get("rules_photo")
    native_markup = _deserialize_markup(data.get("rules_markup"), ctx.bot)

    text = format_template(rules, update.effective_user, chat)

    if native_markup:
        markup = native_markup
    else:
        text, markup = parse_buttons(text)

    if rules_photo:
        await premium.reply_photo(
            msg,
            photo=rules_photo,
            caption=text,
            reply_markup=markup,
        )
    else:
        await premium.reply(
            msg,
            text,
            reply_markup=markup,
            disable_web_page_preview=True,
        )


@admin_only
async def welcome_toggle_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg  = update.effective_message
    chat = update.effective_chat

    if chat.type == "private":
        await premium.reply(msg, ":users: This command works in groups only.")
        return

    if not ctx.args or ctx.args[0].lower() not in ("on", "off"):
        await premium.reply(msg, "Usage: <code>/welcome on</code> or <code>/welcome off</code>")
        return

    enabled = ctx.args[0].lower() == "on"
    await save_chat_settings(chat.id, {"welcome_enabled": enabled})

    on_icon = ":yes:" if enabled else ":no:"
    await premium.reply(msg, f"{on_icon} <b>Welcome {'enabled' if enabled else 'disabled'}.</b>")


@admin_only
async def goodbye_toggle_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg  = update.effective_message
    chat = update.effective_chat

    if chat.type == "private":
        await premium.reply(msg, ":users: This command works in groups only.")
        return

    if not ctx.args or ctx.args[0].lower() not in ("on", "off"):
        await premium.reply(msg, "Usage: <code>/goodbye on</code> or <code>/goodbye off</code>")
        return

    enabled = ctx.args[0].lower() == "on"
    await save_chat_settings(chat.id, {"goodbye_enabled": enabled})

    on_icon = ":yes:" if enabled else ":no:"
    await premium.reply(msg, f"{on_icon} <b>Goodbye {'enabled' if enabled else 'disabled'}.</b>")


# ─────────────────────────────────────────────
# Welcome / Goodbye Senders
# ─────────────────────────────────────────────

async def welcome_member_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg  = update.effective_message
    chat = update.effective_chat

    if not msg or not chat or not msg.new_chat_members:
        return

    await save_group(chat)

    data = await get_chat_settings(chat.id)

    if not data.get("welcome_enabled", True):
        return

    welcome_text  = data.get("welcome_text") or "Welcome {MENTION} to <b>{GROUPNAME}</b>."
    welcome_photo = data.get("welcome_photo")
    buttons_raw   = data.get("welcome_buttons") or ""
    native_markup = _deserialize_markup(data.get("welcome_markup"), ctx.bot)

    for user in msg.new_chat_members:
        if user.is_bot:
            continue

        await db.upsert_user(user.id, {
            "first_name": user.first_name or user.full_name,
            "username":   user.username or "",
        })

        final_text = format_template(welcome_text, user, chat)

        if native_markup:
            markup = native_markup
        else:
            final_text, markup = parse_buttons(final_text)

        try:
            if welcome_photo:
                await premium.reply_photo(
                    msg,
                    photo=welcome_photo,
                    caption=final_text,
                    reply_markup=markup,
                )
            else:
                await premium.reply(
                    msg,
                    final_text,
                    reply_markup=markup,
                    disable_web_page_preview=True,
                )
        except Exception as e:
            log.warning("Welcome send failed: %s", e)


async def goodbye_member_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg  = update.effective_message
    chat = update.effective_chat

    if not msg or not chat or not msg.left_chat_member:
        return

    await save_group(chat)

    data = await get_chat_settings(chat.id)
    if not data.get("goodbye_enabled", False):
        return

    goodbye_text  = data.get("goodbye_text") or "Goodbye {NAME}."
    goodbye_photo = data.get("goodbye_photo")
    native_markup = _deserialize_markup(data.get("goodbye_markup"), ctx.bot)

    user = msg.left_chat_member
    final_text = format_template(goodbye_text, user, chat)

    if native_markup:
        markup = native_markup
    else:
        final_text, markup = parse_buttons(final_text)

    try:
        if goodbye_photo:
            await premium.reply_photo(
                msg,
                photo=goodbye_photo,
                caption=final_text,
                reply_markup=markup,
            )
        else:
            await premium.reply(
                msg,
                final_text,
                reply_markup=markup,
                disable_web_page_preview=True,
            )
    except Exception as e:
        log.warning("Goodbye send failed: %s", e)


# ─────────────────────────────────────────────
# Handlers
# ─────────────────────────────────────────────

bot_added_handler = ChatMemberHandler(track_bot_chats, ChatMemberHandler.MY_CHAT_MEMBER)

auto_save_handler = MessageHandler(
    filters.ChatType.GROUPS & ~filters.COMMAND,
    auto_save_group,
)

setwelcome_handler   = CommandHandler("setwelcome",  setwelcome_cmd)
setgoodbye_handler   = CommandHandler("setgoodbye",  setgoodbye_cmd)
setrules_handler     = CommandHandler("setrules",    setrules_cmd)
rules_handler        = CommandHandler("rules",       rules_cmd)
welcome_toggle_handler = CommandHandler("welcome",   welcome_toggle_cmd)
goodbye_toggle_handler = CommandHandler("goodbye",   goodbye_toggle_cmd)

welcome_callback_h = CallbackQueryHandler(
    welcome_callback,
    pattern=(
        r"^(welcome_set_text|welcome_set_media|welcome_set_buttons"
        r"|welcome_preview|welcome_toggle):-?\d+(:(on|off))?$"
        r"|^welcome_close$"
        r"|^welcome_back:-?\d+$"
    ),
)

welcome_setup_text_h = MessageHandler(
    filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND,
    welcome_setup_text_handler,
)

welcome_member_h  = MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS,  welcome_member_handler)
goodbye_member_h  = MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER,  goodbye_member_handler)
