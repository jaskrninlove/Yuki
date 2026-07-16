"""
Yuki Word Game
Copyright © Jass

3x/day scrambled-word puzzle, first correct reply in the group wins.
"""

from __future__ import annotations

import io
import logging
import random
from datetime import datetime, time, timedelta, timezone

from telegram import Update, InputFile
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from yuki.core import database as core_db
from yuki.database.economy import add
from yuki.database.word_game import (
    set_active_puzzle,
    get_active_puzzle,
    clear_active_puzzle,
    record_attempt,
    record_solve,
    get_stats,
    try_claim_schedule_slot,
)
from yuki.utils.word_list import random_word, scramble
from yuki.utils.word_render import render_word_puzzle
from yuki.utils.keyboards import pbtn
from telegram import InlineKeyboardMarkup

log = logging.getLogger("yuki.wordgame")

REWARD_MIN = 15
REWARD_MAX = 40

# Daily send window, IST (UTC+5:30), converted to UTC internally.
IST_OFFSET = timedelta(hours=5, minutes=30)
WINDOW_START_IST = time(10, 0)
WINDOW_END_IST = time(23, 0)
SENDS_PER_DAY = 3
MIN_GAP_MINUTES = 90

_active_cache: dict[int, dict] = {}  # chat_id -> {word, scrambled, reward}


def _stats_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[pbtn(" My Solved Words", callback_data="wg_stats", style="primary", icon="star")]])


# ==========================================================
# Sending a puzzle
# ==========================================================

async def send_puzzle(bot, chat_id: int):
    word = random_word()
    if not word:
        log.warning("Word list is empty, skipping puzzle send.")
        return

    scrambled = scramble(word)
    reward = random.randint(REWARD_MIN, REWARD_MAX)

    image_bytes = render_word_puzzle(scrambled)

    caption = f"""
:sparkle: <b>Solve the Word!</b>

<blockquote>{scrambled.upper()}</blockquote>

Reply with the correct word to win!

:gift: <b>Reward</b> <code>{reward}</code> coins
"""

    try:
        from yuki.utils import premium
        sent = await bot.send_photo(
            chat_id=chat_id,
            photo=InputFile(io.BytesIO(image_bytes), filename="word_puzzle.png"),
            caption=premium.render(caption),
            parse_mode="HTML",
            reply_markup=_stats_keyboard(),
        )
    except Exception as e:
        log.warning("Failed to send word puzzle to %s: %s", chat_id, e)
        return

    set_active_puzzle(chat_id, word, scrambled, sent.message_id, reward)
    _active_cache[chat_id] = {"word": word, "scrambled": scrambled, "reward": reward}


# ==========================================================
# Answer listener
# ==========================================================

async def try_consume_guess(bot, chat, user, message, text: str) -> bool:
    """Checks if `text` solves the active puzzle in this chat.
    Returns True if solved (handles reward + announcement itself).
    Never raises — always safe to call from the main chat handler."""
    try:
        if not chat or not user or user.is_bot:
            return False

        puzzle = _active_cache.get(chat.id)
        if not puzzle:
            puzzle = get_active_puzzle(chat.id)
            if not puzzle:
                return False
            _active_cache[chat.id] = {
                "word": puzzle["word"],
                "scrambled": puzzle["scrambled"],
                "reward": puzzle["reward"],
            }
            puzzle = _active_cache[chat.id]

        guess = text.strip().lower()
        answer = puzzle["word"].strip().lower()

        if len(guess) != len(answer):
            return False

        if guess != answer:
            record_attempt(user.id)
            return False

        # Correct! Race won.
        reward = puzzle["reward"]

        _active_cache.pop(chat.id, None)
        clear_active_puzzle(chat.id)

        add(user.id, reward)
        record_solve(user.id, reward)

        from yuki.utils.helpers import mention_html
        from yuki.utils import premium

        await premium.reply(
            message,
            f"""
:tada: <b>Solved!</b>

{mention_html(user)} unscrambled it first~

:key: The word was <b>{puzzle['word'].upper()}</b>
:gift: <code>+{reward}</code> coins added to your balance!
""",
            disable_web_page_preview=True,
        )
        return True

    except Exception as e:
        log.warning("try_consume_guess failed: %s", e)
        return False

# ==========================================================
# "My Solved Words" button — private popup, doesn't touch the shared puzzle
# ==========================================================

async def word_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = update.effective_user

    stats = get_stats(user.id)

    await query.answer(
        f"📝 Attempts: {stats.get('attempts', 0)}\n"
        f"✅ Solved: {stats.get('solved', 0)}\n"
        f"🪙 Coins earned: {stats.get('coins_earned', 0)}",
        show_alert=True,
    )

WORD_STATS_CB = CallbackQueryHandler(word_stats_callback, pattern=r"^wg_stats$")


# ==========================================================
# Scheduling
# ==========================================================

def _random_times_in_range(start_utc: datetime, end_utc: datetime, count: int) -> list[datetime]:
    """Pick up to `count` random UTC datetimes between start and end,
    spaced by at least MIN_GAP_MINUTES where the window allows it."""
    window_minutes = int((end_utc - start_utc).total_seconds() / 60)
    if window_minutes <= 0:
        return []

    count = max(1, min(count, (window_minutes // max(MIN_GAP_MINUTES, 1)) + 1))
    count = min(count, window_minutes + 1)

    offsets = sorted(random.sample(range(window_minutes + 1), count))
    for _ in range(50):
        if all(offsets[i + 1] - offsets[i] >= MIN_GAP_MINUTES for i in range(len(offsets) - 1)):
            break
        offsets = sorted(random.sample(range(window_minutes + 1), count))

    return [start_utc + timedelta(minutes=m) for m in offsets]


async def _schedule_group_for_day(app, chat_id: int, base_date):
    date_str = base_date.isoformat()

    if not try_claim_schedule_slot(chat_id, date_str):
        return  # already scheduled today

    now_utc = datetime.utcnow()

    start_ist = datetime.combine(base_date, WINDOW_START_IST)
    end_ist = datetime.combine(base_date, WINDOW_END_IST)
    start_utc = start_ist - IST_OFFSET
    end_utc = end_ist - IST_OFFSET

    if now_utc >= end_utc:
        return  # today's window is fully over, nothing to schedule

    # Start from "now" (with a small buffer) if scheduling happens mid-window,
    # so late scheduling still guarantees sends for the rest of today.
    effective_start = max(now_utc + timedelta(minutes=2), start_utc)

    times = _random_times_in_range(effective_start, end_utc, SENDS_PER_DAY)

    for t in times:
        delay = (t - now_utc).total_seconds()
        if delay <= 0:
            continue
        app.job_queue.run_once(
            lambda ctx, cid=chat_id: ctx.application.create_task(send_puzzle(ctx.bot, cid)),
            when=delay,
            name=f"wordgame_{chat_id}_{t.isoformat()}",
        )

async def _daily_reschedule(context: ContextTypes.DEFAULT_TYPE):
    app = context.application
    groups_cursor = core_db.get_db().groups.find({"active": True}, {"chat_id": 1})
    today = datetime.utcnow().date()

    async for g in groups_cursor:
        chat_id = g.get("chat_id")
        if chat_id:
            await _schedule_group_for_day(app, chat_id, today)


def register_word_game_job(app):
    """Call once at startup, alongside the other register_*_job calls."""
    async def _startup(context: ContextTypes.DEFAULT_TYPE):
        await _daily_reschedule(context)

    app.job_queue.run_once(_startup, when=5)
    app.job_queue.run_daily(_daily_reschedule, time=time(0, 5, tzinfo=timezone.utc))

# ==========================================================
# Manual test trigger (owner only)
# ==========================================================

async def testword_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from yuki.core import config

    user = update.effective_user
    chat = update.effective_chat

    if user.id != config.OWNER_ID:
        return

    await send_puzzle(context.bot, chat.id)

    # Debug: reveal the answer directly so testing doesn't need DB access
    puzzle = get_active_puzzle(chat.id)
    if puzzle:
        await context.bot.send_message(
            chat_id=chat.id,
            text=f"[DEBUG] Answer is: {puzzle['word']}",
        )


TESTWORD_CMD = CommandHandler("testword", testword_cmd)
