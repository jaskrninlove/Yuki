"""
Yuki Word Grid — Image Renderer
Copyright © Jass
"""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT_PATH = str(Path(__file__).parent / "quote_assets" / "fonts" / "Poppins-Bold.ttf")

SCALE = 3
CELL = 60 * SCALE
PAD = 20 * SCALE

BG = (255, 255, 255)
GRID_LINE = (225, 225, 230)
TEXT_COLOR = (30, 30, 40)

HIGHLIGHT_COLORS = [
    (120, 200, 190, 170),
    (255, 130, 130, 170),
    (130, 170, 255, 170),
    (140, 220, 140, 170),
    (255, 200, 120, 170),
    (220, 150, 255, 170),
]


def render_grid_image(grid: list[list[str]], found_paths: list[list[tuple[int, int]]]) -> bytes:
    size = len(grid)
    W = H = PAD * 2 + CELL * size

    base = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(base)
    font = ImageFont.truetype(FONT_PATH, int(CELL * 0.42))

    for i in range(size + 1):
        x = PAD + i * CELL
        draw.line([(x, PAD), (x, H - PAD)], fill=GRID_LINE, width=max(1, SCALE))
        y = PAD + i * CELL
        draw.line([(PAD, y), (W - PAD, y)], fill=GRID_LINE, width=max(1, SCALE))

    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)

    for i, path in enumerate(found_paths):
        color = HIGHLIGHT_COLORS[i % len(HIGHLIGHT_COLORS)]
        centers = [(PAD + c * CELL + CELL // 2, PAD + r * CELL + CELL // 2) for r, c in path]
        radius = int(CELL * 0.42)

        if len(centers) == 1:
            x, y = centers[0]
            odraw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)
        else:
            odraw.line(centers, fill=color, width=radius * 2, joint="curve")
            for x, y in (centers[0], centers[-1]):
                odraw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)

    base = Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(base)

    for r in range(size):
        for c in range(size):
            ch = grid[r][c]
            x = PAD + c * CELL + CELL // 2
            y = PAD + r * CELL + CELL // 2
            bbox = draw.textbbox((0, 0), ch, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            draw.text((x - tw / 2 - bbox[0], y - th / 2 - bbox[1]), ch, font=font, fill=TEXT_COLOR)

    final = base.resize((base.width // SCALE, base.height // SCALE), Image.LANCZOS)
    buf = io.BytesIO()
    final.save(buf, "PNG")
    return buf.getvalue()