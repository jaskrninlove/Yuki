"""
Yuki Bot - Chat Handler
- Pure AI replies — no keyword/custom reply system
- English only
- Admin-only in groups
- Age guard — ignores backlog on reconnect/promote
- No sticker spam, no emoji spam
"""

import asyncio
import logging
import random
from collections import defaultdict
from datetime import datetime, timezone
import time as _time

from telegram import Update, Bot
from telegram.ext import MessageHandler, filters, ContextTypes
from telegram.constants import ChatAction
from yuki.plugins.stickers import get_random_sticker
from yuki.core import database as db
from yuki.utils.brain import get_reply, _smart_fallback
from yuki.utils.helpers import ensure_user

log = logging.getLogger("yuki.handlers.chat")

# ─────────────────────────────────────────────
# State
# ─────────────────────────────────────────────

_history: dict[int, list[dict]] = defaultdict(list)
_MAX_HISTORY = 14

_last_reply: dict[int, datetime]  = {}
_user_last: dict[int, datetime]   = {}
_last_sticker: dict[int, datetime] = {}
_replied_streak: dict[int, int]   = defaultdict(int)
import random  # already imported at top, confirm it's there

_last_random_sticker: dict[int, datetime] = {}
RANDOM_STICKER_CHANCE = 0.06        # 6% chance per group reply
RANDOM_STICKER_COOLDOWN = 30 * 60   # at least 30 min between random stickers per chat


def _can_random_sticker(chat_id: int) -> bool:
    now = datetime.utcnow()
    return (now - _last_random_sticker.get(chat_id, datetime.min)).total_seconds() > RANDOM_STICKER_COOLDOWN


def _mark_random_sticker(chat_id: int):
    _last_random_sticker[chat_id] = datetime.utcnow()

# Cooldowns (seconds)
_CHAT_COOLDOWN    = 5
_USER_COOLDOWN    = 8
_STICKER_COOLDOWN = 180
_STREAK_SKIP      = 6   # skip reply after N consecutive replies (feels natural)

# Bot startup time — messages before this are ignored (backlog guard)
_BOT_START_TIME: datetime | None = None

_bot_id: int | None       = None
_bot_username: str | None = None

# Admin cache
_admin_cache: dict[int, bool]  = {}
_admin_cache_ts: dict[int, float] = {}
_ADMIN_CACHE_TTL = 300


def init_bot_info(bot_id: int, username: str):
    global _bot_id, _bot_username, _BOT_START_TIME
    _bot_id         = bot_id
    _bot_username   = username.lower()
    _BOT_START_TIME = datetime.now(timezone.utc)
    log.info("Chat handler ready — @%s (%s) start=%s", username, bot_id, _BOT_START_TIME)


# ─────────────────────────────────────────────
# Admin Check (cached)
# ─────────────────────────────────────────────

async def _is_admin(bot: Bot, chat_id: int) -> bool:
    now = _time.monotonic()
    if chat_id in _admin_cache:
        if now - _admin_cache_ts.get(chat_id, 0) < _ADMIN_CACHE_TTL:
            return _admin_cache[chat_id]
    try:
        member = await bot.get_chat_member(chat_id, bot.id)
        result = member.status in ("administrator", "creator")
    except Exception:
        result = False
    _admin_cache[chat_id]    = result
    _admin_cache_ts[chat_id] = now
    return result


def invalidate_admin_cache(chat_id: int):
    _admin_cache.pop(chat_id, None)
    _admin_cache_ts.pop(chat_id, None)


# ─────────────────────────────────────────────
# Age Guard — kills backlog spam
# ─────────────────────────────────────────────

def _is_old(msg) -> bool:
    """True if message was sent before bot started — skip it."""
    if _BOT_START_TIME is None or msg.date is None:
        return False
    msg_date = msg.date
    if msg_date.tzinfo is None:
        msg_date = msg_date.replace(tzinfo=timezone.utc)
    return msg_date < _BOT_START_TIME


# ─────────────────────────────────────────────
# Cooldown Helpers
# ─────────────────────────────────────────────

def _push_history(chat_id: int, role: str, content: str):
    hist = _history[chat_id]
    hist.append({"role": role, "content": content})
    if len(hist) > _MAX_HISTORY:
        hist.pop(0)


def _can_reply(chat_id: int, user_id: int) -> bool:
    now = datetime.utcnow()
    if (now - _last_reply.get(chat_id, datetime.min)).total_seconds() < _CHAT_COOLDOWN:
        return False
    if (now - _user_last.get(user_id, datetime.min)).total_seconds() < _USER_COOLDOWN:
        return False
    # Natural skip after too many consecutive replies
    if _replied_streak[chat_id] >= _STREAK_SKIP:
        _replied_streak[chat_id] = 0
        return False
    return True


def _mark_replied(chat_id: int, user_id: int):
    now = datetime.utcnow()
    _last_reply[chat_id]  = now
    _user_last[user_id]   = now
    _replied_streak[chat_id] += 1


def _can_sticker_reply(chat_id: int) -> bool:
    now = datetime.utcnow()
    return (now - _last_sticker.get(chat_id, datetime.min)).total_seconds() > _STICKER_COOLDOWN


def _mark_sticker(chat_id: int):
    _last_sticker[chat_id] = datetime.utcnow()


# ─────────────────────────────────────────────
# Activity Tracking
# ─────────────────────────────────────────────

async def _track_activity(bot, user, chat, kind: str = "text", text: str | None = None):
    try:
        await ensure_user(user)
        await db.increment_user_messages(user.id, chat.id)
        if text:
            await db.log_message(chat.id, user.id, text)

            if chat.type != "private":
                try:
                    from yuki.modules.rankings.rankings import check_daily_milestones
                    await check_daily_milestones(bot, chat.id, chat.title or "")
                except Exception as e:
                    log.debug("Milestone check failed: %s", e)

        inc = {"xp": 5, "rank_score": 5, "daily_messages": 1, "weekly_messages": 1, "monthly_messages": 1}
        if kind == "text":    inc["text_messages"] = 1
        elif kind == "sticker": inc["stickers_sent"] = 1; inc["xp"] = 2; inc["rank_score"] = 2
        elif kind == "photo": inc["photos_sent"] = 1;    inc["xp"] = 3; inc["rank_score"] = 3
        elif kind == "video": inc["videos_sent"] = 1;    inc["xp"] = 4; inc["rank_score"] = 4
        elif kind == "voice": inc["voice_notes"] = 1;    inc["xp"] = 4; inc["rank_score"] = 4

        await db.get_db().users.update_one(
            {"user_id": user.id},
            {
                "$inc": inc,
                "$set": {
                    "user_id":    user.id,
                    "first_name": user.first_name or user.full_name,
                    "username":   user.username,
                    "last_seen":  datetime.utcnow(),
                },
                "$addToSet": {"active_chats": chat.id},
            },
            upsert=True,
        )
    except Exception as e:
        log.debug("Activity tracking failed: %s", e)


async def _send_typing(chat_id: int, ctx):
    try:
        await ctx.bot.send_chat_action(chat_id, ChatAction.TYPING)
    except Exception:
        pass


# ─────────────────────────────────────────────
# Main Text Handler — pure AI, no keyword system
# ─────────────────────────────────────────────

# Replace handle_text in yuki/handlers/chat.py with this instrumented version.
# Temporary — remove the print() lines once the issue is found.

async def handle_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg  = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    if not msg or not user or not chat or user.is_bot:
        return

    # Age guard — skip backlog
    if _is_old(msg):
        return

    # Admin guard — groups only
    if chat.type != "private" and not await _is_admin(ctx.bot, chat.id):
        return

    text = (msg.text or msg.caption or "").strip()
    if not text:
        return

    loop = asyncio.get_event_loop()

    # Always track activity (no admin needed for tracking in group context already guarded above)
    loop.create_task(_track_activity(ctx.bot, user, chat, "text", text))

    # Save reply context
    if msg.reply_to_message and msg.reply_to_message.text:
        loop.create_task(
            db.save_chat_memory(
                chat.id,
                msg.reply_to_message.text[:60],
                reply_text=text[:200],
            )
        )

    _push_history(chat.id, "user", f"{user.first_name}: {text}")
    # ── Word Game answer check (isolated; can never block normal chat) ──
    try:
        from yuki.modules.wordgame.game import try_consume_guess
        if await try_consume_guess(ctx.bot, chat, user, msg, text):
            return
    except Exception as e:
        log.debug("Word game check failed (ignored): %s", e)

    # ── Decide whether Yuki should reply ──
    should_reply = False
    always_reply = False  # bypass cooldown

    if chat.type == "private":
        should_reply = True
        always_reply = True

    elif _bot_username and f"@{_bot_username}" in text.lower():
        # Direct mention → always reply
        should_reply = True
        always_reply = True

    elif (
        msg.reply_to_message
        and msg.reply_to_message.from_user
        and msg.reply_to_message.from_user.id == _bot_id
    ):
        # Reply to Yuki → always reply
        should_reply = True
        always_reply = True

    if not should_reply:
        return

    if not always_reply and not _can_reply(chat.id, user.id):
        return

    _mark_replied(chat.id, user.id)
    loop.create_task(_send_typing(chat.id, ctx))

    try:
        reply_text = await asyncio.wait_for(
            get_reply(
                text,
                history=_history[chat.id][:-1],
                user_name=user.first_name or "friend",
            ),
            timeout=7.0,
        )
    except Exception:
        reply_text = _smart_fallback(text)

    if not reply_text:
        return

    try:
        await msg.reply_text(reply_text, parse_mode="HTML")
        _push_history(chat.id, "assistant", reply_text)
    except Exception:
        try:
            # Fallback without parse_mode if HTML fails
            await msg.reply_text(reply_text)
            _push_history(chat.id, "assistant", reply_text)
        except Exception as e:
            log.warning("Reply failed: %s", e)
            return

    # Rare, natural sticker reaction — only in groups, heavily cooldown-limited
    if chat.type != "private" and _can_random_sticker(chat.id):
        if random.random() < RANDOM_STICKER_CHANCE:
            sticker_id = await get_random_sticker()
            if sticker_id:
                try:
                    await ctx.bot.send_sticker(chat_id=chat.id, sticker=sticker_id)
                    _mark_random_sticker(chat.id)
                except Exception:
                    pass


# ─────────────────────────────────────────────
# Media Handlers
# ─────────────────────────────────────────────

async def handle_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg  = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    if not msg or not user or not chat or user.is_bot:
        return
    if _is_old(msg):
        return
    if chat.type != "private" and not await _is_admin(ctx.bot, chat.id):
        return

    asyncio.get_event_loop().create_task(_track_activity(ctx.bot, user, chat, "photo"))


async def handle_video(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg  = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    if not msg or not user or not chat or user.is_bot:
        return
    if _is_old(msg):
        return
    if chat.type != "private" and not await _is_admin(ctx.bot, chat.id):
        return

    asyncio.get_event_loop().create_task(_track_activity(ctx.bot, user, chat, "video"))


async def handle_voice(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg  = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    if not msg or not user or not chat or user.is_bot:
        return
    if _is_old(msg):
        return
    if chat.type != "private" and not await _is_admin(ctx.bot, chat.id):
        return

    asyncio.get_event_loop().create_task(_track_activity(ctx.bot, user, chat, "voice"))


async def handle_sticker(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    - Age guard: ignores stickers sent before bot started
    - Admin guard: only works when Yuki is admin (groups)
    - Only replies when: DM, OR the sticker is a direct reply to Yuki's own message
    - Never reacts to random/ambient stickers in a group
    - Replies with a real sticker from the safe pool when possible
    """
    msg  = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    if not msg or not user or not chat or user.is_bot:
        return

    if _is_old(msg):
        return

    if chat.type != "private" and not await _is_admin(ctx.bot, chat.id):
        return

    asyncio.get_event_loop().create_task(_track_activity(ctx.bot, user, chat, "sticker"))

    in_dm = chat.type == "private"
    is_reply_to_yuki = (
        msg.reply_to_message
        and msg.reply_to_message.from_user
        and msg.reply_to_message.from_user.id == _bot_id
    )

    if not in_dm and not is_reply_to_yuki:
        return  # ignore ambient group stickers entirely

    if not _can_reply(chat.id, user.id):
        return

    _mark_replied(chat.id, user.id)

    sticker_id = await get_random_sticker()
    if sticker_id:
        try:
            await msg.reply_sticker(sticker=sticker_id)
            return
        except Exception as e:
            log.debug("Sticker reply failed, falling back to text: %s", e)

    try:
        from yuki.utils.brain import get_sticker_reply_text
        emoji = getattr(msg.sticker, "emoji", "") or ""
        reply_text = await get_sticker_reply_text(emoji)
        if reply_text:
            await msg.reply_text(reply_text, parse_mode="HTML")
    except Exception as e:
        log.debug("Sticker text fallback failed: %s", e)

# ------------------------------------------------
# PRIVATE CHAT
# ------------------------------------------------
    if in_dm:
       pass

# ------------------------------------------------
# GROUP
# ------------------------------------------------
    else:

    # Cooldown
      if not _can_sticker_reply(chat.id):
        return

      if not _can_reply(chat.id, user.id):
        return

      should_reply = False

    # User replied to Yuki
      if (
        msg.reply_to_message
        and msg.reply_to_message.from_user
        and msg.reply_to_message.from_user.id == _bot_id
      ):
        should_reply = True

    # Small random chance for natural behaviour
      elif random.randint(1, 100) <= 8:
        should_reply = True

      if not should_reply:
         return

    _mark_replied(chat.id, user.id)
    _mark_sticker(chat.id)

    emoji = getattr(msg.sticker, "emoji", "") or "🙂"

    try:
       from yuki.utils.brain import get_sticker_reply_text

       reply_text = await asyncio.wait_for(
          get_sticker_reply_text(emoji),
          timeout=5,
       )

       if reply_text:
          await msg.reply_text(
             reply_text,
             parse_mode="HTML",
          )

    except Exception as e:
        log.debug("Sticker reply failed: %s", e)


# ─────────────────────────────────────────────
# Handlers
# ─────────────────────────────────────────────

text_handler    = MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)
photo_handler   = MessageHandler(filters.PHOTO, handle_photo)
video_handler   = MessageHandler(filters.VIDEO | filters.ANIMATION, handle_video)
voice_handler   = MessageHandler(filters.VOICE | filters.AUDIO, handle_voice)
sticker_handler = MessageHandler(filters.Sticker.ALL, handle_sticker)
