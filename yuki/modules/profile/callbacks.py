from telegram import Update, InputFile
from telegram.ext import ContextTypes

from yuki.core.database import get_user as user_id
from yuki.utils.premium import edit
from yuki.utils.keyboards import profile_keyboard, profile_back_keyboard, collection_keyboard
from yuki.utils.xp import progress_bar, xp_required, xp_in_level
from yuki.core import database as db

from yuki.database.economy import get as get_economy
from yuki.database.reputation import get as get_reputation
from yuki.database.marriage import is_married, get_partner_id, get_love
from yuki.database.achievements import get_unlocked_details, count as achievement_count


async def _resolve_target(update, context):
    """Sub-pages need the same target the /profile command was opened for,
    not just whoever tapped the button."""
    target_id = context.user_data.get("profile_target_id")
    if target_id:
        try:
            return await context.bot.get_chat(target_id)
        except Exception:
            pass
    return update.effective_user


async def _resolve_partner_name(target_id: int, bot) -> str:
    partner_id = get_partner_id(target_id)
    if not partner_id:
        return "Single"
    try:
        partner = await bot.get_chat(partner_id)
        return partner.full_name
    except Exception:
        return "Unknown"


def _build_profile_text(target, user, eco, rep, partner) -> str:
    return f"""
:flower: <b>{target.full_name}</b>

<blockquote>「 {user.get("title") or "Wandering Soul"}</blockquote>

:star: <b>Level</b> <code>{user.get('level', 1)}</code>
:sparkle: <b>XP</b> <code>{xp_in_level(user.get('xp', 0))} / {xp_required(user.get('level', 1))}</code>
<code>{progress_bar(user.get('xp', 0), user.get('level', 1))}</code>

:gold: <b>Balance</b> <code>{eco.get('balance', 0):,}</code> €
:heart: <b>Reputation</b> <code>{rep.get('rep', 0)}</code>
:ring: <b>Partner</b> <code>{partner}</code>
:trophy: <b>Achievements</b> <code>{achievement_count(target.id)}</code>
:chat: <b>Messages</b> <code>{user.get('total_messages', 0):,}</code>
"""


async def profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    base = data.split(":")[0]
    target = await _resolve_target(update, context)
    is_owner = target.id == update.effective_user.id

    if base == "wallet":
        eco = get_economy(target.id)
        gifts = await db.get_user_gifts(target.id)

        await edit(
            query,
            f"""
:wallet: <b>{target.full_name}'s Wallet</b>

:money: Balance: <code>{eco.get('balance', 0):,}</code>
:gem: Withdrawable: <code>${eco.get('withdraw_balance', 0):,}</code>
:gift: Gifts Received: <code>{len(gifts)}</code>
""",
            reply_markup=profile_back_keyboard(),
        )

    elif base == "ring":
        if is_married(target.id):
            partner_name = await _resolve_partner_name(target.id, context.bot)
            love = get_love(target.id)

            await edit(
                query,
                f"""
:ring: <b>{target.full_name}'s Marriage Status</b>

:heart: Status: Married to <b>{partner_name}</b>
:sparkle: Love Points: <code>{love:,}</code>
""",
                reply_markup=profile_back_keyboard(),
            )
        else:
            await edit(
                query,
                f"""
:ring: <b>{target.full_name}'s Marriage Status</b>

:heart: Status: Single

No partner yet :broken_heart:
""",
                reply_markup=profile_back_keyboard(),
            )

    elif base == "profile_badges":
        badges = get_unlocked_details(target.id)

        if not badges:
            body = "No badges unlocked yet.\n\nKeep interacting to earn achievements :sparkle:"
        else:
            body = "\n".join(f"{b['icon']} <b>{b['label']}</b>" for b in badges)

        await edit(
            query,
            f"""
:trophy: <b>{target.full_name}'s Badges</b>

<blockquote>{body}</blockquote>
""",
            reply_markup=profile_back_keyboard(),
        )

    elif base == "profile_stats":
        stats_user = await user_id(target.id) or {}
        rep = get_reputation(target.id)

        await edit(
            query,
            f"""
:chart: <b>{target.full_name}'s Statistics</b>

Level: <code>{stats_user.get('level', 1)}</code>
XP: <code>{stats_user.get('xp', 0)}</code>
Messages: <code>{stats_user.get('total_messages', 0):,}</code>
Reputation: <code>{rep.get('rep', 0)}</code>
""",
            reply_markup=profile_back_keyboard(),
        )

    elif base == "my_gifts":
        gifts = await db.get_user_gifts(target.id)

        if not gifts:
            text = (
                f":gift: <b>{target.full_name}'s Gift Box is Empty~</b>\n\n"
                "<i>No gifts yet! Maybe drop a hint? :cute:</i>"
            )
        else:
            GIFT_PREMIUM = {
                "Ring": ":ring:", "Bouquet": ":bouquet:", "Teddy": ":teddy:",
                "Teddy Bear": ":teddy:", "Rose": ":rose:", "Cake": ":cake2:",
                "Ribbon": ":ribbon2:", "Star": ":star2:", "Song": ":music:",
                "Choco": ":choco:", "Lollipop": ":lollipop:", "Crown": ":crown2:",
                "Unicorn": ":unicorn:",
            }
            lines = []
            for g in gifts[:15]:
                gift_name = g.get("gift_name") or g.get("name") or "Gift"
                emoji = GIFT_PREMIUM.get(gift_name, ":gift:")
                lines.append(f"{emoji} <b>{gift_name}</b>")
            gift_list = "\n".join(lines)
            text = (
                f":ribbon: <b>{target.full_name}'s Gift Collection</b>\n\n"
                f"<blockquote>{gift_list}</blockquote>\n\n"
                f":gift: <b>Total Gifts:</b> <code>{len(gifts)}</code>"
            )

        await edit(query, text, reply_markup=profile_back_keyboard())

    elif base == "profile_gacha":
        from yuki.modules.gacha.game import _owned_ids_sorted, _collection_caption, PER_PAGE
        from yuki.utils.gacha_render import render_collection_banner
        from yuki.utils.gacha_data import COMPANIONS, TOTAL_COMPANIONS
        from yuki.database.gacha import get_collection
        from yuki.utils import premium
        import io

        doc = get_collection(target.id)
        owned_ids = _owned_ids_sorted(target.id)

        if not owned_ids:
            await query.answer(
                "No companions unlocked yet — use /gacha to pull your first one!",
                show_alert=True,
            )
            return

        total_pages = max(1, (len(owned_ids) + PER_PAGE - 1) // PER_PAGE)
        page_ids = owned_ids[:PER_PAGE]
        banner = render_collection_banner(len(doc.get("companions", {})), TOTAL_COMPANIONS)

        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=InputFile(io.BytesIO(banner), filename="collection.png"),
            caption=premium.render(_collection_caption(target, doc)),
            parse_mode="HTML",
            reply_markup=collection_keyboard(page_ids, COMPANIONS, 1, total_pages),
        )

    elif base == "profile_refresh":
        user = await user_id(target.id) or {}
        eco = get_economy(target.id)
        rep = get_reputation(target.id)
        partner = await _resolve_partner_name(target.id, context.bot)
        await edit(
            query,
            _build_profile_text(target, user, eco, rep, partner),
            reply_markup=profile_keyboard(is_owner),
        )

    elif base == "profile_back":
        user = await user_id(target.id) or {}
        eco = get_economy(target.id)
        rep = get_reputation(target.id)
        partner = await _resolve_partner_name(target.id, context.bot)
        await edit(
            query,
            _build_profile_text(target, user, eco, rep, partner),
            reply_markup=profile_keyboard(is_owner),
        )