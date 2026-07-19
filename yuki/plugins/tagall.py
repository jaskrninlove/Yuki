"""
Yuki Bot - TagAll System
Premium emoji supported. Tags ALL members without stopping.
Multi-strategy fetch: A-Z + digits + empty to get maximum members.
Flood-wait aware. Retry on failure.

Commands:
@all message / @tagall message / @yukitag message
/yukitag message
/yukistop
"""

import asyncio
import html
import logging
import random
import string

from telethon import TelegramClient, errors
from telethon.sessions import StringSession
from telethon.tl.functions.channels import GetParticipantsRequest
from telethon.tl.types import (
    ChannelParticipantsSearch,
    ChannelParticipantsRecent,
    ChannelParticipantsAdmins,
    InputChannel,
)

from telegram import Update
from telegram.constants import ChatAction
from telegram.error import RetryAfter, TimedOut, NetworkError
from telegram.ext import MessageHandler, CommandHandler, filters, ContextTypes

from yuki.core.config import API_ID, API_HASH, SESSION_STRING
from yuki.utils.helpers import admin_only

log = logging.getLogger("yuki.plugins.tagall")

_client: TelegramClient | None = None
_ACTIVE_TAGS: dict[int, bool]  = {}

# ─────────────────────────────────────────────
# Premium Emoji Pools
# ─────────────────────────────────────────────

_LOVE_IDS = [
    "5285439518130857782", "5285184156555306745", "5255956191141454203",
    "5255877597534905292", "5255861796350224063", "5260567255145539253",
    "5260413856093598223", "5262671999573977569", "5285338659413846416",
]
_CUTE_IDS = [
    "6325566832128296846", "6325566935207511670", "6325744330241738879",
    "6325361738849978542", "6323605870320027609", "6325509717653194893",
    "6325520386351958082", "6325760878750730257", "6325706001953589137",
]
_HEART_IDS = [
    "5255877597534905292", "5260413856093598223", "5262671999573977569",
    "6226552258109114048", "6228988874660513717", "5402266721685896440",
    "5402460596509636884", "6226245425645488040",
]
_HAPPY_IDS = [
    "6228807820314150688", "6228766915045623859", "6228643559289915791",
    "6226393408743672191", "6228954420432865653", "6228673074305173076",
    "6228939181888899000", "6226722222849918703",
]
_ALL_IDS = _LOVE_IDS + _CUTE_IDS + _HEART_IDS + _HAPPY_IDS


def _pe(emoji_id: str, fallback: str = "💗") -> str:
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'


def _rand(pool: list, fallback: str = "💗") -> str:
    return _pe(random.choice(pool), fallback)


def _pick() -> str:
    return _pe(random.choice(_ALL_IDS), "✨")


# ─────────────────────────────────────────────
# Telethon Client
# ─────────────────────────────────────────────

async def get_telethon() -> TelegramClient | None:
    global _client

    if not API_ID or not API_HASH or not SESSION_STRING:
        log.warning("Tagall: Missing API_ID / API_HASH / SESSION_STRING")
        return None

    try:
        if _client is None:
            _client = TelegramClient(
                StringSession(SESSION_STRING.strip()),
                int(API_ID),
                API_HASH,
            )

        if not _client.is_connected():
            await _client.connect()

        if not await _client.is_user_authorized():
            log.warning("Tagall: Telethon session not authorized")
            return None

        return _client

    except Exception as e:
        log.exception("Tagall: Telethon start failed: %s", e)
        return None


# ─────────────────────────────────────────────
# Member Fetcher — Multi-Strategy
# Gets MAXIMUM members by searching A-Z, 0-9, recent, admins
# ─────────────────────────────────────────────

async def _fetch_by_query(
    client: TelegramClient,
    input_ch: InputChannel,
    query: str,
    seen_ids: set,
    members: list,
):
    """Fetch members matching a search query and add new ones to list."""
    offset = 0
    limit  = 200

    while True:
        try:
            result = await client(GetParticipantsRequest(
                channel=input_ch,
                filter=ChannelParticipantsSearch(query),
                offset=offset,
                limit=limit,
                hash=0,
            ))
        except errors.FloodWaitError as e:
            log.debug("Tagall: FloodWait %ds for query '%s'", e.seconds, query)
            await asyncio.sleep(e.seconds + 2)
            continue
        except Exception as e:
            log.debug("Tagall: Query '%s' failed: %s", query, e)
            break

        if not result.users:
            break

        added = 0
        for user in result.users:
            if user and not user.bot and not user.deleted and user.id not in seen_ids:
                members.append(user)
                seen_ids.add(user.id)
                added += 1

        offset += len(result.users)

        if len(result.users) < limit:
            break

        await asyncio.sleep(0.5)


async def _fetch_recent(
    client: TelegramClient,
    input_ch: InputChannel,
    seen_ids: set,
    members: list,
):
    """Fetch recent participants — different pool from search."""
    offset = 0
    limit  = 200

    while True:
        try:
            result = await client(GetParticipantsRequest(
                channel=input_ch,
                filter=ChannelParticipantsRecent(),
                offset=offset,
                limit=limit,
                hash=0,
            ))
        except errors.FloodWaitError as e:
            await asyncio.sleep(e.seconds + 2)
            continue
        except Exception:
            break

        if not result.users:
            break

        for user in result.users:
            if user and not user.bot and not user.deleted and user.id not in seen_ids:
                members.append(user)
                seen_ids.add(user.id)

        offset += len(result.users)
        if len(result.users) < limit:
            break

        await asyncio.sleep(0.5)


async def _fetch_admins(
    client: TelegramClient,
    input_ch: InputChannel,
    seen_ids: set,
    members: list,
):
    """Fetch admins — make sure they're included."""
    try:
        result = await client(GetParticipantsRequest(
            channel=input_ch,
            filter=ChannelParticipantsAdmins(),
            offset=0,
            limit=200,
            hash=0,
        ))
        for user in result.users:
            if user and not user.bot and not user.deleted and user.id not in seen_ids:
                members.append(user)
                seen_ids.add(user.id)
    except Exception as e:
        log.debug("Tagall: Admin fetch failed: %s", e)


async def fetch_all_members(
    client: TelegramClient,
    chat_id: int,
    status_cb=None,
) -> list:
    """
    Multi-strategy exhaustive fetch:
    1. Empty search (general pool)
    2. A-Z single letter searches
    3. 0-9 digit searches
    4. Recent participants
    5. Admins
    All merged and deduped — gets maximum possible members.
    """
    members:  list     = []
    seen_ids: set[int] = set()

    try:
        entity = await client.get_entity(chat_id)
    except Exception as e:
        log.warning("Tagall: get_entity failed: %s", e)
        return members

    is_super = hasattr(entity, "megagroup") or hasattr(entity, "broadcast")

    if not is_super:
        # Regular group — simple iter works fine
        try:
            async for user in client.iter_participants(entity):
                if user and not user.bot and not user.deleted and user.id not in seen_ids:
                    members.append(user)
                    seen_ids.add(user.id)
        except Exception as e:
            log.warning("Tagall: Regular group iter failed: %s", e)
        return members

    # ── Supergroup — multi-strategy ──
    input_ch = InputChannel(entity.id, entity.access_hash)

    # Strategy 1: Empty search
    if status_cb:
        await status_cb("Fetching members... (pass 1/4)")
    await _fetch_by_query(client, input_ch, "", seen_ids, members)
    log.debug("Tagall: After empty search: %d", len(members))

    # Strategy 2: A-Z searches
    if status_cb:
        await status_cb(f"Fetching members... (pass 2/4) — {len(members)} so far")

    for char in string.ascii_lowercase:
        if not _ACTIVE_TAGS.get(chat_id, True):
            break
        await _fetch_by_query(client, input_ch, char, seen_ids, members)
        await asyncio.sleep(0.4)

    log.debug("Tagall: After A-Z: %d", len(members))

    # Strategy 3: 0-9 digit searches
    if status_cb:
        await status_cb(f"Fetching members... (pass 3/4) — {len(members)} so far")

    for digit in string.digits:
        if not _ACTIVE_TAGS.get(chat_id, True):
            break
        await _fetch_by_query(client, input_ch, digit, seen_ids, members)
        await asyncio.sleep(0.3)

    log.debug("Tagall: After 0-9: %d", len(members))

    # Strategy 4: Recent + Admins
    if status_cb:
        await status_cb(f"Fetching members... (pass 4/4) — {len(members)} so far")

    await _fetch_recent(client, input_ch, seen_ids, members)
    await _fetch_admins(client, input_ch, seen_ids, members)

    log.info("Tagall: Final member count: %d / chat: %s", len(members), chat_id)
    return members


# ─────────────────────────────────────────────
# Safe Send — retries on flood/network, never skips
# ─────────────────────────────────────────────

async def _safe_send(bot, chat_id: int, text: str, max_retries: int = 6) -> bool:
    for attempt in range(max_retries):
        try:
            await bot.send_message(
                chat_id,
                text,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
            return True

        except RetryAfter as e:
            wait = e.retry_after + 1
            log.debug("Tagall: RetryAfter %ds", wait)
            await asyncio.sleep(wait)

        except (TimedOut, NetworkError) as e:
            wait = 3 * (attempt + 1)
            log.debug("Tagall: Network error retry in %ds: %s", wait, e)
            await asyncio.sleep(wait)

        except Exception as e:
            err = str(e).lower()
            if "flood" in err or "too many" in err or "429" in err:
                wait = 15 * (attempt + 1)
                log.debug("Tagall: Flood, waiting %ds", wait)
                await asyncio.sleep(wait)
            else:
                return False

    return False


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

# CHANGED: now takes the Message object (not raw text) so we can pull the
# HTML-rendered version and preserve bold/italic/premium-emoji formatting.
def extract_message(msg) -> str:
    text = (msg.text or msg.caption or "").strip()
    html_text = (msg.text_html or msg.caption_html or text).strip()
    lower = text.lower()

    for prefix in ("@all", "@tagall", "@yukitag", "/yukitag"):
        if lower.startswith(prefix):
            return html_text[len(prefix):].strip()
    return ""


# ─────────────────────────────────────────────
# /yukistop
# ─────────────────────────────────────────────

@admin_only
async def yukistop_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    msg  = update.effective_message

    if not chat or not msg:
        return

    if chat.type == "private":
        await msg.reply_text("This command works in groups only.")
        return

    if not _ACTIVE_TAGS.get(chat.id):
        await msg.reply_text(
            f"{_rand(_CUTE_IDS, '💗')} <b>No active tagging running right now.</b>",
            parse_mode="HTML",
        )
        return

    _ACTIVE_TAGS[chat.id] = False

    await msg.reply_text(
        f"{_rand(_HEART_IDS, '💗')} <b>Tagging stopped.</b>\n\n"
        f"<blockquote>Yuki paused the mentions for this group.</blockquote>",
        parse_mode="HTML",
    )


# ─────────────────────────────────────────────
# Main Tag Handler
# ─────────────────────────────────────────────

@admin_only
async def tagall_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg  = update.effective_message
    chat = update.effective_chat

    if not msg or not chat:
        return

    if chat.type == "private":
        await msg.reply_text("This command works in groups only.")
        return

    if _ACTIVE_TAGS.get(chat.id):
        await msg.reply_text(
            f"{_rand(_CUTE_IDS, '⚠️')} <b>A tagging session is already running.</b>\n\n"
            f"<blockquote>Use <code>/yukistop</code> to stop it first.</blockquote>",
            parse_mode="HTML",
        )
        return

    # CHANGED: pass the whole message object, not raw text
    custom_msg = extract_message(msg)

    client = await get_telethon()
    if not client:
        await msg.reply_text(
            f"{_rand(_CUTE_IDS, '⚠️')} <b>Tagging not configured.</b>\n\n"
            f"<blockquote>"
            f"Set in .env:\n"
            f"<code>API_ID</code> · <code>API_HASH</code> · <code>SESSION_STRING</code>\n\n"
            f"Session account must be in this group."
            f"</blockquote>",
            parse_mode="HTML",
        )
        return

    await ctx.bot.send_chat_action(chat.id, ChatAction.TYPING)

    status = await msg.reply_text(
        f"{_rand(_HAPPY_IDS, '✨')} <b>Collecting ALL members...</b>\n\n"
        f"<blockquote>This may take a moment for large groups. Please wait!!</blockquote>",
        parse_mode="HTML",
    )

    _ACTIVE_TAGS[chat.id] = True

    async def update_status(text: str):
        try:
            await status.edit_text(
                f"{_rand(_HAPPY_IDS, '✨')} <b>{html.escape(text)}</b>",
                parse_mode="HTML",
            )
        except Exception:
            pass

    members = await fetch_all_members(client, chat.id, status_cb=update_status)

    if not members:
        _ACTIVE_TAGS[chat.id] = False
        await status.edit_text(
            f"{_rand(_CUTE_IDS, '⚠️')} <b>Could not fetch members.</b>\n\n"
            f"<blockquote>"
            f"Make sure the session account is a member of this group "
            f"and can see the member list."
            f"</blockquote>",
            parse_mode="HTML",
        )
        return

    if not _ACTIVE_TAGS.get(chat.id):
        await status.edit_text(
            f"{_rand(_HEART_IDS, '💗')} <b>Stopped during member collection.</b>",
            parse_mode="HTML",
        )
        return

    try:
        await status.edit_text(
            f"{_rand(_HEART_IDS, '💗')} <b>Tagging started!!</b>\n\n"
            f"<blockquote>"
            f"Found <b>{len(members)}</b> members {_rand(_CUTE_IDS, '✨')}\n"
            f"Use <code>/yukistop</code> to stop anytime."
            f"</blockquote>",
            parse_mode="HTML",
        )
    except Exception:
        pass

    if msg.reply_to_message:
        try:
            await msg.reply_to_message.copy(chat.id)
        except Exception:
            pass

    sent    = 0
    failed  = 0
    stopped = False

    for user in members:
        if not _ACTIVE_TAGS.get(chat.id):
            stopped = True
            break

        try:
            name = html.escape(
                user.first_name
                or (f"@{user.username}" if user.username else None)
                or str(user.id)
            )

            emoji = _pick()

            if custom_msg:
                # CHANGED: custom_msg is already safe HTML (from text_html),
                # do not html.escape() it again or the tags/premium emoji break.
                text = (
                    f'{emoji} <a href="tg://user?id={user.id}">{name}</a>\n'
                    f"{custom_msg}"
                )
            else:
                text = f'{emoji} <a href="tg://user?id={user.id}">{name}</a>'

        except Exception:
            failed += 1
            continue

        ok = await _safe_send(ctx.bot, chat.id, text)

        if ok:
            sent += 1
        else:
            failed += 1

        if sent > 0 and sent % 50 == 0:
            try:
                await status.edit_text(
                    f"{_rand(_HAPPY_IDS, '✨')} <b>Tagging in progress...</b>\n\n"
                    f"<blockquote>"
                    f"Tagged: <b>{sent}</b> / <b>{len(members)}</b> "
                    f"{_rand(_CUTE_IDS, '💗')}\n"
                    f"Use <code>/yukistop</code> to stop."
                    f"</blockquote>",
                    parse_mode="HTML",
                )
            except Exception:
                pass

        await asyncio.sleep(1.3)

    _ACTIVE_TAGS[chat.id] = False

    try:
        if stopped:
            await status.edit_text(
                f"{_rand(_HEART_IDS, '💗')} <b>Tagging stopped!!</b>\n\n"
                f"<blockquote>"
                f"Mentioned <b>{sent}</b> / <b>{len(members)}</b> members "
                f"{_rand(_CUTE_IDS, '✨')}\n"
                f"Stopped before finishing."
                f"</blockquote>",
                parse_mode="HTML",
            )
        else:
            await status.edit_text(
                f"{_rand(_HEART_IDS, '💗')} <b>Tagging complete!!</b>\n\n"
                f"<blockquote>"
                f"Tagged <b>{sent}</b> / <b>{len(members)}</b> members "
                f"{_rand(_HAPPY_IDS, '✨')}\n"
                + (f"Failed / skipped: <b>{failed}</b>" if failed else "Everyone was tagged!!")
                + f"</blockquote>",
                parse_mode="HTML",
            )
    except Exception:
        pass

    log.info(
        "Tagall done — chat=%s sent=%d failed=%d total=%d stopped=%s",
        chat.id, sent, failed, len(members), stopped,
    )


# ─────────────────────────────────────────────
# Handlers
# ─────────────────────────────────────────────

tag_handler = MessageHandler(
    filters.Regex(r"(?i)^@(all|tagall|yukitag)(\s|$)") & ~filters.COMMAND,
    tagall_handler,
)
yukitag_handler  = CommandHandler("yukitag",  tagall_handler)
yukistop_handler = CommandHandler("yukistop", yukistop_cmd)


# ─────────────────────────────────────────────
# Shutdown
# ─────────────────────────────────────────────

async def shutdown_telethon():
    global _client

    for chat_id in list(_ACTIVE_TAGS.keys()):
        _ACTIVE_TAGS[chat_id] = False

    if _client:
        try:
            await _client.disconnect()
            log.info("Tagall: Telethon disconnected")
        except Exception as e:
            log.debug("Tagall: Disconnect error: %s", e)
        finally:
            _client = None