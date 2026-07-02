"""
Yuki Bot - Vibes & Personality Plugin
Premium emoji supported.
"""

import logging
import random
import hashlib
from datetime import datetime

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from yuki.core import database as db
from yuki.utils.helpers import full_name, mention_html, admin_only
from yuki.utils import premium

log = logging.getLogger("yuki.plugins.vibes")


SHAYARIS = [
    ("تم ملو تو زندگی مکمل لگے،\nتم بنا ہر شے ادھوری لگے۔",
     "When you're here, life feels complete,\nWithout you, everything feels incomplete."),
    ("محبت وہ آگ ہے جو جلاتی بھی ہے،\nاور روشنی بھی دیتی ہے۔",
     "Love is that fire which burns you,\nyet also gives you light."),
    ("دل کی بات لبوں پہ آ نہیں پاتی،\nآنکھیں کہہ دیتی ہیں جو زبان نہ کہہ پائے۔",
     "What the heart holds, words can't say,\nEyes speak what lips cannot."),
    ("تیری یاد میں ہم کھو گئے ایسے،\nجیسے خواب میں خود کو بھول جائے کوئی۔",
     "Lost in memories of you,\nLike one forgets themselves in a dream."),
    ("ہر سانس میں تیرا نام ہے،\nہر دھڑکن میں تیرا کام ہے۔",
     "Your name in every breath I take,\nYour memory with every heartbeat."),
    ("زندگی ہے تو گم شم ہے,\nتم ہو تو ہر لمحہ حسیں ہے۔",
     "Life exists, yet feels quiet,\nWith you, every moment is beautiful."),
    ("پیار کی راہ میں کانٹے بھی ہیں،\nپر منزل پھر بھی خوبصورت ہے۔",
     "The path of love has thorns too,\nBut the destination is still beautiful."),
    ("تیری مسکان نے دل چرا لیا،\nاور ہم خود کو بھی بھول گئے۔",
     "Your smile stole my heart,\nAnd I forgot even myself."),
]


async def shayari_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    shayari, translation = random.choice(SHAYARIS)

    text = (
        ":flower2: <b>Shayari~</b>\n\n"
        f"<blockquote>{shayari}</blockquote>\n\n"
        f"<i>{translation}</i>\n\n"
        "<i>— Yuki :heart:</i>"
    )

    await premium.reply(msg, text)


SIGNS = {
    "aries": "♈ Aries",
    "taurus": "♉ Taurus",
    "gemini": "♊ Gemini",
    "cancer": "♋ Cancer",
    "leo": "♌ Leo",
    "virgo": "♍ Virgo",
    "libra": "♎ Libra",
    "scorpio": "♏ Scorpio",
    "sagittarius": "♐ Sagittarius",
    "capricorn": "♑ Capricorn",
    "aquarius": "♒ Aquarius",
    "pisces": "♓ Pisces",
}

HOROSCOPE_TEMPLATES = [
    "Today the stars are literally rooting for you~ :sparkle: {sign} energy is through the roof! Love: {love} | Luck: {luck} | Vibe: {vibe}",
    "Ohh {sign}~ the universe has plans for you today :clock: Love: {love} | Luck: {luck} | Vibe: {vibe}. Trust the process bestie~ :heart:",
    "Big day for {sign}!! :star: The cosmos are aligned just for you~ Love: {love} | Luck: {luck} | Vibe: {vibe}",
]

LOVE_SCORES = [
    ":heart: :heart: :heart: :heart: :heart:",
    ":heart: :heart: :heart: :heart: :whiteheart:",
    ":heart: :heart: :heart: :whiteheart: :whiteheart:",
    ":heart: :heart: :whiteheart: :whiteheart: :whiteheart:",
    ":heart: :whiteheart: :whiteheart: :whiteheart: :whiteheart:",
]

LUCK_SCORES = [
    ":success: :success: :success: :success: :success:",
    ":success: :success: :success: :success: :sparkle:",
    ":success: :success: :success: :sparkle: :sparkle:",
    ":success: :success: :sparkle: :sparkle: :sparkle:",
]

VIBES = [
    ":sparkle: Glowing",
    ":zap: On fire",
    ":flower: Soft & sweet",
    ":rocket: Unstoppable",
    ":whiteheart: Peaceful",
    ":cute: Emotional but beautiful",
    ":crown: Main character",
    ":clock: Mysterious",
]

DAILY_ADVICE = [
    "Someone is thinking about you today~ :search: :heart:",
    "Say yes to something unexpected today! :sparkle:",
    "Your kindness will come back to you tenfold~ :flower:",
    "A surprise is coming your way~ :ribbon:",
    "Today is YOUR day — own it! :heart:",
    "Reach out to someone you miss~ :pinkheart:",
    "Good things are loading... please wait~ :star:",
    "Your smile is someone's favourite thing today~ :cute:",
]


async def horoscope_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    args = ctx.args

    if not args:
        signs_list = " | ".join(SIGNS.keys())
        await premium.reply(
            msg,
            ":sparkle: <b>Which sign bestie?</b>\n\n"
            "Usage: <code>/horoscope aries</code>\n\n"
            f"<i>Signs: {signs_list}</i>",
        )
        return

    sign_key = args[0].lower()

    if sign_key not in SIGNS:
        await premium.reply(
            msg,
            ":search: I don't know that sign~ try: aries, leo, scorpio, etc. :heart:",
        )
        return

    sign_name = SIGNS[sign_key]
    seed = int(hashlib.md5(f"{sign_key}{datetime.utcnow().date()}".encode()).hexdigest(), 16)
    rng = random.Random(seed)

    love = rng.choice(LOVE_SCORES)
    luck = rng.choice(LUCK_SCORES)
    vibe = rng.choice(VIBES)
    advice = rng.choice(DAILY_ADVICE)
    tmpl = rng.choice(HOROSCOPE_TEMPLATES)

    reading = tmpl.format(sign=sign_name, love=love, luck=luck, vibe=vibe)

    text = (
        f":sparkle: <b>Daily Horoscope — {sign_name}</b>\n"
        f"<i>{datetime.utcnow().strftime('%d %B %Y')}</i>\n\n"
        f"<blockquote>{reading}</blockquote>\n\n"
        f":star: <b>Yuki says:</b> <i>{advice}</i>\n\n"
        "<i>— Read by Yuki with love~ :heart:</i>"
    )

    await premium.reply(msg, text)


LETTER_INTROS = [
    "My dearest {name},\n\nEvery time I see your messages light up the chat, my heart does a little dance~ :heart:",
    "To the wonderful {name},\n\nWords can barely capture how special you are to everyone here~ :flower:",
    "Hey {name}~\n\nI've been meaning to tell you this for a while now... :pinkheart:",
]

LETTER_MIDDLES = [
    "Your energy brightens every conversation, and the group just isn't the same without you.",
    "There's something magical about the way you talk — it makes everyone feel seen and heard.",
    "You bring the most wonderful chaos and laughter to everything, and honestly? We need more of that.",
]

LETTER_ENDS = [
    "\n\nDon't ever forget how loved you are~ :heart:\n\nForever yours,\n<b>Yuki :flower:</b>",
    "\n\nStay exactly as wonderful as you are~ :sparkle:\n\nWith all my heart,\n<b>Yuki :heart:</b>",
    "\n\nYou deserve every good thing~ :cute:\n\nAlways,\n<b>Yuki :ribbon:</b>",
]


async def loveletter_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    sender = update.effective_user
    target = msg.reply_to_message.from_user if msg.reply_to_message else None

    if not target:
        await premium.reply(
            msg,
            ":mail: <b>Reply to someone</b> and use /loveletter~\n\n"
            "I'll write them the most beautiful letter :flower:",
        )
        return

    if target.id == sender.id:
        await premium.reply(
            msg,
            "Hehe~ you want a love letter for yourself? That's kinda cute but reply to someone else :heart:",
        )
        return

    name = full_name(target)

    letter = (
        f":mail: <b>A Letter for {mention_html(target)}~</b>\n\n"
        "<blockquote>"
        f"{random.choice(LETTER_INTROS).format(name=name)}\n\n"
        f"{random.choice(LETTER_MIDDLES)}"
        f"{random.choice(LETTER_ENDS)}"
        "</blockquote>"
    )

    await premium.reply(msg, letter, disable_web_page_preview=True)


ROASTS = [
    "I'd roast you but my mama said I'm not allowed to burn trash~ :heart:",
    "You're not stupid, you just have bad luck thinking~ :cute:",
    "I've seen better comebacks from a boomerang that never returned~ :sad:",
    "You're like a cloud — when you disappear, it's a beautiful day~ :heart:",
    "If brains were petrol, you wouldn't have enough to power a fly's motorcycle~",
    "You're the reason shampoo has instructions~ :sad:",
    "I would explain the joke but I don't have crayons with me~",
    "You're not completely useless — you can always serve as a bad example~ :sparkle:",
    "I'd give you a nasty look but you already have one~ :heart:",
    "You bring everyone so much joy... when you leave the room~ :flower:",
    "I'm not saying you're dumb, I'm just saying you had bad luck being born on a thinking day~ :cute:",
    "Even your WiFi signal is stronger than your personality~ :signal: :heart:",
]


async def roast_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    target = msg.reply_to_message.from_user if msg.reply_to_message else None

    if not target:
        await premium.reply(msg, ":cute: Reply to someone to roast them~ /roast :heart:")
        return

    if target.is_bot:
        await premium.reply(msg, "Hehe I can't roast myself~ pick a human! :heart:")
        return

    roast = random.choice(ROASTS)

    text = (
        f":zap: <b>Roasting {mention_html(target)}~</b>\n\n"
        f"<blockquote>{roast}</blockquote>\n\n"
        "<i>All love no hate~ :sad: :heart: Yuki approves this roast</i>"
    )

    await premium.reply(msg, text, disable_web_page_preview=True)


async def ship_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user1 = None
    user2 = None

    if msg.reply_to_message:
        user1 = msg.reply_to_message.from_user
        user2 = update.effective_user
    elif len(ctx.args) >= 1 and msg.entities:
        mentions = [e for e in (msg.entities or []) if e.type == "text_mention"]
        if len(mentions) >= 2:
            user1 = mentions[0].user
            user2 = mentions[1].user
        elif len(mentions) == 1:
            user1 = mentions[0].user
            user2 = update.effective_user

    if not user1 or not user2:
        await premium.reply(
            msg,
            ":pinkheart: <b>How to ship:</b>\n\n"
            "Reply to someone's message and type <code>/ship</code>\n"
            "I'll calculate your compatibility~ :flower:",
        )
        return

    seed = (min(user1.id, user2.id) * 1000 + max(user1.id, user2.id)) % 100
    score = (seed + 42) % 101

    n1 = full_name(user1)
    n2 = full_name(user2)

    ship_name = n1[:len(n1) // 2] + n2[len(n2) // 2:]

    filled = int(score / 10)
    bar = ":heart:" * filled + ":whiteheart:" * (10 - filled)

    if score >= 90:
        verdict = "SOULMATES!! :sad: :heart: This is literally destiny~"
    elif score >= 75:
        verdict = "Super compatible!! :heart: These two are everything~"
    elif score >= 60:
        verdict = "Pretty good match~ :pinkheart: Could def work!!"
    elif score >= 40:
        verdict = "There's something there~ :search: Give it a chance!"
    elif score >= 20:
        verdict = "Hmm... opposites attract? :cute: Maybe~"
    else:
        verdict = "Bestie... the stars said no :sad: but love is unpredictable~"

    text = (
        ":pinkheart: <b>Ship Calculator~</b>\n\n"
        f"<b>{mention_html(user1)}</b> + <b>{mention_html(user2)}</b>\n\n"
        f"Ship name: <b>{ship_name}</b> :flower:\n\n"
        f"{bar} <b>{score}%</b>\n\n"
        f"<blockquote>{verdict}</blockquote>\n\n"
        "<i>— Calculated by Yuki with science and magic~ :heart: :sparkle:</i>"
    )

    await premium.reply(msg, text, disable_web_page_preview=True)


COMPLIMENTS = [
    "You have the kind of energy that makes people feel safe~ :flower:",
    "Honestly? The group is just better when you're here~ :heart:",
    "Your sense of humour is genuinely one of a kind~ :sparkle:",
    "You're the kind of person everyone secretly wants to be around~ :cute: :pinkheart:",
    "There's something about the way you talk that just makes everyone smile~ :flower:",
    "You're so effortlessly cool and you probably don't even realise it~ :heart:",
    "Kindness looks really good on you~ :sparkle:",
    "You're like that one song that goes perfectly with every mood~ :pinkheart:",
    "The world genuinely needs more people like you~ :star: :heart:",
    "You make hard things look easy and that's honestly a superpower~ :sparkle:",
]


async def compliment_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    target = msg.reply_to_message.from_user if msg.reply_to_message else update.effective_user

    comp = random.choice(COMPLIMENTS)

    text = (
        f":mail: <b>A little something for {mention_html(target)}~</b>\n\n"
        f"<blockquote>{comp}</blockquote>\n\n"
        "<i>— From Yuki with love :heart: :flower:</i>"
    )

    await premium.reply(msg, text, disable_web_page_preview=True)


DARES = [
    "Send a voice note saying 'I love Yuki' in the most dramatic voice possible~ :heart:",
    "Type your honest opinion about the last person who messaged you~ :search:",
    "Send the 5th photo in your gallery right now~",
    "Write a 3-line poem about the group chat~ :sparkle:",
    "Change your profile pic to something funny for 1 hour~ :sad:",
    "Send a voice note of you singing any song for 10 seconds~",
    "Confess the most embarrassing thing you did this week~",
    "Tag someone and say one genuine thing you like about them~ :heart:",
    "Write a love letter to your favourite food~",
    "Send a selfie with your best pout~",
    "Tell us your most controversial food opinion~",
    "Do a British accent voice note saying 'good day old chap'~",
]


async def dare_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    dare = random.choice(DARES)

    text = (
        f":trophy: <b>Dare for {mention_html(user)}~</b>\n\n"
        f"<blockquote>{dare}</blockquote>\n\n"
        "<i>No skipping!! Yuki is watching~ :search: :heart:</i>"
    )

    await premium.reply(update.effective_message, text, disable_web_page_preview=True)


FACTS = [
    "Honey never expires~ archaeologists found 3000-year-old honey in Egyptian tombs and it was still good!!",
    "Otters hold hands while sleeping so they don't drift apart~ :heart: IMAGINE",
    "A group of flamingos is called a flamboyance~ serve!!",
    "Cows have best friends and get stressed when separated from them~ :pinkheart:",
    "The shortest war in history lasted 38–45 minutes~ that's shorter than my attention span",
    "Butterflies taste with their feet~ imagine tasting the floor bestie",
    "Wombat poop is cube-shaped~ nature said squares only",
    "Bananas are technically berries but strawberries aren't~ the betrayal!!",
    "Cleopatra lived closer in time to the Moon landing than to the building of the Great Pyramid~",
    "A day on Venus is longer than a year on Venus~ time is fake apparently",
    "Penguins propose to their partner with a pebble~ so romantic honestly",
    "The thumbnail got its name because people used their thumbs to file things~",
]


async def fact_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    fact = random.choice(FACTS)
    reactions = [
        "Yuki learnt this today too~ :flower:",
        "Can you believe?? :cute:",
        "The more you know~ :sparkle: :heart:",
        "Okay this blew my mind~",
        "Sharing because I think about this a lot~ :pinkheart:",
    ]

    text = (
        ":brain: <b>Fun Fact~</b>\n\n"
        f"<blockquote>{fact}</blockquote>\n\n"
        f"<i>{random.choice(reactions)}</i>"
    )

    await premium.reply(update.effective_message, text)


GM_MSGS = [
    ":sparkle: <b>Good Morning everyone~</b> :heart:\n\nA new day is here!! Make it count, eat breakfast, drink water, and be kind :flower:\n\n<i>— Yuki loves you~ :pinkheart:</i>",
    ":flower: <b>Good Morning bestiesss~</b>\n\nThe sun is up, the vibes are immaculate, and Yuki is READY~ :sparkle: :heart: How's everyone doing??",
    ":sparkle: <b>Morning everyone!!~</b> :flower:\n\nRemember: you are loved, you are capable, and today is going to be amazing~ :heart:\n\n<i>— Your fav Yuki :ribbon:</i>",
]

GN_MSGS = [
    ":clock: <b>Good Night everyone~</b> :heart:\n\nThank you for chatting with me today~ Sweet dreams and sleep well :flower:\n\n<i>— Yuki misses you already :cute:</i>",
    ":clock: <b>GN GN bestiesss~</b>\n\nAnother day done!! You did amazing~ Now rest that beautiful brain of yours :pinkheart: :sparkle:\n\n<i>— Yuki :heart:</i>",
    ":clock: <b>Night night everyone~</b> :flower:\n\nDon't scroll your phone too long ok?? Sleep is important~ I'll be here in the morning :heart:\n\n<i>— Your Yuki :ribbon:</i>",
]


async def gm_job(context):
    try:
        cursor = db.get_db().groups.find({"daily_msgs": True}, {"chat_id": 1})
        groups = [doc["chat_id"] async for doc in cursor]
        msg = random.choice(GM_MSGS)

        for chat_id in groups:
            try:
                await premium.send(context.bot, chat_id, msg)
            except Exception:
                pass
    except Exception as e:
        log.debug("GM job: %s", e)


async def gn_job(context):
    try:
        cursor = db.get_db().groups.find({"daily_msgs": True}, {"chat_id": 1})
        groups = [doc["chat_id"] async for doc in cursor]
        msg = random.choice(GN_MSGS)

        for chat_id in groups:
            try:
                await premium.send(context.bot, chat_id, msg)
            except Exception:
                pass
    except Exception as e:
        log.debug("GN job: %s", e)


def register_daily_jobs(app):
    from datetime import time as dtime
    import pytz

    ist = pytz.timezone("Asia/Kolkata")

    app.job_queue.run_daily(
        gm_job,
        time=dtime(hour=8, minute=0, tzinfo=ist),
        name="daily_gm",
    )

    app.job_queue.run_daily(
        gn_job,
        time=dtime(hour=22, minute=0, tzinfo=ist),
        name="daily_gn",
    )

    log.info("Daily GM/GN jobs scheduled IST")


@admin_only
async def dailymsg_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    msg = update.effective_message

    if chat.type == "private":
        await premium.reply(msg, "Use this in a group~ :heart:")
        return

    doc = await db.get_group(chat.id) or {}
    current = doc.get("daily_msgs", False)

    await db.upsert_group(chat.id, {"daily_msgs": not current})

    status = ":success: ON" if not current else ":warning: OFF"

    await premium.reply(
        msg,
        f":calendar: <b>Daily GM/GN Messages: {status}</b>\n\n"
        f"<i>{'Yuki will now send morning and night messages~ :heart:' if not current else 'No more daily messages~ :clock:'}</i>",
    )


shayari_h = CommandHandler("shayari", shayari_cmd)
horoscope_h = CommandHandler("horoscope", horoscope_cmd)
loveletter_h = CommandHandler("loveletter", loveletter_cmd)
roast_h = CommandHandler("roast", roast_cmd)
ship_h = CommandHandler("ship", ship_cmd)
compliment_h = CommandHandler("compliment", compliment_cmd)
dare_h = CommandHandler("dare", dare_cmd)
fact_h = CommandHandler("fact", fact_cmd)
dailymsg_h = CommandHandler("dailymsg", dailymsg_cmd)