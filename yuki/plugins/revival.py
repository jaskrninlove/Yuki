"""
Yuki Bot - GC Revival Plugin
Automatically revives silent group chats after configurable timeout.
"""

import logging
from datetime import datetime, timedelta

from telegram.ext import Application

from yuki.core.config import AUTO_REVIVE_MINUTES, AUTO_REVIVE_ENABLED
from yuki.core import database as db
from yuki.utils.brain import get_revival_message

log = logging.getLogger("yuki.plugins.revival")

# chat_id -> last message datetime
_last_activity: dict[int, datetime] = {}


def update_activity(chat_id: int):
    """Call this from the chat handler on every message."""
    _last_activity[chat_id] = datetime.utcnow()


async def revival_job(context):
    """Scheduled job — check all registered groups."""
    if not AUTO_REVIVE_ENABLED:
        return

    now       = datetime.utcnow()
    threshold = timedelta(minutes=AUTO_REVIVE_MINUTES)

    # Get all group chat IDs from DB
    try:
        db_obj = db.get_db()
        cursor = db_obj.groups.find({"auto_revive": True}, {"chat_id": 1})
        groups = [doc["chat_id"] async for doc in cursor]
    except Exception:
        return

    for chat_id in groups:
        last = _last_activity.get(chat_id)
        if last and (now - last) < threshold:
            continue  # Still active

        try:
            msg = await get_revival_message()
            await context.bot.send_message(chat_id, msg)
            _last_activity[chat_id] = now  # Reset timer
            log.info("Revived chat %s", chat_id)
        except Exception as e:
            log.debug("Failed to revive chat %s: %s", chat_id, e)


def register_revival_job(app: Application, interval_seconds: int = 300):
    """Register the revival job with the job queue."""
    app.job_queue.run_repeating(
        revival_job,
        interval=interval_seconds,
        first=60,
        name="gc_revival",
    )
    log.info("✅ GC revival job registered (every %ds)", interval_seconds)
