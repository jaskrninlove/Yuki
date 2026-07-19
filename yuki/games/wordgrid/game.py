"""
Yuki Word Grid Game
Copyright © Jass
"""

from __future__ import annotations

import io
import logging
from pathlib import Path
from dataclasses import dataclass, field

from telegram import Update, InputFile, InputMediaPhoto, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram import InlineKeyboardMarkup
from yuki.utils.keyboards import pbtn
from yuki.database.economy import add, add_withdraw
from yuki.utils.wordgrid_gen import generate_grid, pick_words
from yuki.utils.wordgrid_render import render_grid_image
from yuki.utils.premium import reply, render as premium_render

log = logging.getLogger("yuki.wordgrid")

GRID_SIZE = 8
LENGTH_TARGETS = [3, 3, 3, 4, 4, 5, 5, 6, 6, 6]

WIN_BALANCE = {1: 500, 2: 350, 3: 200}
WIN_WITHDRAW = {1: 10, 2: 7, 3: 5}

# ── FIX 1: dedicated word pool for the grid (needs 3-letter words too,
# unlike the scramble game's word_list.py which excludes them on purpose) ──
_WORDGRID_WORDS: list[str] = []
_WORDGRID_LOADED = False

_WORDS_FILE = Path(__file__).parent.parent.parent / "assets" / "words.txt"
_WORDGRID_MIN_LEN = 3
_WORDGRID_MAX_LEN = 6


def _load_wordgrid_pool():
    global _WORDGRID_WORDS, _WORDGRID_LOADED
    if _WORDGRID_LOADED:
        return

    words = set()
    if _WORDS_FILE.exists():
        with open(_WORDS_FILE, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                w = line.strip().lower()
                if w.isalpha() and _WORDGRID_MIN_LEN <= len(w) <= _WORDGRID_MAX_LEN:
                    words.add(w)

    _WORDGRID_WORDS = list(words)
    _WORDGRID_LOADED = True


@dataclass
class GridGame:
    chat_id: int
    grid: list
    placements: dict          # WORD -> path
    found: dict = field(default_factory=dict)   # WORD -> (path, user_id)
    scores: dict = field(default_factory=dict)  # user_id -> {"name": str, "points": int}
    message_id: int | None = None

    def points_for(self, word: str) -> int:
        return max(2, (len(word) - 2) * 2)

    def is_complete(self) -> bool:
        return len(self.found) == len(self.placements)


_active_grids: dict[int, GridGame] = {}


def _masked_line(word: str, solved: bool) -> str:
    if solved:
        return f":check: <b>{word}</b>"
    return f"{word[0]}{'—' * (len(word) - 1)} ({len(word)})"


def _build_caption(game: GridGame) -> str:
    lines = [":grid: <b>WORD GRID CHALLENGE</b> :grid:\n", "Find these words:"]
    for word in sorted(game.placements.keys(), key=len):
        solved = word in game.found
        lines.append(_masked_line(word, solved))
    lines.append("\n<i>Just type a word in chat to guess it!</i>")
    return "\n".join(lines)


def _grid_keyboard(chat_id: int):
    return InlineKeyboardMarkup(
        [
            [
                pbtn(
                    " Refresh",
                    callback_data=f"wg_refresh:{chat_id}",
                    style="primary",
                    icon="refresh",
                )
            ]
        ]
    )


async def _push_grid_update(ctx: ContextTypes.DEFAULT_TYPE, game: GridGame):
    image_bytes = render_grid_image(game.grid, [p for p, _ in game.found.values()])
    caption = premium_render(_build_caption(game))

    try:
        await ctx.bot.edit_message_media(
            chat_id=game.chat_id,
            message_id=game.message_id,
            media=InputMediaPhoto(
                media=io.BytesIO(image_bytes),
                caption=caption,
                parse_mode="HTML",
            ),
            reply_markup=_grid_keyboard(game.chat_id),
        )
    except Exception as e:
        log.debug("Grid update failed: %s", e)


# ==========================================================
# /newgrid — start a round
# ==========================================================

async def new_grid_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat = update.effective_chat

    if chat.type == "private":
        return await reply(msg, ":warning: Word Grid can only be played in groups~")

    if chat.id in _active_grids:
        return await reply(msg, ":warning: A grid is already active here! Solve it first~")

    _load_wordgrid_pool()
    pool = list(_WORDGRID_WORDS)
    words = pick_words(pool, LENGTH_TARGETS)

    if len(words) < 5:
        return await reply(msg, ":warning: Not enough words available to build a grid right now.")

    try:
        grid, placements = generate_grid(words, size=GRID_SIZE)
    except RuntimeError:
        return await reply(msg, ":warning: Couldn't build a grid this time, try /newgrid again~")

    game = GridGame(chat_id=chat.id, grid=grid, placements=placements)
    _active_grids[chat.id] = game

    image_bytes = render_grid_image(grid, [])
    caption = premium_render(_build_caption(game))

    sent = await ctx.bot.send_photo(
        chat_id=chat.id,
        photo=InputFile(io.BytesIO(image_bytes), filename="grid.png"),
        caption=caption,
        parse_mode="HTML",
        reply_markup=_grid_keyboard(chat.id),
    )
    game.message_id = sent.message_id


# ==========================================================
# Guess listener
# ==========================================================

async def _wordgrid_guess_listener_inner(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    if not message or not user or user.is_bot or not message.text:
        return

    game = _active_grids.get(chat.id)
    if not game:
        return

    guess = message.text.strip().upper()

    if guess not in game.placements or guess in game.found:
        return

    path = game.placements[guess]
    game.found[guess] = (path, user.id)

    points = game.points_for(guess)
    score_entry = game.scores.setdefault(user.id, {"name": user.full_name, "points": 0})
    score_entry["points"] += points
    from yuki.database.wordgrid_stats import log_points
    log_points(user.id, chat.id, user.full_name, points)

    grid_link = f"https://t.me/c/{str(chat.id)[4:]}/{game.message_id}" if str(chat.id).startswith("-100") else None
     
    kb = None
    if grid_link:
        kb = InlineKeyboardMarkup(
            [
                [
                    pbtn(
                        "Go to Grid",
                        url=grid_link,
                        style="primary",
                        icon="grid",
                    )
                ]
            ]
        )

    await reply(
        message,
        f""":check: <b>+{points} points</b> for {user.full_name}! You found <b>{guess}</b>.""",
        reply_markup=kb,
    )

    await _push_grid_update(ctx, game)

    if game.is_complete():
        await _finish_round(ctx, game)


async def wordgrid_guess_listener(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        await _wordgrid_guess_listener_inner(update, ctx)
    except Exception as e:
        log.warning("Guess listener failed: %s", e)


async def refresh_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = int(query.data.split(":")[1])

    game = _active_grids.get(chat_id)
    if not game:
        await query.answer("No active grid~", show_alert=True)
        return

    await query.answer("Refreshed!")
    await _push_grid_update(ctx, game)


# Replace _finish_round in yuki/modules/wordgrid/game.py (or wherever this lives) with this version.

async def _finish_round(ctx: ContextTypes.DEFAULT_TYPE, game: GridGame):
    from yuki.utils import premium

    ranking = sorted(game.scores.items(), key=lambda kv: kv[1]["points"], reverse=True)

    lines = [":party: :ek::do::teen::char::panch::six: :party:\n", "<blockquote>--- Round Summary ---\n"]

    medal_icons = [":gold:", ":silver:", ":bronze:"]

    for i, (uid, data) in enumerate(ranking):
        medal = medal_icons[i] if i < 3 else f":onlyb: {i + 1}."
        line = f"{medal} <b>{data['name']}</b> — <code>{data['points']}</code> pts"

        if i < 3:
            bal_bonus = WIN_BALANCE[i + 1]
            wd_bonus = WIN_WITHDRAW[i + 1]
            add(uid, bal_bonus)
            add_withdraw(uid, wd_bonus)
            line += f"\n     :gold: +{bal_bonus} coins  •  :gem: +${wd_bonus} withdrawable"

        lines.append(line)

    lines.append("</blockquote>")
    lines.append("\nThanks for playing! Start another game with /newgrid.")

    keyboard = InlineKeyboardMarkup(
        [
            [
                pbtn(
                    " Support Group",
                    url="https://t.me/XenoraChatz",
                    style="primary",
                    icon="heart",
                )
            ]
        ]
    )

    await premium.send(ctx.bot, game.chat_id, "\n".join(lines), reply_markup=keyboard)
    _active_grids.pop(game.chat_id, None)

NEW_GRID = CommandHandler("newgrid", new_grid_cmd)
WORDGRID_GUESS_HANDLER = MessageHandler(
    filters.TEXT & ~filters.COMMAND & ~filters.UpdateType.EDITED_MESSAGE,
    wordgrid_guess_listener,
    block=False,
)
WORDGRID_REFRESH_CB = CallbackQueryHandler(refresh_callback, pattern=r"^wg_refresh:-?\d+$")