"""
Yuki Bot - Premium Post & Create System

Commands:
/create [buttons]  - Reply to any message/media to save a reusable post
/post [buttons]    - Reply to any message/media to publish to saved channels
/posts             - Show saved created posts
/sendpost POST_ID  - Send saved post in current chat
/delpost POST_ID   - Delete saved post
/connect           - Forward a message from your channel to connect it

Button syntax:
Text - https://link | Text 2 - https://link && New Row - https://link

Examples:
/create Support - https://t.me/xenorachatz | Updates - https://t.me/xenoraorg
/create Buy Now - https://example.com && Support - https://t.me/xenorachatz
"""

import html
import logging
import secrets
from datetime import datetime

from telegram import Update, InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    ChatMemberHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

from yuki.core import config, database as db
from yuki.utils.helpers import owner_only
from yuki.utils.keyboards import pbtn, icon
from yuki.utils import premium

log = logging.getLogger("yuki.plugins.post")

BOT_USERNAME = getattr(config, "BOT_USERNAME", "yukkichitbot")


# ─────────────────────────────────────────────────────────────
# Button Parser
# ─────────────────────────────────────────────────────────────

def _normalize_url(url: str) -> str:
    url = (url or "").strip()

    if url.startswith("t.me/"):
        return "https://" + url

    if url.startswith("@"):
        return "https://t.me/" + url[1:]

    return url


def parse_buttons(raw: str) -> InlineKeyboardMarkup | None:
    """
    Button syntax:
    Text - https://link | Text 2 - https://link && New Row - https://link
    """
    raw = (raw or "").strip()
    if not raw:
        return None

    rows = []

    for row_text in raw.split("&&"):
        row = []

        for part in row_text.split("|"):
            part = part.strip()

            if " - " not in part:
                continue

            label, url = part.split(" - ", 1)
            label = label.strip()
            url = _normalize_url(url)

            if not label or not url.startswith(("http://", "https://")):
                continue

            row.append(
                pbtn(
                    label[:64],
                    url=url,
                    style="primary",
                    icon=icon("sparkle") or icon("gift"),
                )
            )

        if row:
            rows.append(row)

    return InlineKeyboardMarkup(rows) if rows else None


# ─────────────────────────────────────────────────────────────
# DB Helpers
# ─────────────────────────────────────────────────────────────

def _post_id() -> str:
    return secrets.token_hex(4)


async def save_created_post(owner_id: int, source_chat_id: int, source_msg_id: int, button_raw: str):
    post_id = _post_id()

    await db.get_db().created_posts.insert_one({
        "post_id": post_id,
        "owner_id": owner_id,
        "source_chat_id": source_chat_id,
        "source_msg_id": source_msg_id,
        "button_raw": button_raw or "",
        "created_at": datetime.utcnow(),
    })

    return post_id


async def get_created_post(post_id: str):
    return await db.get_db().created_posts.find_one({"post_id": post_id})


async def get_created_posts(owner_id: int, limit: int = 10):
    cursor = db.get_db().created_posts.find(
        {"owner_id": owner_id}
    ).sort("created_at", -1).limit(limit)

    return [doc async for doc in cursor]


async def delete_created_post(post_id: str, owner_id: int):
    res = await db.get_db().created_posts.delete_one({
        "post_id": post_id,
        "owner_id": owner_id,
    })
    return res.deleted_count > 0


async def get_saved_channels():
    cursor = db.get_db().channels.find({"active": True})
    return [doc async for doc in cursor]


# ─────────────────────────────────────────────────────────────
# Keyboards
# ─────────────────────────────────────────────────────────────

def channels_keyboard(channels: list) -> InlineKeyboardMarkup:
    rows = []

    for ch in channels[:30]:
        title = ch.get("title") or str(ch.get("chat_id"))
        chat_id = ch.get("chat_id")

        rows.append([
            pbtn(
                title[:40],
                callback_data=f"post_to:{chat_id}",
                style="success",
                icon=icon("signal") or icon("updates"),
            )
        ])

    rows.append([
        pbtn(
            "Add Me To Channel",
            url=f"https://t.me/{BOT_USERNAME}?startchannel=true",
            style="primary",
            icon=icon("add") or icon("bot"),
        )
    ])

    rows.append([
        pbtn(
            "Cancel",
            callback_data="post_cancel",
            style="danger",
            icon=icon("cancel"),
        )
    ])

    return InlineKeyboardMarkup(rows)


def created_posts_keyboard(posts: list) -> InlineKeyboardMarkup:
    rows = []

    for p in posts:
        post_id = p.get("post_id")
        created = p.get("created_at")
        when = created.strftime("%d %b") if hasattr(created, "strftime") else "Saved"

        rows.append([
            pbtn(
                f"{post_id} • {when}",
                callback_data=f"created_post:{post_id}",
                style="primary",
                icon=icon("mail") or icon("book"),
            )
        ])

    rows.append([
        pbtn(
            "Close",
            callback_data="post_cancel",
            style="danger",
            icon=icon("cancel"),
        )
    ])

    return InlineKeyboardMarkup(rows)


def created_post_actions_keyboard(post_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            pbtn(
                "Send Here",
                callback_data=f"send_created:{post_id}",
                style="success",
                icon=icon("success"),
            ),
            pbtn(
                "Delete",
                callback_data=f"delete_created:{post_id}",
                style="danger",
                icon=icon("warning"),
            ),
        ],
        [
            pbtn(
                "Back",
                callback_data="created_posts_back",
                style="primary",
                icon=icon("back"),
            )
        ],
    ])


# ─────────────────────────────────────────────────────────────
# Channel Save Event
# ─────────────────────────────────────────────────────────────

async def channel_member_update(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    event = update.my_chat_member
    if not event:
        return

    chat = event.chat
    new = event.new_chat_member.status

    if chat.type != "channel":
        return

    active = new in ("administrator", "member")
    removed = new in ("left", "kicked")

    if active:
        await db.get_db().channels.update_one(
            {"chat_id": chat.id},
            {
                "$set": {
                    "chat_id": chat.id,
                    "title": chat.title or "",
                    "username": chat.username or "",
                    "type": chat.type,
                    "active": True,
                    "updated_at": datetime.utcnow(),
                }
            },
            upsert=True,
        )
        log.info("Channel saved for posting: %s", chat.id)

    elif removed:
        await db.get_db().channels.update_one(
            {"chat_id": chat.id},
            {"$set": {"active": False, "updated_at": datetime.utcnow()}},
            upsert=True,
        )


# ─────────────────────────────────────────────────────────────
# /connect — Forward a channel message to connect it
# ─────────────────────────────────────────────────────────────

@owner_only
async def connect_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message

    if not msg:
        return

    await premium.reply(
        msg,
        ":sparkle: <b>Connect Your Channel</b>\n\n"
        "<blockquote>"
        "Forward any message from your channel here\n"
        "and I'll connect it instantly so you can post to it!\n\n"
        ":settings: Make sure I'm added as <b>Admin</b> in that channel first.\n"
        ":signal: Then just forward any message from the channel below."
        "</blockquote>\n\n"
        "<i>Waiting for a forwarded channel message...</i>",
        disable_web_page_preview=True,
    )

    ctx.user_data["waiting_connect"] = True


async def handle_forwarded_channel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user = update.effective_user

    if not msg or not user:
        return

    if user.id != config.OWNER_ID:
        return

    if not ctx.user_data.get("waiting_connect"):
        return

    # Check if forwarded from a channel
    forward_origin = msg.forward_origin if hasattr(msg, "forward_origin") else None
    forward_chat = None

    # PTB v20+ uses forward_origin
    if forward_origin and hasattr(forward_origin, "chat"):
        forward_chat = forward_origin.chat
    # Fallback for older PTB
    elif msg.forward_from_chat and msg.forward_from_chat.type == "channel":
        forward_chat = msg.forward_from_chat

    if not forward_chat or forward_chat.type != "channel":
        await premium.reply(
            msg,
            ":warning: <b>That's not a channel message.</b>\n\n"
            "<blockquote>Please forward a message <b>from a channel</b>, not a group or user.</blockquote>",
        )
        return

    ctx.user_data.pop("waiting_connect", None)

    chat_id = forward_chat.id
    title = forward_chat.title or str(chat_id)
    username = getattr(forward_chat, "username", "") or ""

    # Save/update channel in DB
    await db.get_db().channels.update_one(
        {"chat_id": chat_id},
        {
            "$set": {
                "chat_id": chat_id,
                "title": title,
                "username": username,
                "type": "channel",
                "active": True,
                "updated_at": datetime.utcnow(),
            }
        },
        upsert=True,
    )

    log.info("Channel connected via /connect: %s (%s)", title, chat_id)

    await premium.reply(
        msg,
        ":success: <b>Channel Connected!</b>\n\n"
        "<blockquote>"
        f":signal: <b>Channel:</b> {html.escape(title)}\n"
        f":id: <b>ID:</b> <code>{chat_id}</code>\n"
        f":settings: <b>Username:</b> {'@' + username if username else 'Private'}"
        "</blockquote>\n\n"
        "<i>You can now use /post to publish messages to this channel.</i>",
        disable_web_page_preview=True,
    )


# ─────────────────────────────────────────────────────────────
# /create
# ─────────────────────────────────────────────────────────────

@owner_only
async def create_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user = update.effective_user

    if not msg or not user:
        return

    if not msg.reply_to_message:
        await premium.reply(
            msg,
            ":sparkle: <b>Premium Create System</b>\n\n"
            "<blockquote>"
            "Reply to any message/media and use:\n\n"
            "<code>/create Button - https://link</code>\n\n"
            "Two buttons in one row:\n"
            "<code>/create Support - https://t.me/xenorachatz | Updates - https://t.me/xenoraorg</code>\n\n"
            "New row:\n"
            "<code>/create Buy - https://example.com && Support - https://t.me/xenorachatz</code>"
            "</blockquote>\n\n"
            "<i>It will save a reusable post you can send anywhere later.</i>",
        )
        return

    button_raw = " ".join(ctx.args).strip()
    markup = parse_buttons(button_raw)

    post_id = await save_created_post(
        owner_id=user.id,
        source_chat_id=msg.chat_id,
        source_msg_id=msg.reply_to_message.message_id,
        button_raw=button_raw,
    )

    ctx.user_data[f"created_markup:{post_id}"] = markup

    await premium.reply(
        msg,
        ":success: <b>Post Created Successfully</b>\n\n"
        "<blockquote>"
        f":id: <b>Post ID:</b> <code>{post_id}</code>\n"
        ":mail: <b>Saved:</b> Message/media copied source\n"
        f":settings: <b>Buttons:</b> {'Yes' if markup else 'No'}"
        "</blockquote>\n\n"
        "<b>Use:</b>\n"
        f"<code>/sendpost {post_id}</code>\n"
        f"<code>/postid {post_id}</code>\n\n"
        "<i>You can broadcast or send it anywhere later.</i>",
        disable_web_page_preview=True,
    )


# ─────────────────────────────────────────────────────────────
# Saved Posts
# ─────────────────────────────────────────────────────────────

@owner_only
async def posts_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user = update.effective_user

    posts = await get_created_posts(user.id, limit=10)

    if not posts:
        await premium.reply(
            msg,
            ":mail: <b>No created posts yet.</b>\n\n"
            "Reply to any message and use <code>/create</code> first.",
        )
        return

    lines = []
    for p in posts:
        pid = p.get("post_id")
        created = p.get("created_at")
        when = created.strftime("%d %b %Y • %H:%M") if hasattr(created, "strftime") else "Unknown"
        has_buttons = "Yes" if p.get("button_raw") else "No"
        lines.append(f":mail: <code>{pid}</code> — Buttons: <b>{has_buttons}</b> — {when}")

    await premium.reply(
        msg,
        ":book: <b>Your Created Posts</b>\n\n"
        f"<blockquote>{chr(10).join(lines)}</blockquote>\n\n"
        "<i>Tap a saved post below or use /sendpost POST_ID.</i>",
        reply_markup=created_posts_keyboard(posts),
        disable_web_page_preview=True,
    )


async def created_post_details(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = update.effective_user

    if not query or not user:
        return

    if user.id != config.OWNER_ID:
        await query.answer("Owner only.", show_alert=True)
        return

    await query.answer()

    post_id = query.data.split(":", 1)[1]
    post = await get_created_post(post_id)

    if not post:
        await premium.edit(query, ":warning: Saved post not found.")
        return

    created = post.get("created_at")
    when = created.strftime("%d %b %Y • %H:%M") if hasattr(created, "strftime") else "Unknown"

    await premium.edit(
        query,
        ":mail: <b>Created Post</b>\n\n"
        "<blockquote>"
        f":id: <b>Post ID:</b> <code>{post_id}</code>\n"
        f":settings: <b>Buttons:</b> {'Yes' if post.get('button_raw') else 'No'}\n"
        f":clock: <b>Created:</b> <code>{when}</code>"
        "</blockquote>",
        reply_markup=created_post_actions_keyboard(post_id),
    )


async def created_posts_back(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = update.effective_user

    if not query or not user:
        return

    await query.answer()

    posts = await get_created_posts(user.id, limit=10)

    if not posts:
        await premium.edit(query, ":mail: No created posts yet.")
        return

    lines = []
    for p in posts:
        pid = p.get("post_id")
        created = p.get("created_at")
        when = created.strftime("%d %b %Y • %H:%M") if hasattr(created, "strftime") else "Unknown"
        has_buttons = "Yes" if p.get("button_raw") else "No"
        lines.append(f":mail: <code>{pid}</code> — Buttons: <b>{has_buttons}</b> — {when}")

    await premium.edit(
        query,
        ":book: <b>Your Created Posts</b>\n\n"
        f"<blockquote>{chr(10).join(lines)}</blockquote>",
        reply_markup=created_posts_keyboard(posts),
    )


# ─────────────────────────────────────────────────────────────
# Send Created Post
# ─────────────────────────────────────────────────────────────

async def _send_created_post(bot, post: dict, target_chat_id: int):
    button_raw = post.get("button_raw") or ""
    markup = parse_buttons(button_raw) if button_raw else None

    return await bot.copy_message(
        chat_id=target_chat_id,
        from_chat_id=post["source_chat_id"],
        message_id=post["source_msg_id"],
        reply_markup=markup,
    )

@owner_only
async def sendpost_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message

    if not ctx.args:
        await premium.reply(
            msg,
            ":mail: Usage: <code>/sendpost POST_ID</code>",
        )
        return

    post_id = ctx.args[0].strip()
    post = await get_created_post(post_id)

    if not post:
        await premium.reply(msg, ":warning: Post not found.")
        return

    try:
        await _send_created_post(ctx.bot, post, msg.chat_id)
        await premium.reply(
            msg,
            ":success: <b>Created post sent here.</b>",
        )
    except Exception as e:
        await premium.reply(
            msg,
            ":warning: <b>Failed to send post.</b>\n\n"
            f"<blockquote><code>{html.escape(str(e))}</code></blockquote>",
        )


async def send_created_cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = update.effective_user

    if not query or not user:
        return

    if user.id != config.OWNER_ID:
        await query.answer("Owner only.", show_alert=True)
        return

    await query.answer("Sending...")

    post_id = query.data.split(":", 1)[1]
    post = await get_created_post(post_id)

    if not post:
        await premium.edit(query, ":warning: Post not found.")
        return

    try:
        await _send_created_post(ctx.bot, post, query.message.chat_id)
        await premium.edit(query, ":success: <b>Created post sent here.</b>")
    except Exception as e:
        await premium.edit(
            query,
            ":warning: <b>Failed to send post.</b>\n\n"
            f"<blockquote><code>{html.escape(str(e))}</code></blockquote>",
        )


@owner_only
async def delpost_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user = update.effective_user

    if not ctx.args:
        await premium.reply(msg, ":warning: Usage: <code>/delpost POST_ID</code>")
        return

    post_id = ctx.args[0].strip()
    ok = await delete_created_post(post_id, user.id)

    if ok:
        await premium.reply(msg, f":success: Deleted post <code>{post_id}</code>.")
    else:
        await premium.reply(msg, ":warning: Post not found or not yours.")


async def delete_created_cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = update.effective_user

    if not query or not user:
        return

    if user.id != config.OWNER_ID:
        await query.answer("Owner only.", show_alert=True)
        return

    post_id = query.data.split(":", 1)[1]
    ok = await delete_created_post(post_id, user.id)

    await query.answer("Deleted" if ok else "Not found")

    if ok:
        await premium.edit(query, f":success: Deleted post <code>{post_id}</code>.")
    else:
        await premium.edit(query, ":warning: Post not found.")


# ─────────────────────────────────────────────────────────────
# /post Direct Channel Publisher
# ─────────────────────────────────────────────────────────────

@owner_only
async def post_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user = update.effective_user

    if not msg or not user:
        return

    if not msg.reply_to_message:
        await premium.reply(
            msg,
            ":mail: <b>Premium Channel Post</b>\n\n"
            "<blockquote>"
            "Reply to any message/media and use:\n\n"
            "<code>/post Button - https://link</code>\n\n"
            "This will publish the replied message directly to saved channels.\n\n"
            ":sparkle: Don't have a channel connected yet?\n"
            "Use /connect to add one!"
            "</blockquote>",
        )
        return

    button_raw = " ".join(ctx.args).strip()
    post_markup = parse_buttons(button_raw)

    ctx.user_data["pending_post_msg_id"] = msg.reply_to_message.message_id
    ctx.user_data["pending_post_chat_id"] = msg.chat_id
    ctx.user_data["pending_post_markup"] = post_markup
    # Store button_raw so it can be re-parsed fresh per send (fixes broadcast stripping issue)
    ctx.user_data["pending_post_button_raw"] = button_raw

    channels = await get_saved_channels()

    if not channels:
        await premium.reply(
            msg,
            ":warning: <b>No connected channels yet.</b>\n\n"
            "<blockquote>"
            "Use /connect and forward a message from your channel,\n"
            "or add me as admin and I'll detect it automatically."
            "</blockquote>",
            reply_markup=channels_keyboard([]),
        )
        return

    await premium.reply(
        msg,
        ":sparkle: <b>Choose where to publish this post</b>\n\n"
        "<blockquote>"
        f":signal: <b>Connected Channels:</b> {len(channels)}\n"
        "Your replied message will be copied exactly with formatting/media."
        "</blockquote>\n\n"
        "<i>Select a channel below.</i>",
        reply_markup=channels_keyboard(channels),
    )


async def post_to_channel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = update.effective_user

    if not query or not user:
        return

    if user.id != config.OWNER_ID:
        await query.answer("Owner only.", show_alert=True)
        return

    await query.answer("Publishing...")

    try:
        target_chat_id = int(query.data.split(":", 1)[1])
    except Exception:
        await query.answer("Invalid channel.", show_alert=True)
        return

    source_chat_id = ctx.user_data.get("pending_post_chat_id")
    source_msg_id = ctx.user_data.get("pending_post_msg_id")
    button_raw = ctx.user_data.get("pending_post_button_raw", "")

    post_markup = parse_buttons(button_raw) if button_raw else None

    if not source_chat_id or not source_msg_id:
        await premium.edit(
            query,
            ":warning: <b>Post session expired.</b>\n\nReply to the message and use /post again.",
        )
        return

    try:
        # Step 1: Forward message as-is (premium emoji intact)
        forwarded = await ctx.bot.forward_message(
            chat_id=target_chat_id,
            from_chat_id=source_chat_id,
            message_id=source_msg_id,
        )

        # Step 2: Patch buttons onto forwarded message
        if post_markup:
            try:
                await ctx.bot.edit_message_reply_markup(
                    chat_id=target_chat_id,
                    message_id=forwarded.message_id,
                    reply_markup=post_markup,
                )
            except Exception:
                pass

        await premium.edit(
            query,
            ":success: <b>Post Published Successfully</b>\n\n"
            "<blockquote>"
            f":signal: Channel ID: <code>{target_chat_id}</code>\n"
            ":sparkle: Buttons and media copied beautifully."
            "</blockquote>",
        )

    except Exception as e:
        await premium.edit(
            query,
            ":warning: <b>Post Failed</b>\n\n"
            f"<blockquote><code>{html.escape(str(e))}</code></blockquote>\n\n"
            "<i>Make sure Yuki is admin in that channel.</i>",
        )

async def post_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if not query:
        return

    await query.answer("Cancelled")

    ctx.user_data.pop("pending_post_msg_id", None)
    ctx.user_data.pop("pending_post_chat_id", None)
    ctx.user_data.pop("pending_post_markup", None)
    ctx.user_data.pop("pending_post_button_raw", None)

    try:
        await premium.edit(query, ":success: Post cancelled.")
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────
# Handlers
# ─────────────────────────────────────────────────────────────

connect_cmd_h = CommandHandler("connect", connect_cmd)
connect_forward_h = MessageHandler(
    filters.FORWARDED & filters.ChatType.PRIVATE,
    handle_forwarded_channel,
)

create_cmd_h = CommandHandler("create", create_cmd)
posts_cmd_h = CommandHandler("posts", posts_cmd)
sendpost_cmd_h = CommandHandler(["sendpost", "postid"], sendpost_cmd)
delpost_cmd_h = CommandHandler("delpost", delpost_cmd)

created_post_details_h = CallbackQueryHandler(created_post_details, pattern=r"^created_post:[a-f0-9]+$")
created_posts_back_h = CallbackQueryHandler(created_posts_back, pattern=r"^created_posts_back$")
send_created_h = CallbackQueryHandler(send_created_cb, pattern=r"^send_created:[a-f0-9]+$")
delete_created_h = CallbackQueryHandler(delete_created_cb, pattern=r"^delete_created:[a-f0-9]+$")

post_cmd_h = CommandHandler("post", post_cmd)
post_to_channel_h = CallbackQueryHandler(post_to_channel, pattern=r"^post_to:-?\d+$")
post_cancel_h = CallbackQueryHandler(post_cancel, pattern=r"^post_cancel$")

post_channel_event_h = ChatMemberHandler(
    channel_member_update,
    ChatMemberHandler.MY_CHAT_MEMBER,
)