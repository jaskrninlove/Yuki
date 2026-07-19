"""
Yuki Database - Word Grid
Copyright © Jass
"""

from __future__ import annotations

from pymongo.collection import Collection

from yuki.core.config import DB

wordgrid_active: Collection = DB.wordgrid_active  # _id = chat_id (in-memory mirror, not critical to persist deeply)