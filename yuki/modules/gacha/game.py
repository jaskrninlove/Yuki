"""
Yuki Gacha
Copyright © Jass
"""

from __future__ import annotations

import io
import random
import logging
log = logging.getLogger("yuki.gacha")
from telegram import Update, InputFile, InputMediaPhoto
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

from yuki.database.economy import get as get_economy, remove, add_withdraw
from yuki.database.gacha import (
    add_companion,
    get_collection,
    get_companion_count,
    unlocked_count,
    has_claimed_completion,
    mark_completion_claimed,
)
from yuki.utils.rewards import GACHA_COMPLETION_REWARD
from yuki.utils.gacha_data import (
    COMPANIONS,
    COMPANIONS_BY_RARITY,
    RARITY_WEIGHTS,
    RARITY_LABELS,
    RARITY_ORDER,
    TOTAL_COMPANIONS,
    get_card_bytes,
)
from yuki.utils.gacha_render import render_gacha_card, render_collection_banner
from yuki.utils.premium import reply, render as premium_render
from yuki.utils.keyboards import collection_keyboard, collection_card_keyboard

PULL_COST = 100
PER_PAGE = 8


def _roll_companion() -> tuple[str, dict]:
    rarity = random.choices(
        list(RARITY_WEIGHTS.keys()),
        weights=list(RARITY_WEIGHTS.values()),
        k=1,
    )[0]
    companion_id = random.choice(COMPANIONS_BY_RARITY[rarity])
    return companion_id, COMPANIONS[companion_id]


def _get_card_image(companion_id: str, data: dict, is_new: bool) -> bytes:
    card_bytes = get_card_bytes(companion_id)
    if card_bytes:
        return card_bytes
    return render_gacha_card(data["name"], data["emoji"], data["rarity"], is_new)


# ==========================================================
# /gacha — pull
# ==========================================================

async def gacha_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user

    eco = get_economy(user.id)

    if eco["balance"] < PULL_COST:
        return await reply(
            message,
            f"""
:warning: <b>Not Enough Coins</b>

A pull costs <code>{PULL_COST}</code> coins.
Your balance: <code>{eco['balance']:,}</code>
""",
        )

    remove(user.id, PULL_COST)

    companion_id, data = _roll_companion()

    had_before = get_companion_count(user.id, companion_id)
    add_companion(user.id, companion_id)
    is_new = had_before == 0
    completion_bonus_text = ""
    if unlocked_count(user.id) == TOTAL_COMPANIONS and not has_claimed_completion(user.id):
        mark_completion_claimed(user.id)
        add_withdraw(user.id, GACHA_COMPLETION_REWARD)
        completion_bonus_text = f"""

:tada: <b>COLLECTION COMPLETE!!</b>

You've unlocked all {TOTAL_COMPANIONS} companions~
:gift: <code>+${GACHA_COMPLETION_REWARD}</code> added to your withdrawable balance!
"""

    image_bytes = _get_card_image(companion_id, data, is_new)

    caption = f"""
:sparkle: <b>{data['name']}</b> {data['emoji']}

:gem: Rarity: <b>{RARITY_LABELS[data['rarity']]}</b>
{":gift: <b>New companion unlocked!</b>" if is_new else ":repebroken_heartat: You already have this one~"}

Use <code>/collection</code> to see your full roster!
{completion_bonus_text}
"""

    await message.reply_photo(
        photo=InputFile(io.BytesIO(image_bytes), filename="gacha.png"),
        caption=premium_render(caption),
        parse_mode="HTML",
    )


# ==========================================================
# /collection — paginated owned-companion browser (single edited message)
# ==========================================================

def _owned_ids_sorted(user_id: int) -> list[str]:
    doc = get_collection(user_id)
    owned = doc.get("companions", {})
    ordered = []
    for rarity in RARITY_ORDER:
        for cid in COMPANIONS_BY_RARITY[rarity]:
            if cid in owned:
                ordered.append(cid)
    return ordered


def _collection_caption(user, doc) -> str:
    owned = doc.get("companions", {})
    return f"""
:ribbon: <b>{user.full_name}'s Collection</b>

:trophy: <b>Unlocked</b> <code>{len(owned)}/{TOTAL_COMPANIONS}</code>
:diamond: <b>Total Pulls</b> <code>{doc.get('total_pulls', 0):,}</code>

Tap a companion below to view their card~
"""


async def collection_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user

    doc = get_collection(user.id)
    owned_ids = _owned_ids_sorted(user.id)

    if not owned_ids:
        return await reply(
            message,
            """
:ribbon: <b>Your Collection is Empty~</b>

Use <code>/gacha</code> to pull your first companion!
""",
        )

    total_pages = max(1, (len(owned_ids) + PER_PAGE - 1) // PER_PAGE)
    page = 1
    page_ids = owned_ids[:PER_PAGE]

    banner = render_collection_banner(len(doc.get("companions", {})), TOTAL_COMPANIONS)

    await message.reply_photo(
        photo=InputFile(io.BytesIO(banner), filename="collection.png"),
        caption=premium_render(_collection_caption(user, doc)),
        parse_mode="HTML",
        reply_markup=collection_keyboard(page_ids, COMPANIONS, page, total_pages),
    )


# ==========================================================
# Callbacks — all edit the same message (media/caption swap only)
# ==========================================================

async def collection_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = update.effective_user
    await query.answer()

    page = int(query.data.split(":")[1])

    doc = get_collection(user.id)
    owned_ids = _owned_ids_sorted(user.id)
    total_pages = max(1, (len(owned_ids) + PER_PAGE - 1) // PER_PAGE)
    page = max(1, min(page, total_pages))

    start = (page - 1) * PER_PAGE
    page_ids = owned_ids[start:start + PER_PAGE]

    # Only the caption/keyboard change across pages — banner image stays the same.
    try:
        await query.edit_message_caption(
            caption=premium_render(_collection_caption(user, doc)),
            parse_mode="HTML",
            reply_markup=collection_keyboard(page_ids, COMPANIONS, page, total_pages),
        )
    except Exception as e:
        log.warning("collection_page_callback failed: %s", e)


async def collection_card_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = update.effective_user
    await query.answer()

    _, companion_id, page = query.data.split(":")
    page = int(page)

    data = COMPANIONS.get(companion_id)
    if not data:
        await query.answer("Companion not found~", show_alert=True)
        return

    count = get_companion_count(user.id, companion_id)
    image_bytes = _get_card_image(companion_id, data, is_new=False)

    caption = f"""
:sparkle: <b>{data['name']}</b> {data['emoji']}

Rarity: <b>{RARITY_LABELS[data['rarity']]}</b>
Owned: <code>x{count}</code>
"""

    try:
        photo_buf = io.BytesIO(image_bytes)
        photo_buf.name = "gacha.png"
        await query.edit_message_media(
            media=InputMediaPhoto(
                media=photo_buf,
                caption=premium_render(caption),
                parse_mode="HTML",
            ),
            reply_markup=collection_card_keyboard(page),
        )
    except Exception as e:
        log.warning("collection_card_callback failed: %s", e)


async def collection_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = update.effective_user
    await query.answer()

    page = int(query.data.split(":")[1])

    doc = get_collection(user.id)
    owned_ids = _owned_ids_sorted(user.id)
    total_pages = max(1, (len(owned_ids) + PER_PAGE - 1) // PER_PAGE)
    page = max(1, min(page, total_pages))

    start = (page - 1) * PER_PAGE
    page_ids = owned_ids[start:start + PER_PAGE]

    banner = render_collection_banner(len(doc.get("companions", {})), TOTAL_COMPANIONS)

    try:
        banner_buf = io.BytesIO(banner)
        banner_buf.name = "collection.png"
        await query.edit_message_media(
            media=InputMediaPhoto(
                media=banner_buf,
                caption=premium_render(_collection_caption(user, doc)),
                parse_mode="HTML",
            ),
            reply_markup=collection_keyboard(page_ids, COMPANIONS, page, total_pages),
        )
    except Exception as e:
        log.warning("collection_back_callback failed: %s", e)


# ==========================================================
# Handlers
# ==========================================================

GACHA = CommandHandler(["gacha", "pull"], gacha_cmd)
COLLECTION = CommandHandler(["collection", "mycompanions"], collection_cmd)
COLLECTION_PAGE_CB = CallbackQueryHandler(collection_page_callback, pattern=r"^col_page:\d+$")
COLLECTION_CARD_CB = CallbackQueryHandler(collection_card_callback, pattern=r"^col_card:")
COLLECTION_BACK_CB = CallbackQueryHandler(collection_back_callback, pattern=r"^col_back:\d+$")