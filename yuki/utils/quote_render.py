"""
Yuki Quote Renderer
Copyright © Jass

Renders a quote-sticker style image locally with Pillow, no external API
dependency. Replaces the old bot.lyo.su-based generator.
"""

from __future__ import annotations

import io
import unicodedata
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

FONT_DIR = Path(__file__).parent / "quote_assets" / "fonts"

FONT_BOLD = str(FONT_DIR / "Poppins-Bold.ttf")
FONT_REGULAR = str(FONT_DIR / "Poppins-Regular.ttf")
FONT_ITALIC = str(FONT_DIR / "Poppins-Italic.ttf")

SCALE = 3  # supersample factor for crisp text/edges before downscaling

BG_TOP = (30, 20, 45)
BG_BOTTOM = (18, 12, 28)
ACCENT = (255, 140, 190)
ACCENT_SOFT = (255, 190, 215)
TEXT_MAIN = (240, 235, 245)
TEXT_MUTED = (170, 160, 185)

MAX_LINES = 10
CARD_WIDTH = 900  # layout units, pre-scale


def _clean_display_text(text: str) -> str:
    """Normalizes stylized Unicode (bold/italic Telegram fonts) back to
    plain characters so it renders correctly with our card font, instead
    of showing tofu boxes for glyphs Poppins doesn't have."""
    if not text:
        return text
    normalized = unicodedata.normalize("NFKD", text)
    cleaned = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    # Fallback: if normalization stripped everything (e.g. emoji-only text), keep original.
    return cleaned if cleaned.strip() else text


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


def _circle_avatar(img: Image.Image, size: int) -> Image.Image:
    img = ImageOps.fit(img.convert("RGB"), (size, size), Image.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
    out = Image.new("RGBA", (size, size))
    out.paste(img, (0, 0), mask)
    return out


def _hard_break_word(draw, word, font, max_width):
    chunks = []
    cur = ""
    for ch in word:
        trial = cur + ch
        if draw.textlength(trial, font=font) <= max_width or not cur:
            cur = trial
        else:
            chunks.append(cur)
            cur = ch
    if cur:
        chunks.append(cur)
    return chunks


def _wrap_text(draw, text, font, max_width):
    lines = []
    for paragraph in text.split("\n"):
        if not paragraph:
            lines.append("")
            continue
        words = paragraph.split(" ")
        cur = ""
        for word in words:
            if draw.textlength(word, font=font) > max_width:
                if cur:
                    lines.append(cur)
                    cur = ""
                lines.extend(_hard_break_word(draw, word, font, max_width))
                continue

            trial = (cur + " " + word).strip()
            if draw.textlength(trial, font=font) <= max_width:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
    return lines


def render_quote(
    name: str,
    text: str,
    avatar_bytes: bytes | None = None,
) -> bytes:
    """
    Renders a quote card and returns WEBP bytes sized to fit Telegram's
    static sticker constraint (one side exactly 512px, other <= 512px).
    """
    name = _clean_display_text((name or "Unknown").strip())[:64]
    text = _clean_display_text((text or "").strip())[:600] or " "

    W = CARD_WIDTH * SCALE
    pad = 60 * SCALE
    avatar_size = 130 * SCALE

    scratch = Image.new("RGB", (10, 10))
    measure_draw = ImageDraw.Draw(scratch)

    name_font = ImageFont.truetype(FONT_BOLD, int(38 * SCALE))
    quote_font = ImageFont.truetype(FONT_REGULAR, int(34 * SCALE))
    quote_mark_font = ImageFont.truetype(FONT_BOLD, int(70 * SCALE))
    footer_font = ImageFont.truetype(FONT_ITALIC, int(24 * SCALE))

    text_x = pad + avatar_size + 40 * SCALE
    max_text_width = W - text_x - pad - 46 * SCALE

    lines = _wrap_text(measure_draw, text, quote_font, max_text_width)
    truncated = len(lines) > MAX_LINES
    if truncated:
        lines = lines[:MAX_LINES]
        lines[-1] = lines[-1].rstrip() + "…"

    line_height = int(34 * SCALE * 1.45)

    text_top = pad + 4 * SCALE
    body_top = text_top + 60 * SCALE
    text_block_height = max(1, len(lines)) * line_height
    content_bottom = body_top + 10 * SCALE + text_block_height + 30 * SCALE
    footer_bottom = content_bottom + 60 * SCALE

    avatar_bottom = pad + avatar_size
    final_h = max(int(footer_bottom), int(avatar_bottom + pad))

    canvas = _vertical_gradient((W, final_h), BG_TOP, BG_BOTTOM)
    draw = ImageDraw.Draw(canvas)

    avatar_x, avatar_y = pad, pad

    if avatar_bytes:
        try:
            av_img = Image.open(io.BytesIO(avatar_bytes))
            av = _circle_avatar(av_img, avatar_size)
        except Exception:
            av = None
    else:
        av = None

    if av is None:
        av = Image.new("RGBA", (avatar_size, avatar_size), (0, 0, 0, 0))
        ad = ImageDraw.Draw(av)
        ad.ellipse((0, 0, avatar_size, avatar_size), fill=ACCENT)
        initial = name[0].upper() if name else "?"
        f = ImageFont.truetype(FONT_BOLD, int(avatar_size * 0.45))
        bbox = ad.textbbox((0, 0), initial, font=f)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        ad.text(
            ((avatar_size - tw) / 2 - bbox[0], (avatar_size - th) / 2 - bbox[1]),
            initial, font=f, fill=(255, 255, 255),
        )

    ring_pad = 6 * SCALE
    ring_box = (
        avatar_x - ring_pad, avatar_y - ring_pad,
        avatar_x + avatar_size + ring_pad, avatar_y + avatar_size + ring_pad,
    )
    draw.ellipse(ring_box, outline=ACCENT, width=int(4 * SCALE))
    canvas.paste(av, (avatar_x, avatar_y), av)

    draw.text((text_x, text_top), name, font=name_font, fill=ACCENT_SOFT)
    draw.text((text_x - 4 * SCALE, body_top - 18 * SCALE), "\u201C", font=quote_mark_font, fill=ACCENT)

    ty = body_top + 10 * SCALE
    for line in lines:
        draw.text((text_x + 46 * SCALE, ty), line, font=quote_font, fill=TEXT_MAIN)
        ty += line_height

    draw.text((pad, content_bottom), "Yuki \u2022 quoted with \u2764", font=footer_font, fill=TEXT_MUTED)

    radius = 40 * SCALE
    mask = Image.new("L", canvas.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, canvas.size[0], canvas.size[1]), radius=radius, fill=255)
    rgba = canvas.convert("RGBA")
    rgba.putalpha(mask)

    final = rgba.resize((rgba.width // SCALE, rgba.height // SCALE), Image.LANCZOS)

    w, h = final.size
    if w >= h:
        new_w, new_h = 512, max(1, round(h * (512 / w)))
    else:
        new_h, new_w = 512, max(1, round(w * (512 / h)))
    final = final.resize((new_w, new_h), Image.LANCZOS)

    buf = io.BytesIO()
    final.save(buf, "WEBP")
    return buf.getvalue()