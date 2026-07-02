"""
Yuki Bot - Utility Commands
/id /avatar /calc /password /uuid /base64 /json /stickerid /getfile /url
/qr /google /wiki /time /weather /wish
Premium emoji supported.
"""

import ast
import base64
import html
import io
import json
import random
import secrets
import string
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
import qrcode
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from yuki.utils.helpers import full_name
from yuki.utils import premium


async def id_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    target = msg.reply_to_message.from_user if msg.reply_to_message else user

    text = (
        ":id: <b>ID Info</b>\n\n"
        f"<blockquote>"
        f":user: User: <b>{html.escape(full_name(target))}</b>\n"
        f":id: User ID: <code>{target.id}</code>\n"
        f":chat: Chat ID: <code>{chat.id}</code>\n"
        f":mail: Message ID: <code>{msg.message_id}</code>"
        f"</blockquote>"
    )

    await premium.reply(msg, text)


async def avatar_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user = msg.reply_to_message.from_user if msg.reply_to_message else update.effective_user

    photos = await ctx.bot.get_user_profile_photos(user.id, limit=1)
    if photos.total_count == 0:
        await premium.reply(msg, ":search: No profile photo found.")
        return

    file_id = photos.photos[0][-1].file_id
    await msg.reply_photo(
        file_id,
        caption=premium.render(f":user: Avatar of <b>{html.escape(full_name(user))}</b>"),
        parse_mode="HTML",
    )


def safe_calc(expr: str):
    allowed = {
        ast.Expression, ast.BinOp, ast.UnaryOp, ast.Num, ast.Constant,
        ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod, ast.FloorDiv,
        ast.USub, ast.UAdd,
    }

    tree = ast.parse(expr, mode="eval")
    for node in ast.walk(tree):
        if type(node) not in allowed:
            raise ValueError("Invalid expression")

    return eval(compile(tree, "<calc>", "eval"), {"__builtins__": {}}, {})


async def calc_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    expr = " ".join(ctx.args)

    if not expr:
        await premium.reply(msg, ":tools: Usage: <code>/calc 25*10+50</code>")
        return

    try:
        result = safe_calc(expr)
        await premium.reply(
            msg,
            f":success: <b>Result:</b>\n<blockquote><code>{result}</code></blockquote>",
        )
    except Exception:
        await premium.reply(msg, ":warning: Invalid calculation.")


async def password_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message

    try:
        length = int(ctx.args[0]) if ctx.args else 16
    except Exception:
        length = 16

    length = max(8, min(length, 64))
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    pwd = "".join(secrets.choice(chars) for _ in range(length))

    await premium.reply(
        msg,
        f":shield: <b>Password:</b>\n<blockquote><code>{pwd}</code></blockquote>",
    )


async def uuid_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await premium.reply(
        update.effective_message,
        f":id: <b>Random UUID</b>\n<blockquote><code>{uuid.uuid4()}</code></blockquote>",
    )


async def base64_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message

    if len(ctx.args) < 2:
        await premium.reply(
            msg,
            ":tools: <b>Base64 Tool</b>\n\n"
            "Usage:\n"
            "<code>/base64 encode hello</code>\n"
            "<code>/base64 decode aGVsbG8=</code>",
        )
        return

    mode = ctx.args[0].lower()
    data = " ".join(ctx.args[1:])

    try:
        if mode == "encode":
            result = base64.b64encode(data.encode()).decode()
        elif mode == "decode":
            result = base64.b64decode(data.encode()).decode()
        else:
            raise ValueError

        await premium.reply(
            msg,
            f":success: <b>Base64 Result</b>\n<blockquote><code>{html.escape(result)}</code></blockquote>",
        )
    except Exception:
        await premium.reply(msg, ":warning: Invalid base64 input.")


async def json_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    raw = " ".join(ctx.args)

    if msg.reply_to_message and msg.reply_to_message.text:
        raw = msg.reply_to_message.text

    if not raw:
        await premium.reply(
            msg,
            ':tools: Send <code>/json {"name":"Yuki"}</code> or reply to JSON text.',
        )
        return

    try:
        parsed = json.loads(raw)
        pretty = json.dumps(parsed, indent=2, ensure_ascii=False)
        await premium.reply(
            msg,
            f":success: <b>Pretty JSON</b>\n\n<pre>{html.escape(pretty[:3500])}</pre>",
        )
    except Exception:
        await premium.reply(msg, ":warning: Invalid JSON.")


async def stickerid_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message

    if not msg.reply_to_message or not msg.reply_to_message.sticker:
        await premium.reply(msg, ":reply: Reply to a sticker.")
        return

    s = msg.reply_to_message.sticker
    text = (
        ":gift: <b>Sticker Info</b>\n\n"
        f"<blockquote>"
        f"<b>File ID:</b>\n<code>{s.file_id}</code>\n\n"
        f"<b>Unique ID:</b>\n<code>{s.file_unique_id}</code>\n"
        f"<b>Emoji:</b> {s.emoji or 'None'}\n"
        f"<b>Pack:</b> {s.set_name or 'None'}"
        f"</blockquote>"
    )
    await premium.reply(msg, text)


async def getfile_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message

    if not msg.reply_to_message:
        await premium.reply(msg, ":reply: Reply to any media/file.")
        return

    r = msg.reply_to_message
    file_obj = (
        r.document or r.video or r.audio or r.voice or r.animation or
        r.sticker or (r.photo[-1] if r.photo else None)
    )

    if not file_obj:
        await premium.reply(msg, ":search: No media found.")
        return

    text = (
        ":mail: <b>File Info</b>\n\n"
        f"<blockquote>"
        f"<b>File ID:</b>\n<code>{file_obj.file_id}</code>\n\n"
        f"<b>Unique ID:</b>\n<code>{file_obj.file_unique_id}</code>"
        f"</blockquote>"
    )

    await premium.reply(msg, text)


async def url_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message

    if not msg.reply_to_message:
        await premium.reply(msg, ":reply: Reply to any media/file.")
        return

    r = msg.reply_to_message
    file_obj = (
        r.document or r.video or r.audio or r.voice or r.animation or
        r.sticker or (r.photo[-1] if r.photo else None)
    )

    if not file_obj:
        await premium.reply(msg, ":search: No media found.")
        return

    file = await ctx.bot.get_file(file_obj.file_id)
    await premium.reply(
        msg,
        f":mail: <b>Telegram File URL</b>\n<blockquote><code>{file.file_path}</code></blockquote>",
    )


async def qr_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    text = " ".join(ctx.args)

    if msg.reply_to_message and msg.reply_to_message.text:
        text = msg.reply_to_message.text

    if not text:
        await premium.reply(msg, ":tools: Usage: <code>/qr your text</code> or reply to text.")
        return

    img = qrcode.make(text)
    bio = io.BytesIO()
    bio.name = "qr.png"
    img.save(bio, "PNG")
    bio.seek(0)

    await msg.reply_photo(
        bio,
        caption=premium.render(":success: QR Code"),
        parse_mode="HTML",
    )


async def google_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    q = " ".join(ctx.args)

    if not q:
        await premium.reply(msg, ":search: Usage: <code>/google your search</code>")
        return

    link = "https://www.google.com/search?q=" + q.replace(" ", "+")
    await premium.reply(
        msg,
        f":search: <b>Google Search:</b>\n<blockquote>{html.escape(link)}</blockquote>",
        disable_web_page_preview=True,
    )


async def wiki_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    import urllib.parse

    msg = update.effective_message
    query = " ".join(ctx.args).strip()

    if not query:
        await premium.reply(msg, ":book: Usage: <code>/wiki Python</code>")
        return

    try:
        title = urllib.parse.quote(query.replace(" ", "_"))
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}"

        async with httpx.AsyncClient(
            timeout=20,
            headers={"User-Agent": "YukiBot/1.1 Telegram Bot"},
        ) as client:
            res = await client.get(url)

        if res.status_code == 404:
            await premium.reply(msg, ":search: No Wikipedia page found.")
            return

        res.raise_for_status()
        data = res.json()

        page_title = data.get("title", query)
        extract = data.get("extract") or "No summary found."
        page_url = data.get("content_urls", {}).get("desktop", {}).get("page", "")

        text = (
            f":book: <b>{html.escape(page_title)}</b>\n\n"
            f"<blockquote>{html.escape(extract[:3000])}</blockquote>"
        )

        if page_url:
            text += f"\n\n{page_url}"

        await premium.reply(
            msg,
            text,
            disable_web_page_preview=True,
        )

    except Exception as e:
        await premium.reply(
            msg,
            f":warning: Wikipedia search failed.\n<code>{html.escape(str(e))}</code>",
        )


async def time_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    zone = " ".join(ctx.args) or "Asia/Kolkata"

    common = {
        "india": "Asia/Kolkata",
        "delhi": "Asia/Kolkata",
        "tokyo": "Asia/Tokyo",
        "london": "Europe/London",
        "newyork": "America/New_York",
        "ny": "America/New_York",
        "dubai": "Asia/Dubai",
    }

    zone = common.get(zone.lower().replace(" ", ""), zone)

    try:
        now = datetime.now(ZoneInfo(zone))
        await premium.reply(
            msg,
            f":clock: <b>Time in {html.escape(zone)}</b>\n"
            f"<blockquote><code>{now.strftime('%d %b %Y, %I:%M:%S %p')}</code></blockquote>",
        )
    except Exception:
        await premium.reply(msg, ":warning: Invalid timezone. Try <code>/time Asia/Kolkata</code>")


async def weather_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    city = " ".join(ctx.args)

    if not city:
        await premium.reply(msg, ":cloud: Usage: <code>/weather Delhi</code>")
        return

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.get(f"https://wttr.in/{city}?format=3")
            text = res.text.strip()

        await premium.reply(
            msg,
            f":sparkle: <b>Weather</b>\n<blockquote>{html.escape(text)}</blockquote>",
        )
    except Exception:
        await premium.reply(msg, ":warning: Weather service failed.")


async def wish_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    wish = " ".join(ctx.args)

    if not wish:
        await premium.reply(msg, ":star: Usage: <code>/wish I wish if I'm superman</code>")
        return

    chance = random.randint(1, 100)

    if chance >= 90:
        verdict = "Almost possible. Universe is secretly on your side."
    elif chance >= 70:
        verdict = "High chance. Keep believing and act on it."
    elif chance >= 45:
        verdict = "Maybe. Needs luck, timing and a little madness."
    elif chance >= 20:
        verdict = "Low chance, but not impossible."
    else:
        verdict = "Very rare. Even Yuki needs a miracle for this."

    text = (
        ":star: <b>Wish Reality Check</b>\n\n"
        f"<blockquote>"
        f"<b>Wish:</b> {html.escape(wish)}\n"
        f"<b>Possibility:</b> <code>{chance}%</code>\n"
        f"<b>Yuki says:</b> {verdict}"
        f"</blockquote>"
    )

    await premium.reply(msg, text)


id_handler = CommandHandler(["id", "info"], id_cmd)
avatar_handler = CommandHandler(["avatar", "pfp"], avatar_cmd)
calc_handler = CommandHandler("calc", calc_cmd)
password_handler = CommandHandler(["password", "pass"], password_cmd)
uuid_handler = CommandHandler("uuid", uuid_cmd)
base64_handler = CommandHandler("base64", base64_cmd)
json_handler = CommandHandler("json", json_cmd)
stickerid_handler = CommandHandler("stickerid", stickerid_cmd)
getfile_handler = CommandHandler("getfile", getfile_cmd)
url_handler = CommandHandler("url", url_cmd)
qr_handler = CommandHandler("qr", qr_cmd)
google_handler = CommandHandler("google", google_cmd)
wiki_handler = CommandHandler("wiki", wiki_cmd)
time_handler = CommandHandler("time", time_cmd)
weather_handler = CommandHandler("weather", weather_cmd)
wish_handler = CommandHandler("wish", wish_cmd)