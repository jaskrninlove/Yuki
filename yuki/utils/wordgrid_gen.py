"""
Yuki Word Grid — Grid Generation
Copyright © Jass
"""

from __future__ import annotations

import random

DIRECTIONS = [
    (0, 1), (0, -1), (1, 0), (-1, 0),
    (1, 1), (1, -1), (-1, 1), (-1, -1),
]


def generate_grid(words: list[str], size: int = 8, seed: int | None = None, max_attempts: int = 200):
    rng = random.Random(seed)
    words = sorted(set(w.upper() for w in words), key=len, reverse=True)

    for _ in range(max_attempts):
        grid = [[None] * size for _ in range(size)]
        placements = {}
        ok = True

        for word in words:
            candidates = []

            for _ in range(100):
                dr, dc = rng.choice(DIRECTIONS)
                start_r = rng.randint(0, size - 1)
                start_c = rng.randint(0, size - 1)

                end_r = start_r + dr * (len(word) - 1)
                end_c = start_c + dc * (len(word) - 1)
                if not (0 <= end_r < size and 0 <= end_c < size):
                    continue

                path = [(start_r + dr * i, start_c + dc * i) for i in range(len(word))]

                conflict = False
                for (r, c), ch in zip(path, word):
                    existing = grid[r][c]
                    if existing is not None and existing != ch:
                        conflict = True
                        break
                if conflict:
                    continue

                candidates.append(path)
                if len(candidates) >= 5:
                    break

            if not candidates:
                ok = False
                break

            path = rng.choice(candidates)
            for (r, c), ch in zip(path, word):
                grid[r][c] = ch
            placements[word] = path

        if ok and len(placements) == len(words):
            alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            for r in range(size):
                for c in range(size):
                    if grid[r][c] is None:
                        grid[r][c] = rng.choice(alphabet)
            return grid, placements

    raise RuntimeError(f"Could not place all {len(words)} words after {max_attempts} attempts")


def pick_words(word_pool: list[str], length_targets: list[int]) -> list[str]:
    """Picks one random word per target length from the pool."""
    by_length: dict[int, list[str]] = {}
    for w in word_pool:
        by_length.setdefault(len(w), []).append(w)

    chosen = []
    used = set()
    for length in length_targets:
        candidates = [w for w in by_length.get(length, []) if w.upper() not in used]
        if not candidates:
            continue
        word = random.choice(candidates)
        chosen.append(word.upper())
        used.add(word.upper())
    return chosen