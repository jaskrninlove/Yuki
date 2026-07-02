"""
Yuki Bot - Stylish Name Generator
/style your name

Shows 20+ stylish fonts with premium colored buttons, 3 per page.
"""

import html

from telegram import Update, InlineKeyboardMarkup as Markup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes

from yuki.utils.keyboards import pbtn, icon
from yuki.utils import premium

STYLE_CACHE = {}

FONT_MAPS = {
    "Bold": str.maketrans(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",
        "𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇0123456789",
    ),
    "Italic": str.maketrans(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
        "𝘈𝘉𝘊𝘋𝘌𝘍𝘎𝘏𝘐𝘑𝘒𝘓𝘔𝘕𝘖𝘗𝘘𝘙𝘚𝘛𝘜𝘝𝘞𝘟𝘠𝘡𝘢𝘣𝘤𝘥𝘦𝘧𝘨𝘩𝘪𝘫𝘬𝘭𝘮𝘯𝘰𝘱𝘲𝘳𝘴𝘵𝘶𝘷𝘸𝘹𝘺𝘻",
    ),
    "Bold Italic": str.maketrans(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
        "𝘼𝘽𝘾𝘿𝙀𝙁𝙂𝙃𝙄𝙅𝙆𝙇𝙈𝙉𝙊𝙋𝙌𝙍𝙎𝙏𝙐𝙑𝙒𝙓𝙔𝙕𝙖𝙗𝙘𝙙𝙚𝙛𝙜𝙝𝙞𝙟𝙠𝙡𝙢𝙣𝙤𝙥𝙦𝙧𝙨𝙩𝙪𝙫𝙬𝙭𝙮𝙯",
    ),
    "Mono": str.maketrans(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",
        "𝙰𝙱𝙲𝙳𝙴𝙵𝙶𝙷𝙸𝙹𝙺𝙻𝙼𝙽𝙾𝙿𝚀𝚁𝚂𝚃𝚄𝚅𝚆𝚇𝚈𝚉𝚊𝚋𝚌𝚍𝚎𝚏𝚐𝚑𝚒𝚓𝚔𝚕𝚖𝚗𝚘𝚙𝚚𝚛𝚜𝚝𝚞𝚟𝚠𝚡𝚢𝚣𝟶𝟷𝟸𝟹𝟺𝟻𝟼𝟽𝟾𝟿",
    ),
    "Double": str.maketrans(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",
        "𝔸𝔹ℂ𝔻𝔼𝔽𝔾ℍ𝕀𝕁𝕂𝕃𝕄ℕ𝕆ℙℚℝ𝕊𝕋𝕌𝕍𝕎𝕏𝕐ℤ𝕒𝕓𝕔𝕕𝕖𝕗𝕘𝕙𝕚𝕛𝕜𝕝𝕞𝕟𝕠𝕡𝕢𝕣𝕤𝕥𝕦𝕧𝕨𝕩𝕪𝕫𝟘𝟙𝟚𝟛𝟜𝟝𝟞𝟟𝟠𝟡",
    ),
    "Script": str.maketrans(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
        "𝒜𝐵𝒞𝒟𝐸𝐹𝒢𝐻𝐼𝒥𝒦𝐿𝑀𝒩𝒪𝒫𝒬𝑅𝒮𝒯𝒰𝒱𝒲𝒳𝒴𝒵𝒶𝒷𝒸𝒹𝑒𝒻𝑔𝒽𝒾𝒿𝓀𝓁𝓂𝓃𝑜𝓅𝓆𝓇𝓈𝓉𝓊𝓋𝓌𝓍𝓎𝓏",
    ),
    "Fraktur": str.maketrans(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
        "𝔄𝔅ℭ𝔇𝔈𝔉𝔊ℌℑ𝔍𝔎𝔏𝔐𝔑𝔒𝔓𝔔ℜ𝔖𝔗𝔘𝔙𝔚𝔛𝔜ℨ𝔞𝔟𝔠𝔡𝔢𝔣𝔤𝔥𝔦𝔧𝔨𝔩𝔪𝔫𝔬𝔭𝔮𝔯𝔰𝔱𝔲𝔳𝔴𝔵𝔶𝔷",
    ),
    "Circled": str.maketrans(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",
        "ⒶⒷⒸⒹⒺⒻⒼⒽⒾⒿⓀⓁⓂⓃⓄⓅⓆⓇⓈⓉⓊⓋⓌⓍⓎⓏⓐⓑⓒⓓⓔⓕⓖⓗⓘⓙⓚⓛⓜⓝⓞⓟⓠⓡⓢⓣⓤⓥⓦⓧⓨⓩ⓪①②③④⑤⑥⑦⑧⑨",
    ),
    "Square": str.maketrans(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
        "🄰🄱🄲🄳🄴🄵🄶🄷🄸🄹🄺🄻🄼🄽🄾🄿🅀🅁🅂🅃🅄🅅🅆🅇🅈🅉🄰🄱🄲🄳🄴🄵🄶🄷🄸🄹🄺🄻🄼🄽🄾🄿🅀🅁🅂🅃🅄🅅🅆🅇🅈🅉",
    ),
}


def transform(text: str, font: str) -> str:
    if font in FONT_MAPS:
        return text.translate(FONT_MAPS[font])

    styles = {
        "Spaced": " ".join(text),
        "Upper": text.upper(),
        "Lower": text.lower(),
        "Stars": f"✦ {text} ✦",
        "Hearts": f"♡ {text} ♡",
        "Sparkle": f"✨ {text} ✨",
        "Cute": f"𐙚 {text} 𐙚",
        "Royal": f"♛ {text} ♛",
        "Fire": f"🔥 {text} 🔥",
        "Moon": f"☾ {text} ☽",
        "Angel": f"꒰ঌ {text} ໒꒱",
        "Devil": f"𖤐 {text} 𖤐",
        "Arrows": f"➳ {text} ➳",
        "Brackets": f"『 {text} 』",
        "Cloud": f"☁ {text} ☁",
        "Rose": f"❀ {text} ❀",
    }

    return styles.get(font, text)


FONTS = [
    "Bold", "Italic", "Bold Italic",
    "Mono", "Double", "Script",
    "Fraktur", "Circled", "Square",
    "Spaced", "Upper", "Lower",
    "Stars", "Hearts", "Sparkle",
    "Cute", "Royal", "Fire",
    "Moon", "Angel", "Devil",
    "Arrows", "Brackets", "Cloud",
    "Rose",
]

PER_PAGE = 3


def keyboard(user_id: int, page: int) -> Markup:
    total = (len(FONTS) + PER_PAGE - 1) // PER_PAGE
    page = max(1, min(page, total))

    start = (page - 1) * PER_PAGE
    page_fonts = FONTS[start:start + PER_PAGE]

    rows = []

    for font in page_fonts:
        rows.append([
            pbtn(
                font,
                callback_data=f"style:{user_id}:{font}:{page}",
                style="primary",
                icon=icon("sparkle") or icon("settings"),
            )
        ])

    nav = []

    if page > 1:
        nav.append(
            pbtn(
                "Back",
                callback_data=f"stylepage:{user_id}:{page - 1}",
                style="primary",
                icon=icon("back"),
            )
        )

    nav.append(
        pbtn(
            f"{page}/{total}",
            callback_data="noop",
            style="success",
            icon=icon("help"),
        )
    )

    if page < total:
        nav.append(
            pbtn(
                "Next",
                callback_data=f"stylepage:{user_id}:{page + 1}",
                style="primary",
                icon=icon("next"),
            )
        )

    rows.append(nav)

    return Markup(rows)


async def style_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user = update.effective_user
    name = " ".join(ctx.args).strip()

    if not msg or not user:
        return

    if not name:
        await premium.reply(
            msg,
            ":sparkle: <b>Stylish Name Generator</b>\n\n"
            "Usage: <code>/style your name</code>",
        )
        return

    STYLE_CACHE[user.id] = name

    await premium.reply(
        msg,
        f":sparkle: <b>Choose a stylish font for:</b>\n\n"
        f"<blockquote><code>{html.escape(name)}</code></blockquote>",
        reply_markup=keyboard(user.id, 1),
    )


async def style_page_cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if not query:
        return

    await query.answer()

    _, uid, page = query.data.split(":")
    uid = int(uid)
    page = int(page)

    if query.from_user.id != uid:
        await query.answer("This style menu is not yours.", show_alert=True)
        return

    name = STYLE_CACHE.get(uid, "Your Name")

    await premium.edit(
        query,
        f":sparkle: <b>Choose a stylish font for:</b>\n\n"
        f"<blockquote><code>{html.escape(name)}</code></blockquote>",
        reply_markup=keyboard(uid, page),
    )


async def style_pick_cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if not query:
        return

    try:
        _, uid, font, page = query.data.split(":", 3)
        uid = int(uid)
        page = int(page)
    except Exception:
        await query.answer("Invalid style.", show_alert=True)
        return

    if query.from_user.id != uid:
        await query.answer("This style menu is not yours.", show_alert=True)
        return

    name = STYLE_CACHE.get(uid, "Your Name")
    result = transform(name, font)

    await query.answer(result[:190], show_alert=True)

    await premium.edit(
        query,
        f":sparkle: <b>{html.escape(font)}</b>\n\n"
        f"<blockquote><code>{html.escape(result)}</code></blockquote>\n\n"
        f"<i>Tap and copy your stylish name.</i>",
        reply_markup=keyboard(uid, page),
    )


style_handler = CommandHandler(["style", "font", "stylish"], style_cmd)
style_page_handler = CallbackQueryHandler(style_page_cb, pattern=r"^stylepage:\d+:\d+$")
style_pick_handler = CallbackQueryHandler(style_pick_cb, pattern=r"^style:\d+:[^:]+:\d+$")