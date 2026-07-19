"""
Yuki Premium Emoji Engine

Use tokens in en.yml:
:heart:
:flower:
:sparkle:

This renders premium/custom emoji using Telegram HTML:
<tg-emoji emoji-id="...">fallback</tg-emoji>
"""

import re

TOKEN_RE = re.compile(r":([a-zA-Z0-9_]+):")

PREMIUM = {
    "heart": "6294236798050638950",
    "flower": "6294324943664454191",
    "sparkle": "5999041732996504081",
    "pinkheart": "5260567255145539253",
    "gift": "5262671999573977569",
    "ribbon": "5235471434817498104",
    "star": "6098009917073921326",
    "bot": "6241997609045598666",
    "settings": "6239948750731617663",
    "users": "6293889313721555480",
    "group": "5291873529464122510",
    "book": "5256227233642605352",
    "tools": "5258361295517806281",
    "chart": "5258500400918587241",
    "clock": "5267334530171169409",
    "rocket": "5256131095094652290",
    "brain": "5280774071250872500",
    "database": "5280826864988873394",
    "signal": "5285439518130857782",
    "calendar": "5287606810168028257",
    "cake": "6132007091482662089",
    "trophy": "5334628996887895660",
    "crown": "5264757468189188707",
    "search": "5262605161292915346",
    "reply": "5402071365098437489",
    "warning": "5433892975362995314",
    "success": "6116023147352298145",
    "cute": "6116183899388253363",
    "sad": "6228735269726586366",
    "flower2": "6102617459204822706",
    "whiteheart": "6228917595383269239",
    "greenheart": "6228766915045623859",
    "mail": "6244501154072368012",
    "chat": "6237491831869806976",
    "user": "6237927637906364256",
    "id": "6242447111732862933",
    "ping": "6240247938153455115",
    "zap": "6242479594570522124",
    "toast": "5206619699948849433",
    "spider": "6294324943664454191",
    "mask": "6294073481919208430",
    "pinkgift": "5355230232724935087",
    "gold": "5440539497383087970",
    "silver": "5447203607294265305",
    "bronze": "5453902265922376865",

    # aliases
    "shield": "5433892975362995314",
    "bot2": "6241997609045598666",
    "kiss": "6237491831869806976",

    # add inside PREMIUM
"ring": "5262922516426420894",
"bouquet": "6293965450606812914",
"teddy": "5206502842478638898",
"rose": "6102617459204822706",
"cake2": "6118216466891281890",
"ribbon2": "6221961320321783118",
"star2": "6237718408574539239",
"music": "5470135030393090150",
"choco": "5321310634015482162",
"lollipop": "5262693362741308140",
"crown2": "5931567294265169011",
"unicorn": "5467658895847608185",

"dot2": "5819078828017849357",

"wallet": "5215420556089776398",
"money": "5296355151743838259",
"coin": "5382164415019768638",
"bag": "5319009880164570032",
"bank": "5197369495739455200",
"sword": "5453991094435997597",
"target": "5256131095094652290",
"fire": "5335060684050822126",
"bolt": "5377834924776627189",
"diamond": "5228981786477881645",
"medal": "5454065135377222655",
"rank": "5188344996356448758",
"love": "5255861796350224063",
"giftbox": "5193085063998224234",
"coii": "5224428893510850014",
"cat": "5334705202492630985",
"broken_heart": "5334800026780592575",
"tada": "5461151367559141950",
"gem": "5931612473026154687",
"broken_heart": "5334800026780592575",
"crossed_swords": "6118209143972040877",
"skull": "6118209143972040877",
"refer": "5335005820138564214",
"grid": "5265120027853481187",
"magnifier": "5231012545799666522",
"party": "5461151367559141950",
"check": "5465626908165163181",
"key": "6194861919224991102",


"ek": "5233477268617053735",
"do": "5233546451950256512",
"teen": "5233604395354047945",
"char": "5233544652358962131",
"panch": "5233619423444616550",
"six": "5233286945731267091",
"refresh": "5256110612395605858",
"onlyb": "6269232765468676321",
"lock": "5886505193180239900",
"private": "5335005820138564214",
"kiss": "5422801686177526412"
}

FALLBACK = {
    "heart": "💗",
    "flower": "🌸",
    "sparkle": "✨",
    "pinkheart": "🩷",
    "gift": "🎁",
    "ribbon": "🎀",
    "star": "🌟",
    "bot": "🤖",
    "settings": "⚙️",
    "users": "👥",
    "group": "👥",
    "book": "📖",
    "tools": "🧰",
    "shield": "🛡️",
    "chart": "📊",
    "clock": "⏱️",
    "rocket": "🚀",
    "brain": "🧠",
    "database": "🗄️",
    "signal": "📡",
    "calendar": "📅",
    "cake": "🎂",
    "trophy": "🏆",
    "crown": "👑",
    "search": "🔍",
    "reply": "↩️",
    "warning": "⚠️",
    "success": "✅",
    "cute": "🥹",
    "sad": "🥺",
    "flower2": "🌷",
    "whiteheart": "🤍",
    "greenheart": "💚",
    "mail": "📨",
    "chat": "💬",
    "user": "👤",
    "id": "🆔",
    "ping": "🏓",
    "zap": "⚡",
    "toast": "🥂",
    "spider": "🕷️",
    "mask": "🎭",
    "pinkgift": "💝",
    "gold": "🥇",
    "silver": "🥈",
    "bronze": "🥉",
    "ring": "💍",
"bouquet": "💐",
"teddy": "🧸",
"rose": "🌹",
"cake2": "🍰",
"ribbon2": "🎀",
"star2": "⭐",
"music": "🎵",
"choco": "🍫",
"lollipop": "🍭",
"crown2": "👑",
"unicorn": "🦄",
"grid": "🔲",
}


def render(text: str) -> str:
    def repl(match):
        key = match.group(1)
        emoji_id = PREMIUM.get(key, "")
        fallback = FALLBACK.get(key, "✨")

        if emoji_id:
            return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'

        return fallback

    return TOKEN_RE.sub(repl, text or "")


async def reply(message, text: str, **kwargs):
    kwargs.pop("entities", None)
    kwargs.pop("caption_entities", None)
    kwargs.pop("parse_mode", None)

    return await message.reply_text(
        render(text),
        parse_mode="HTML",
        **kwargs,
    )


async def send(bot, chat_id, text: str, **kwargs):
    kwargs.pop("entities", None)
    kwargs.pop("caption_entities", None)
    kwargs.pop("parse_mode", None)

    return await bot.send_message(
        chat_id,
        render(text),
        parse_mode="HTML",
        **kwargs,
    )


async def edit(query, text: str, **kwargs):
    kwargs.pop("entities", None)
    kwargs.pop("caption_entities", None)
    kwargs.pop("parse_mode", None)

    return await query.edit_message_text(
        render(text),
        parse_mode="HTML",
        **kwargs,
    )


async def reply_photo(message, photo, caption: str, **kwargs):
    kwargs.pop("entities", None)
    kwargs.pop("caption_entities", None)
    kwargs.pop("parse_mode", None)

    return await message.reply_photo(
        photo=photo,
        caption=render(caption),
        parse_mode="HTML",
        **kwargs,
    )


async def edit_caption(query, caption: str, **kwargs):
    kwargs.pop("entities", None)
    kwargs.pop("caption_entities", None)
    kwargs.pop("parse_mode", None)

    return await query.edit_message_caption(
        caption=render(caption),
        parse_mode="HTML",
        **kwargs,
    )

from telegram import InlineKeyboardButton as Btn


def pbtn(
    text: str,
    *,
    callback_data: str | None = None,
    url: str | None = None,
    style: str | None = None,
    icon: str | None = None,
) -> Btn:
    api_kwargs = {}

    if style:
        api_kwargs["style"] = style

    if icon:
        # icon name -> Telegram custom emoji ID
        emoji_id = PREMIUM.get(icon)

        if emoji_id:
            api_kwargs["icon_custom_emoji_id"] = emoji_id

    return Btn(
        text=text,
        callback_data=callback_data,
        url=url,
        api_kwargs=api_kwargs or None,
    )