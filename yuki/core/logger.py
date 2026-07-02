"""
Yuki Bot - Logger Setup
Structured, colorful logging with group relay support.
"""

import asyncio
import html
import logging
import sys
from pathlib import Path

LOG_FILE = Path("logs/yuki.log")
LOG_FILE.parent.mkdir(exist_ok=True)

RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"


class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: CYAN,
        logging.INFO: GREEN,
        logging.WARNING: YELLOW,
        logging.ERROR: RED,
        logging.CRITICAL: MAGENTA + BOLD,
    }

    def format(self, record: logging.LogRecord) -> str:
        old_levelname = record.levelname
        old_name = record.name

        color = self.COLORS.get(record.levelno, RESET)
        record.levelname = f"{color}{old_levelname:<8}{RESET}"
        record.name = f"{CYAN}{old_name}{RESET}"

        result = super().format(record)

        record.levelname = old_levelname
        record.name = old_name
        return result


def setup_logging(level: str = "INFO"):
    fmt = "%(asctime)s | %(levelname)s | %(name)s — %(message)s"
    date_fmt = "%Y-%m-%d %H:%M:%S"

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    root.handlers.clear()

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(ColorFormatter(fmt=fmt, datefmt=date_fmt))
    root.addHandler(console)

    file_h = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_h.setFormatter(logging.Formatter(fmt=fmt, datefmt=date_fmt))
    root.addHandler(file_h)

    for lib in ("httpx", "telegram.ext", "httpcore", "hpack", "apscheduler"):
        logging.getLogger(lib).setLevel(logging.WARNING)

    logging.getLogger("yuki").info("✨ Logger initialized — Yuki is waking up~")


class TelegramLogHandler(logging.Handler):
    """Forward INFO+ Yuki logs to logger group."""

    def __init__(self, bot, chat_id: int):
        super().__init__(level=logging.INFO)
        self._bot = bot
        self._chat_id = chat_id
        self._closed = False

    def close(self):
        self._closed = True
        super().close()

    def emit(self, record: logging.LogRecord):
        # shutdown ke time async task create mat karo
        if self._closed:
            return

        try:
            if not str(record.name).startswith("yuki"):
                return

            # shutdown/disconnect logs ko Telegram pe relay mat karo
            msg_raw = record.getMessage().lower()
            if "shutting down" in msg_raw or "disconnected" in msg_raw:
                return

            import asyncio
            import html

            msg = self.format(record)
            msg = html.escape(msg)

            icon = "ℹ️"
            if record.levelno >= logging.CRITICAL:
                icon = "🚨"
            elif record.levelno >= logging.ERROR:
                icon = "🔴"
            elif record.levelno >= logging.WARNING:
                icon = "🟡"
            elif record.levelno >= logging.INFO:
                icon = "🟢"

            text = (
                f"{icon} <b>Yuki Log</b>\n\n"
                f"<blockquote>{msg[:3000]}</blockquote>"
            )

            loop = asyncio.get_running_loop()

            if not loop.is_running() or loop.is_closed():
                return

            task = loop.create_task(
                self._safe_send(text)
            )
            task.add_done_callback(lambda t: t.exception() if not t.cancelled() else None)

        except Exception:
            pass

    async def _safe_send(self, text: str):
        try:
            await self._bot.send_message(
                chat_id=self._chat_id,
                text=text,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
        except Exception:
            pass

def attach_telegram_handler(bot, log_group_id: int):
    if not log_group_id:
        return

    handler = TelegramLogHandler(bot, log_group_id)
    handler.setLevel(logging.ERROR)

    fmt = "%(asctime)s | %(levelname)s | %(name)s — %(message)s"
    date_fmt = "%Y-%m-%d %H:%M:%S"
    handler.setFormatter(logging.Formatter(fmt=fmt, datefmt=date_fmt))

    logging.getLogger("yuki").addHandler(handler)


async def send_log(bot, chat_id: int, text: str):
    """Manual log sender for start/add events."""
    if not chat_id:
        return

    try:
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
    except Exception:
        pass