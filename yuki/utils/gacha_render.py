"""
Yuki Gacha - Fallback Pull Result Card Renderer
Copyright © Jass

Used only when an AI-generated card image is missing from
yuki/assets/gacha_cards/. Otherwise the AI card is sent directly.
"""

from __future__ import annotations

import io
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT_DIR = Path(__file__).parent / "quote_assets" / "fonts"
FONT_BOLD = str(FONT_DIR / "Poppins-Bold.ttf")
FONT_REGULAR = str(FONT_DIR / "Poppins-Regular.ttf")

EMOJI_FONT_PATH = str(Path(__file__).parent / "gacha_assets" / "NotoColorEmoji.ttf")
EMOJI_NATIVE_SIZE = 109

SCALE = 3

RARITY_GRADIENTS = {
    "common":    ((210, 210, 218), (165, 165, 178)),
    "rare":      ((110, 160, 255), (60, 105, 225)),
    "epic":      ((190, 110, 255), (135, 55, 225)),
    "legendary": ((255, 220, 90), (255, 150, 40)),
}

RARITY_TEXT_COLOR = {
    "common": (70, 70, 80),
    "rare": (255, 255, 255),
    "epic": (255, 255, 255),
    "legendary": (90, 45, 0),
}


def _vertical_gradient(size, top, bottom):
    w, h = size
    base = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / max(h - 1, 1)
        r = int(top[0] + (bottom[0] - top[0]) * t)
        g = int(top[1] + (bottom[1] - top[1]) * t)
        b = int(top[2] + (bottom[2] - top[2]) * t)
        base.putpixel((0, y), (r, g, b))
    return base.resize((w, h))


def _draw_sparkle(draw, cx, cy, size, color):
    pts = []
    for i in range(8):
        angle = i * math.pi / 4
        r = size if i % 2 == 0 else size * 0.35
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        pts.append((x, y))
    draw.polygon(pts, fill=color)


def _render_emoji_tile(emoji: str, target_size: int) -> Image.Image:
    font = ImageFont.truetype(EMOJI_FONT_PATH, EMOJI_NATIVE_SIZE)
    tile = Image.new("RGBA", (136, 128), (0, 0, 0, 0))
    d = ImageDraw.Draw(tile)
    d.text((0, 0), emoji, font=font, embedded_color=True)
    bbox = tile.getbbox()
    if bbox:
        tile = tile.crop(bbox)
    return tile.resize((target_size, target_size), Image.LANCZOS)


def render_gacha_card(name: str, emoji: str, rarity: str, is_new: bool) -> bytes:
    """Returns PNG bytes of a pull-result card (fallback only)."""
    W, H = 700 * SCALE, 700 * SCALE
    top, bottom = RARITY_GRADIENTS.get(rarity, RARITY_GRADIENTS["common"])
    canvas = _vertical_gradient((W, H), top, bottom)
    draw = ImageDraw.Draw(canvas)

    rng = random.Random()
    for _ in range(16):
        x = rng.randint(0, W)
        y = rng.randint(0, H)
        size = rng.randint(5, 14) * SCALE
        _draw_sparkle(draw, x, y, size, (255, 255, 255))

    card_pad = 60 * SCALE
    card_top = 90 * SCALE
    card_bottom = H - 90 * SCALE
    draw.rounded_rectangle(
        (card_pad, card_top, W - card_pad, card_bottom),
        radius=50 * SCALE,
        fill=(255, 255, 255),
    )

    emoji_tile = _render_emoji_tile(emoji, 260 * SCALE)
    ex = (W - emoji_tile.width) // 2
    ey = card_top + 70 * SCALE
    canvas.paste(emoji_tile, (ex, ey), emoji_tile)

    name_font = ImageFont.truetype(FONT_BOLD, int(42 * SCALE))
    name_y = ey + emoji_tile.height + 30 * SCALE
    bbox = draw.textbbox((0, 0), name, font=name_font)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) / 2, name_y), name, font=name_font, fill=(40, 30, 45))

    label = rarity.upper()
    pill_font = ImageFont.truetype(FONT_BOLD, int(28 * SCALE))
    bbox = draw.textbbox((0, 0), label, font=pill_font)
    ptw, pth = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pill_pad_x, pill_pad_y = 36 * SCALE, 16 * SCALE
    pill_w, pill_h = ptw + pill_pad_x * 2, pth + pill_pad_y * 2
    pill_y = name_y + 70 * SCALE
    pill_x = (W - pill_w) / 2
    draw.rounded_rectangle(
        (pill_x, pill_y, pill_x + pill_w, pill_y + pill_h),
        radius=pill_h / 2,
        fill=top,
    )
    draw.text(
        (pill_x + pill_pad_x - bbox[0], pill_y + pill_pad_y - bbox[1]),
        label, font=pill_font, fill=RARITY_TEXT_COLOR.get(rarity, (255, 255, 255)),
    )

    if is_new:
        new_font = ImageFont.truetype(FONT_BOLD, int(26 * SCALE))
        new_text = "✦ NEW ✦"
        bbox = draw.textbbox((0, 0), new_text, font=new_font)
        ntw = bbox[2] - bbox[0]
        draw.text(((W - ntw) / 2, pill_y + pill_h + 24 * SCALE), new_text, font=new_font, fill=(255, 90, 140))

    heading_font = ImageFont.truetype(FONT_BOLD, int(36 * SCALE))
    heading = "Yuki Gacha"
    bbox = draw.textbbox((0, 0), heading, font=heading_font)
    htw = bbox[2] - bbox[0]
    draw.text(((W - htw) / 2, 20 * SCALE), heading, font=heading_font, fill=(255, 255, 255))

    final = canvas.resize((canvas.width // SCALE, canvas.height // SCALE), Image.LANCZOS)
    buf = io.BytesIO()
    final.save(buf, "PNG")
    return buf.getvalue()

def render_collection_banner(unlocked: int, total: int) -> bytes:
    """A simple pink-gradient banner used as the base photo for /collection,
    so pagination and card views can all use edit_message_media/edit_caption
    on the same message instead of sending new ones."""
    W, H = 700 * SCALE, 350 * SCALE
    canvas = _vertical_gradient((W, H), (255, 175, 205), (255, 130, 170))
    draw = ImageDraw.Draw(canvas)

    rng = random.Random()
    for _ in range(10):
        x = rng.randint(0, W)
        y = rng.randint(0, H)
        size = rng.randint(5, 12) * SCALE
        _draw_sparkle(draw, x, y, size, (255, 255, 255))

    title_font = ImageFont.truetype(FONT_BOLD, int(46 * SCALE))
    title = "Your Collection"
    bbox = draw.textbbox((0, 0), title, font=title_font)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) / 2, H / 2 - 70 * SCALE), title, font=title_font, fill=(255, 255, 255))

    sub_font = ImageFont.truetype(FONT_REGULAR, int(32 * SCALE))
    sub = f"{unlocked}/{total} companions unlocked"
    bbox = draw.textbbox((0, 0), sub, font=sub_font)
    stw = bbox[2] - bbox[0]
    draw.text(((W - stw) / 2, H / 2 + 10 * SCALE), sub, font=sub_font, fill=(255, 245, 248))

    final = canvas.resize((canvas.width // SCALE, canvas.height // SCALE), Image.LANCZOS)
    buf = io.BytesIO()
    final.save(buf, "PNG")
    return buf.getvalue()