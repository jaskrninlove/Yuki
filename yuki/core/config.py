"""
Yuki Bot - Configuration
All settings pulled from environment variables + permanent config here.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Bot Core ────────────────────────────────────────────────────────────────
BOT_TOKEN: str = os.environ.get("BOT_TOKEN", "")
BOT_NAME: str = "Yuki"
BOT_VERSION: str = "1.0.0"
BOT_PREFIX: str = "/"

# ── Telegram IDs ────────────────────────────────────────────────────────────
OWNER_ID: int = int(os.environ.get("OWNER_ID", "0"))
OWNER_USERNAME: str = os.environ.get("OWNER_USERNAME", "imceobiitxh")

# ── Permanent Channel / Group Links ─────────────────────────────────────────
SUPPORT_LINK: str = os.environ.get("SUPPORT_LINK", "https://t.me/xenorachatz")
UPDATES_CHANNEL: str = os.environ.get("UPDATES_CHANNEL", "https://t.me/xenoraorg")
LOG_GROUP_ID: int = int(os.environ.get("LOG_GROUP_ID", "0"))

# ── MongoDB ──────────────────────────────────────────────────────────────────
MONGO_URI: str = os.environ.get("MONGO_URI", "")
MONGO_DB_NAME: str = os.environ.get("MONGO_DB_NAME", "yukidb")

# ── Telethon (for @all tagging) ───────────────────────────────────────────
API_ID: int = int(os.environ.get("API_ID", "0"))
API_HASH: str = os.environ.get("API_HASH", "")
SESSION_STRING: str = os.environ.get("SESSION_STRING", "")

# ── Images (permanent) ───────────────────────────────────────────────────────
# Telegram file_ids for images — set these after first upload
START_IMAGE: str = os.environ.get(
    "START_IMAGE",
    "https://i.pinimg.com/736x/56/99/4a/56994a1d2418fd279a5e05e5f32e06fe.jpg"   # replace with real file_id
)
PING_IMAGE: str = os.environ.get(
    "PING_IMAGE",
    "https://i.pinimg.com/736x/56/99/4a/56994a1d2418fd279a5e05e5f32e06fe.jpg"    # replace with real file_id
)
OWNER_IMAGE: str = os.environ.get(
    "OWNER_IMAGE",
    "https://i.pinimg.com/736x/56/99/4a/56994a1d2418fd279a5e05e5f32e06fe.jpg"   # replace with real file_id
)
RANKING_IMAGE: str = os.environ.get(
    "RANKING_IMAGE",
    "https://i.pinimg.com/736x/db/03/db/db03db52c309fdca55792ea7cdec416d.jpg"
)

# ── AI Chat (OpenAI / any compatible API) ────────────────────────────────────
AI_API_KEY: str = os.environ.get("AI_API_KEY", "")
AI_BASE_URL: str = os.environ.get("AI_BASE_URL", "https://api.groq.com/openai/v1")
AI_MODEL: str = os.environ.get("AI_MODEL", "llama-3.1-8b-instant")

# ── Auto-Revive ───────────────────────────────────────────────────────────────
# Minutes of silence before Yuki pings the group
AUTO_REVIVE_MINUTES: int = int(os.environ.get("AUTO_REVIVE_MINUTES", "30"))
AUTO_REVIVE_ENABLED: bool = os.environ.get("AUTO_REVIVE_ENABLED", "true").lower() == "true"

# ── Sticker Learning ──────────────────────────────────────────────────────────
MAX_STICKER_POOL: int = int(os.environ.get("MAX_STICKER_POOL", "500"))

# ── Maintenance Mode (runtime toggle, stored in DB) ──────────────────────────
MAINTENANCE_MODE: bool = False

# ── Webhook (optional, for production) ───────────────────────────────────────
WEBHOOK: bool = os.environ.get("WEBHOOK", "false").lower() == "true"
WEBHOOK_URL: str = os.environ.get("WEBHOOK_URL", "")
PORT: int = int(os.environ.get("PORT", "8443"))

# ── Quote Sticker Service ─────────────────────────────────────────────────────
QUOTLY_API: str = "https://bot.lyo.su/quote/generate"

from pymongo import MongoClient

client = MongoClient(MONGO_URI)

DB = client[MONGO_DB_NAME]

# ── Validation ───────────────────────────────────────────────────────────────
def validate():
    missing = []
    if not BOT_TOKEN:
        missing.append("BOT_TOKEN")
    if not MONGO_URI:
        missing.append("MONGO_URI")
    if not OWNER_ID:
        missing.append("OWNER_ID")
    if missing:
        raise EnvironmentError(
            f"❌ Missing required environment variables: {', '.join(missing)}\n"
            f"Please check your .env file."
        )
