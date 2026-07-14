"""
Yuki XP Engine
Copyright © Jass

Handles:
- XP Formula
- Level Progression
- Message XP
"""

from __future__ import annotations

import random

# ==========================================================
# XP SETTINGS
# ==========================================================

MIN_XP = 2
MAX_XP = 5

MESSAGE_COOLDOWN = 30  # seconds

XP_PER_LEVEL = 100  # matches core.database._level_for_xp: level = (xp // 100) + 1


# ==========================================================
# XP Formula
# ==========================================================

def xp_required(level: int) -> int:
    """
    XP needed to go from the current level to the next.

    This is intentionally a constant, matching the linear leveling
    formula used when XP is granted: level = (total_xp // 100) + 1.
    """
    return XP_PER_LEVEL


def xp_in_level(total_xp: int) -> int:
    """XP earned within the current level (resets every XP_PER_LEVEL)."""
    return total_xp % XP_PER_LEVEL


# ==========================================================
# Random XP
# ==========================================================

def random_xp() -> int:
    """
    XP gained per valid message.
    """
    return random.randint(MIN_XP, MAX_XP)


# ==========================================================
# Progress
# ==========================================================

def progress(current_xp: int, level: int) -> float:
    """
    Returns progress percentage within the current level.

    Example:
        53.82
    """
    required = xp_required(level)

    if required <= 0:
        return 100.0

    return round((xp_in_level(current_xp) / required) * 100, 2)


# ==========================================================
# Progress Bar
# ==========================================================

def progress_bar(current_xp: int, level: int, length: int = 10) -> str:
    """
    Example:

    ■■■■■■■□□□
    """

    required = xp_required(level)
    in_level = xp_in_level(current_xp)

    filled = int((in_level / required) * length)
    filled = min(length, filled)

    return "■" * filled + "□" * (length - filled)


# ==========================================================
# Level Check (legacy — not currently used by the XP listener,
# which computes level directly via total_xp // 100 + 1)
# ==========================================================

def check_level(level: int, xp: int):
    """
    Returns:

    (
        new_level,
        remaining_xp,
        leveled_up
    )
    """

    leveled = False

    while xp >= xp_required(level):
        xp -= xp_required(level)
        level += 1
        leveled = True

    return level, xp, leveled