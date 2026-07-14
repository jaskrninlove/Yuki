"""
Yuki Reward Engine
Copyright © Jass

Shared reward utilities for economy commands.
"""

from __future__ import annotations

import random


# ==========================================================
# Daily
# ==========================================================

DAILY_MIN = 10
DAILY_MAX = 50
GACHA_COMPLETION_REWARD = 100  # withdraw_balance, one-time, for unlocking all companions
WEEKLY_STREAK_BONUS = 2      # withdraw_balance, on every 7th day
MONTHLY_STREAK_BONUS = 10    # withdraw_balance, on every 30th day


def daily_reward() -> int:
    return random.randint(DAILY_MIN, DAILY_MAX)


def daily_streak_bonus(streak: int) -> int:
    """Returns a withdraw_balance bonus for streak milestones. 0 if none hit."""
    if streak and streak % 30 == 0:
        return MONTHLY_STREAK_BONUS
    if streak and streak % 7 == 0:
        return WEEKLY_STREAK_BONUS
    return 0


# ==========================================================
# Work
# ==========================================================

WORK_JOBS = [
    ("Barista", 180, 320),
    ("Programmer", 260, 420),
    ("Streamer", 300, 520),
    ("Designer", 220, 380),
    ("Photographer", 240, 410),
    ("Chef", 180, 350),
    ("Teacher", 170, 330),
    ("Musician", 200, 400),
]


def random_job():
    return random.choice(WORK_JOBS)


def work_reward():
    job, minimum, maximum = random_job()
    reward = random.randint(minimum, maximum)

    return job, reward


# ==========================================================
# Crime
# ==========================================================

CRIME_SUCCESS = 0.55

CRIME_REWARD = (300, 900)

CRIME_FINE = (150, 500)


def crime():
    success = random.random() <= CRIME_SUCCESS

    if success:
        return (
            True,
            random.randint(*CRIME_REWARD),
        )

    return (
        False,
        random.randint(*CRIME_FINE),
    )


# ==========================================================
# Rob
# ==========================================================

ROB_SUCCESS = 0.45
ROB_COOLDOWN = 20 * 60           # 20 minutes          # 3 hours
ROB_MIN_TARGET_BALANCE = 50      # target must have at least this much
ROB_FAIL_FINE = (20, 60)
ROB_MILESTONE_STEP = 10_000      # every 10k total robbed
ROB_MILESTONE_REWARD = 3         # withdraw_balance bonus per step


def rob(maximum: int):
    success = random.random() <= ROB_SUCCESS

    if not success:
        return False, 0

    amount = random.randint(
        100,
        max(100, int(maximum * 0.35)),
    )

    return True, min(amount, maximum)


def rob_milestone_bonus(total_before: int, total_after: int) -> int:
    steps_before = total_before // ROB_MILESTONE_STEP
    steps_after = total_after // ROB_MILESTONE_STEP

    if steps_after > steps_before:
        return ROB_MILESTONE_REWARD * (steps_after - steps_before)

    return 0


# ==========================================================
# Kill
# ==========================================================

KILL_COOLDOWN = 3 * 3600         # 6 hours
KILL_REWARD_RANGE = (50, 150)
KILL_MILESTONE_STEP = 50         # every 50 kills
KILL_MILESTONE_REWARD = 2        # withdraw_balance bonus per step
DEATH_PROTECTION = 3 * 3600      # 3 hours — target can't be killed again while "dead"

SHIELD_COST = 250
SHIELD_DURATION = 12 * 3600      # 12 hours
PERMANENT_SHIELD_COST = 20       # withdraw_balance ($)

def kill_reward(target_balance: int) -> int:
    amount = random.randint(*KILL_REWARD_RANGE)
    return min(amount, target_balance)


def kill_milestone_bonus(kills: int) -> int:
    if kills and kills % KILL_MILESTONE_STEP == 0:
        return KILL_MILESTONE_REWARD
    return 0