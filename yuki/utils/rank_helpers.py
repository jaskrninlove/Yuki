"""
Yuki Rank Helpers
Copyright © Jass
"""

from __future__ import annotations

from yuki.core import database as core_db


async def get_global_rank(user_id: int) -> int:
    user = await core_db.get_user(user_id)
    my_messages = (user or {}).get("total_messages", 0)

    higher = await core_db.get_db().users.count_documents(
        {"total_messages": {"$gt": my_messages}}
    )
    return higher + 1


async def get_group_rank(chat_id: int, user_id: int) -> int | None:
    """Returns None if the user has no activity in this chat."""
    user = await core_db.get_user(user_id)
    if not user or chat_id not in (user.get("active_chats") or []):
        return None

    my_messages = user.get("total_messages", 0)

    higher = await core_db.get_db().users.count_documents(
        {"active_chats": chat_id, "total_messages": {"$gt": my_messages}}
    )
    return higher + 1