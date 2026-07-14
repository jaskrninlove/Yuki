"""
Yuki Word Game - Puzzle Image Renderer
Copyright © Jass

Renders a pink-gradient letter-tile puzzle image locally with Pillow.
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
FONT_TILE = str(FONT_DIR / "Baloo2-Bold.ttf")

SCALE = 3

PINK_TOP = (255, 175, 205)
PINK_BOTTOM = (255, 130, 170)
CARD_BG = (255, 245, 248)
TILE_BG = (255, 105, 155)
TILE_BG_ALT = (255, 130, 175)
TILE_TEXT = (255, 255, 255)
SPARKLE_COLOR = (255, 255, 255)


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


def render_word_puzzle(scrambled: str) -> bytes:
    """Returns PNG bytes of a pink letter-tile puzzle card."""
    W, H = 900 * SCALE, 500 * SCALE
    canvas = _vertical_gradient((W, H), PINK_TOP, PINK_BOTTOM)
    draw = ImageDraw.Draw(canvas)

    rng = random.Random()
    for _ in range(14):
        x = rng.randint(0, W)
        y = rng.randint(0, int(H * 0.3))
        size = rng.randint(6, 16) * SCALE
        _draw_sparkle(draw, x, y, size, SPARKLE_COLOR)

    heading_font = ImageFont.truetype(FONT_BOLD, int(40 * SCALE))
    heading = "Unscramble the Word!"
    bbox = draw.textbbox((0, 0), heading, font=heading_font)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) / 2, 60 * SCALE), heading, font=heading_font, fill=(255, 255, 255))

    card_pad_x = 70 * SCALE
    card_top = 160 * SCALE
    card_bottom = H - 90 * SCALE
    draw.rounded_rectangle(
        (card_pad_x, card_top, W - card_pad_x, card_bottom),
        radius=50 * SCALE,
        fill=CARD_BG,
    )

    letters = list(scrambled.upper())
    n = len(letters)
    tile_size = 100 * SCALE
    gap = 18 * SCALE
    total_w = n * tile_size + (n - 1) * gap
    max_row_w = (W - card_pad_x * 2) - 80 * SCALE

    if total_w > max_row_w:
        row1 = letters[: (n + 1) // 2]
        row2 = letters[(n + 1) // 2:]
    else:
        row1 = letters
        row2 = []

    tile_font = ImageFont.truetype(FONT_TILE, int(52 * SCALE))

    def draw_row(row, row_y):
        row_w = len(row) * tile_size + (len(row) - 1) * gap
        start_x = (W - row_w) / 2
        for i, ch in enumerate(row):
            x = start_x + i * (tile_size + gap)
            color = TILE_BG if i % 2 == 0 else TILE_BG_ALT
            draw.rounded_rectangle(
                (x, row_y, x + tile_size, row_y + tile_size),
                radius=22 * SCALE,
                fill=color,
            )
            bbox = draw.textbbox((0, 0), ch, font=tile_font)
            cw, ch_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            draw.text(
                (x + (tile_size - cw) / 2 - bbox[0], row_y + (tile_size - ch_h) / 2 - bbox[1]),
                ch, font=tile_font, fill=TILE_TEXT,
            )

    card_center_y = (card_top + card_bottom) / 2
    if row2:
        row_gap = 26 * SCALE
        total_rows_h = tile_size * 2 + row_gap
        y1 = card_center_y - total_rows_h / 2
        y2 = y1 + tile_size + row_gap
        draw_row(row1, y1)
        draw_row(row2, y2)
    else:
        y1 = card_center_y - tile_size / 2
        draw_row(row1, y1)

    footer_font = ImageFont.truetype(FONT_REGULAR, int(26 * SCALE))
    footer = "Yuki Word Game"
    bbox = draw.textbbox((0, 0), footer, font=footer_font)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) / 2, H - 62 * SCALE), footer, font=footer_font, fill=(255, 255, 255))

    final = canvas.resize((canvas.width // SCALE, canvas.height // SCALE), Image.LANCZOS)

    buf = io.BytesIO()
    final.save(buf, "PNG")
    return buf.getvalue()