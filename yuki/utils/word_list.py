"""
Yuki Word Game - Word List Loader
Copyright © Jass
"""

from __future__ import annotations

import random
from pathlib import Path

# Place your words.txt (one word per line) here:
WORDS_FILE = Path(__file__).parent.parent / "assets" / "words.txt"

MIN_LEN = 4
MAX_LEN = 9

_word_cache: list[str] = []
_loaded = False


def _load():
    global _word_cache, _loaded

    if _loaded:
        return

    words = set()

    if WORDS_FILE.exists():
        with open(WORDS_FILE, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                w = line.strip().lower()
                if w.isalpha() and MIN_LEN <= len(w) <= MAX_LEN:
                    words.add(w)

    _word_cache = list(words)
    _loaded = True


def get_all_words() -> list[str]:
    _load()
    return _word_cache


def random_word() -> str | None:
    _load()
    if not _word_cache:
        return None
    return random.choice(_word_cache)


def scramble(word: str) -> str:
    letters = list(word)
    original = word

    for _ in range(20):
        random.shuffle(letters)
        scrambled = "".join(letters)
        if scrambled != original:
            return scrambled

    return "".join(letters)