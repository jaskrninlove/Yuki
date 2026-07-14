"""
Yuki XP Listener
Copyright © Jass

Automatically rewards users with XP while chatting.
"""

from __future__ import annotations

import time

from telegram import Update
from telegram.ext import (
    ContextTypes,
    MessageHandler,
    filters,
)

from yuki.core.database import (
    ensure_user,
    increment_user_messages,
    add_xp,
)

from yuki.utils.xp import (
    MESSAGE_COOLDOWN,
    random_xp,
)

# ==========================================================
# Cooldown Cache
# ==========================================================

XP_CACHE: dict[int, float] = {}


# ==========================================================
# XP Listener
# ==========================================================

async def xp_listener(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message

    if not message:
        return

    user = update.effective_user

    if not user or user.is_bot:
        return

    # Ensure user exists
    await ensure_user(
        user.id,
        first_name=user.first_name or "",
        username=user.username or "",
    )

    # Count every message
    await increment_user_messages(user.id, message.chat_id)

    # Cooldown
    now = time.time()
    last = XP_CACHE.get(user.id, 0)

    if now - last < MESSAGE_COOLDOWN:
        return

    XP_CACHE[user.id] = now

    gained = random_xp()
    await add_xp(user.id, gained)


# ==========================================================
# Handler
# ==========================================================

XP_HANDLER = MessageHandler(
    filters.TEXT
    & ~filters.COMMAND
    & ~filters.UpdateType.EDITED_MESSAGE,
    xp_listener,
)