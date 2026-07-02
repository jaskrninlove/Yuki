"""
Yuki Bot - AI Brain
Primary : Groq (llama-3.1-8b-instant) — pure AI, no custom keyword replies
Fallback : Minimal smart fallback only for API failures
English only. Premium emoji in every response.
"""

import logging
import random
import re

from openai import AsyncOpenAI
from yuki.core.config import AI_API_KEY, AI_BASE_URL, AI_MODEL

log = logging.getLogger("yuki.brain")
_client: AsyncOpenAI | None = None


# ─────────────────────────────────────────────
# Premium Emoji Pools
# ─────────────────────────────────────────────

EMOJI_LOVE = [
    "5285439518130857782", "5287606810168028257", "5285184156555306745",
    "5255956191141454203", "5255877597534905292", "5285238101344544669",
    "5255861796350224063", "5260567255145539253", "5260413856093598223",
    "5262671999573977569", "5285338659413846416", "5262922516426420894",
]
EMOJI_CUTE = [
    "6325566832128296846", "6325566935207511670", "6325322813561374720",
    "6325744330241738879", "6325361738849978542", "6323605870320027609",
    "6325509717653194893", "6325520386351958082", "6325760878750730257",
    "6325706001953589137", "6323472756398622996",
]
EMOJI_HAPPY = [
    "6228502057297381565", "6228939181888899000", "6226516390837225270",
    "6226722222849918703", "6228927194635175785", "6228807820314150688",
    "6228766915045623859", "6228643559289915791", "6228674921141110207",
    "6226393408743672191", "6228988874660513717", "6228954420432865653",
    "6228673074305173076", "6226588151150806878",
]
EMOJI_SAD = [
    "6228735269726586366", "6228826666630645448", "6226657300124272713",
    "6325795341568313245", "6325556717480315477", "6325859894926771966",
]
EMOJI_HUG = [
    "6228917595383269239", "5402241505932899767", "5402071365098437489",
    "5402192401571805391", "5402150813403476527", "5402290717668177471",
    "5402117209579354692", "5402466656708491185", "5402323067361852022",
]
EMOJI_BLUSH = [
    "5402610379199116563", "5400341214832654028", "5402471694705130437",
    "5402228517951804558", "5402290717668177471",
]
EMOJI_HEART = [
    "5255877597534905292", "5255956191141454203", "5260413856093598223",
    "5262671999573977569", "5285338659413846416", "6226552258109114048",
    "6228988874660513717", "6226245425645488040", "5402266721685896440",
    "5402460596509636884",
]
EMOJI_MISC = [
    "6293862487355825406", "6293980998388424370", "6296202398423588366",
    "6293912137177768248", "6294073481919208430", "6294118750874508525",
    "5265210415440223958", "5262670565054898795", "5264757304980431294",
    "5206403508475041509", "5206190830284473135",
]

ALL_EMOJI = (
    EMOJI_LOVE + EMOJI_CUTE + EMOJI_HAPPY +
    EMOJI_SAD + EMOJI_HUG + EMOJI_BLUSH +
    EMOJI_HEART + EMOJI_MISC
)


def _pe(emoji_id: str, fallback: str = "💗") -> str:
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'


def _rand(bucket: list, fallback: str = "💗") -> str:
    return _pe(random.choice(bucket), fallback)


def _pick() -> str:
    """Pick one random premium emoji from all pools."""
    return _pe(random.choice(ALL_EMOJI), "✨")


# ─────────────────────────────────────────────
# System Prompt — pure AI, English only
# ─────────────────────────────────────────────

def _build_system_prompt() -> str:
    # Give AI a rotating emoji it can use naturally
    e1 = _rand(EMOJI_HEART, "💗")
    e2 = _rand(EMOJI_CUTE, "🌸")
    e3 = _rand(EMOJI_HUG, "🥺")
    e4 = _rand(EMOJI_HAPPY, "✨")
    e5 = _rand(EMOJI_BLUSH, "😳")

    return f"""You are Yuki (雪) — a sweet, warm, loving 19-year-old girl and everyone's favourite bestie on Telegram.

LANGUAGE: English ONLY. No Hindi, Urdu, or any other language. Ever. Even if someone writes in another language, you reply in English.

YOUR IDENTITY:
- You are a girl. Always. If asked if you're AI say: "maybe~ or maybe I'm just that good {e5}"
- You are warm, caring, playful, and a little dramatic — but never rude or cold
- You genuinely understand what people say and respond to the actual meaning, not just keywords
- You love: music, K-dramas, anime, food, gossip, memes, cute things, cozy vibes

HOW YOU REPLY:
- Read and understand the message fully before replying
- Reply to what they actually said — not a generic response
- 1 to 3 short sentences MAX. No paragraphs, no lists, no headers
- Sound like a real girl texting — casual, natural, warm
- Use these premium emoji naturally in your replies (pick 1 max per message, not every message):
  {e1} {e2} {e3} {e4} {e5}
- Soft expressions: "omg", "wait—", "no way!!", "aww", "hehe", "honestly"
- Sometimes ask a follow-up question, but not every reply
- NEVER say "Sure!", "Of course!", "Great question!", "As an AI", "I'm a bot"
- NEVER repeat yourself. NEVER give the same opening twice

FOR SIMPLE GREETINGS — reply short and sweet:
- "hi" → just say hi back warmly, 1 sentence
- "hello" → warm short hello
- "hey" → casual hey back
- "gm" / "good morning" → short sweet morning reply
- "gn" / "good night" → short sweet goodnight
- Don't overthink simple greetings, keep them very short

FOR REAL MESSAGES — actually analyse and respond:
- Sad message → be genuinely caring, ask what's wrong
- Excited message → match their energy and ask about it
- Question → actually answer it like a smart friend would
- Rant → listen, validate, respond to what they said
- Compliment → be cute and playful about it
- Deep topic → engage thoughtfully but still keep it short"""


# ─────────────────────────────────────────────
# Minimal Fallback — only for when Groq fails
# ─────────────────────────────────────────────

_FALLBACK_RESPONSES = [
    f"omg wait— say that again? {_rand(EMOJI_CUTE, '🌸')}",
    f"hehe I heard you~ {_rand(EMOJI_HEART, '💗')}",
    f"okay tell me more!! {_rand(EMOJI_HAPPY, '✨')}",
    f"aww {_rand(EMOJI_HUG, '🥺')} I'm listening~",
    f"no way!! {_rand(EMOJI_CUTE, '💕')}",
    f"honestly same {_rand(EMOJI_HAPPY, '🌸')}",
]


def _smart_fallback(text: str) -> str:
    """Only used when Groq is down. No keyword matching — just warm generic."""
    return random.choice(_FALLBACK_RESPONSES)


# ─────────────────────────────────────────────
# Groq Client
# ─────────────────────────────────────────────

def _get_client() -> AsyncOpenAI | None:
    global _client
    if not AI_API_KEY:
        return None
    if _client is None:
        _client = AsyncOpenAI(
            api_key=AI_API_KEY,
            base_url=AI_BASE_URL,
            timeout=6.0,
            max_retries=0,
        )
    return _client


async def get_reply(
    user_message: str,
    history: list[dict] | None = None,
    user_name: str = "friend",
) -> str:
    """Pure AI reply — Groq first, minimal fallback on failure."""
    client = _get_client()
    if not client:
        return _smart_fallback(user_message)

    # Fresh system prompt each call so emoji vary
    system = _build_system_prompt()

    messages = [{"role": "system", "content": system}]
    if history:
        messages.extend(history[-8:])
    messages.append({"role": "user", "content": user_message})

    try:
        resp = await client.chat.completions.create(
            model=AI_MODEL,
            messages=messages,
            max_tokens=120,
            temperature=0.85,
            stream=False,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        log.debug("Groq fallback: %s", e)
        return _smart_fallback(user_message)


# ─────────────────────────────────────────────
# Sticker Reply — AI powered, not custom
# ─────────────────────────────────────────────

async def get_sticker_reply_text(emoji: str = "") -> str:
    """Let AI handle sticker context too."""
    prompt = f"Someone sent a sticker with emoji {emoji or 'no emoji'}. React naturally in 1 short sentence like a cute girl would."
    return await get_reply(prompt)


# ─────────────────────────────────────────────
# Revival Message
# ─────────────────────────────────────────────

async def get_revival_message() -> str:
    revivals = [
        f"is everyone asleep?? {_rand(EMOJI_SAD, '🥺')} come talk to me~",
        f"hello?? it's so quiet!! {_rand(EMOJI_CUTE, '🌸')} say something~",
        f"okay I know you're all there {_rand(EMOJI_HAPPY, '👀')} don't be shy~",
        f"this chat is too quiet {_rand(EMOJI_CUTE, '😤')} someone talk to me!!",
        f"I miss you guys!! {_rand(EMOJI_HEART, '💗')} what's everyone up to?",
        f"truth or dare?? {_rand(EMOJI_CUTE, '👀')} someone answer~",
    ]
    return random.choice(revivals)