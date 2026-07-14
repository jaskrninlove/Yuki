"""
Yuki Gacha - Companion Roster
Copyright © Jass
"""

from __future__ import annotations

from pathlib import Path

COMMON = "common"
RARE = "rare"
EPIC = "epic"
LEGENDARY = "legendary"

RARITY_WEIGHTS = {
    COMMON: 60,
    RARE: 27,
    EPIC: 10,
    LEGENDARY: 3,
}

RARITY_LABELS = {
    COMMON: "Common",
    RARE: "Rare",
    EPIC: "Epic",
    LEGENDARY: "Legendary",
}

RARITY_ORDER = [LEGENDARY, EPIC, RARE, COMMON]

# id -> {name, emoji, rarity}
COMPANIONS: dict[str, dict] = {
    # ---- Common ----
    "sleepy_star":    {"name": "Sleepy Star",    "emoji": "⭐", "rarity": COMMON},
    "baby_moth":      {"name": "Baby Moth",      "emoji": "🦋", "rarity": COMMON},
    "tiny_cloud":     {"name": "Tiny Cloud",     "emoji": "☁️", "rarity": COMMON},
    "petal_sprite":   {"name": "Petal Sprite",   "emoji": "🌸", "rarity": COMMON},
    "dust_bunny":     {"name": "Dust Bunny",     "emoji": "🐇", "rarity": COMMON},
    "cotton_chick":   {"name": "Cotton Chick",   "emoji": "🐥", "rarity": COMMON},
    "pebble_turtle":  {"name": "Pebble Turtle",  "emoji": "🐢", "rarity": COMMON},
    "dewdrop_frog":   {"name": "Dewdrop Frog",   "emoji": "🐸", "rarity": COMMON},
    "sprout_sprite":  {"name": "Sprout Sprite",  "emoji": "🌱", "rarity": COMMON},
    "honey_bee":      {"name": "Honey Bee",      "emoji": "🐝", "rarity": COMMON},

    # ---- Rare ----
    "moonlit_fox":    {"name": "Moonlit Fox",    "emoji": "🦊", "rarity": RARE},
    "starlight_owl":  {"name": "Starlight Owl",  "emoji": "🦉", "rarity": RARE},
    "crystal_deer":   {"name": "Crystal Deer",   "emoji": "🦌", "rarity": RARE},
    "aurora_fish":    {"name": "Aurora Fish",    "emoji": "🐟", "rarity": RARE},
    "whisper_cat":    {"name": "Whisper Cat",    "emoji": "🐈", "rarity": RARE},
    "comet_hare":     {"name": "Comet Hare",     "emoji": "🐇", "rarity": RARE},
    "frost_sparrow":  {"name": "Frost Sparrow",  "emoji": "🐦", "rarity": RARE},
    "dream_jelly":    {"name": "Dream Jelly",    "emoji": "🎐", "rarity": RARE},

    # ---- Epic ----
    "celestial_wolf":     {"name": "Celestial Wolf",     "emoji": "🐺", "rarity": EPIC},
    "nebula_dragon":      {"name": "Nebula Dragon",      "emoji": "🐉", "rarity": EPIC},
    "twilight_phoenix":   {"name": "Twilight Phoenix",   "emoji": "🔥", "rarity": EPIC},
    "starforged_unicorn": {"name": "Starforged Unicorn", "emoji": "🦄", "rarity": EPIC},
    "void_panther":       {"name": "Void Panther",       "emoji": "🐆", "rarity": EPIC},
    "galaxy_serpent":     {"name": "Galaxy Serpent",     "emoji": "🐍", "rarity": EPIC},

    # ---- Legendary ----
    "guardian_star":     {"name": "Yuki's Guardian Star",       "emoji": "🌟", "rarity": LEGENDARY},
    "moonflower_spirit": {"name": "Eternal Moonflower Spirit",  "emoji": "🌙", "rarity": LEGENDARY},
    "empress_butterfly": {"name": "Cosmic Empress Butterfly",   "emoji": "👑", "rarity": LEGENDARY},
    "the_first_wish":    {"name": "The First Wish",             "emoji": "✨", "rarity": LEGENDARY},
}

TOTAL_COMPANIONS = len(COMPANIONS)

COMPANIONS_BY_RARITY: dict[str, list[str]] = {r: [] for r in RARITY_ORDER}
for cid, data in COMPANIONS.items():
    COMPANIONS_BY_RARITY[data["rarity"]].append(cid)


# ==========================================================
# AI-generated card images (yuki/assets/gacha_cards/1.png ... 28.png)
# ==========================================================

CARD_DIR = Path(__file__).parent.parent / "assets" / "gacha_cards"

# Companion id -> card image number (1-28), based on definition order above.
CARD_IMAGE_MAP: dict[str, str] = {
    cid: str(i + 1) for i, cid in enumerate(COMPANIONS.keys())
}


def get_card_bytes(companion_id: str) -> bytes | None:
    number = CARD_IMAGE_MAP.get(companion_id)
    if not number:
        return None
    for ext in (".png", ".jpg", ".jpeg"):
        path = CARD_DIR / f"{number}{ext}"
        if path.exists():
            return path.read_bytes()
    return None