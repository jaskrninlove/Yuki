"""
Yuki Bot - Locale Loader
Loads en.yml and provides easy string access with format support.
"""

import yaml
import logging
from pathlib import Path
from functools import reduce
from typing import Any

log = logging.getLogger("yuki.locale")

_strings: dict = {}
_LOCALE_DIR = Path(__file__).parent.parent / "locals"


def load(lang: str = "en") -> None:
    global _strings
    path = _LOCALE_DIR / f"{lang}.yml"
    if not path.exists():
        log.warning("Locale file not found: %s, falling back to en", path)
        path = _LOCALE_DIR / "en.yml"
    with open(path, encoding="utf-8") as f:
        _strings = yaml.safe_load(f)
    log.info("✅ Locale loaded: %s", lang)


def get(key: str, **kwargs) -> str:
    """
    Dot-notation access to locale strings.
    e.g. get("start.caption", name="Yuki")
    """
    try:
        value: Any = reduce(lambda d, k: d[k], key.split("."), _strings)
    except (KeyError, TypeError):
        log.warning("Missing locale key: %s", key)
        return key

    if isinstance(value, list):
        import random
        value = random.choice(value)

    if isinstance(value, str) and kwargs:
        try:
            value = value.format(**kwargs)
        except KeyError as e:
            log.warning("Missing format key %s in locale string '%s'", e, key)

    return value


def get_list(key: str) -> list:
    try:
        value = reduce(lambda d, k: d[k], key.split("."), _strings)
        return value if isinstance(value, list) else [value]
    except (KeyError, TypeError):
        return []
