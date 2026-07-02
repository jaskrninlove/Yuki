"""
Yuki Bot - Keyboard Builder
Premium styled inline keyboard layouts.

Colored buttons and button icons use Bot API extra fields through api_kwargs.
If the Telegram client supports them, they will render.
Otherwise Telegram will safely ignore them.
"""

from telegram import InlineKeyboardButton as Btn, InlineKeyboardMarkup as Markup
from yuki.core.config import SUPPORT_LINK, UPDATES_CHANNEL


BOT_USERNAME = "yukkichitbot"


BUTTON_ICONS = {
    "add": "6102617459204822706",
    "help": "5258500400918587241",
    "support": "5258361295517806281",
    "updates": "5256227233642605352",
    "owner": "6116023147352298145",
    "back": "6237491831869806976",
    "next": "6242479594570522124",
    "home": "5262671999573977569",
    "gift": "6294236798050638950",
    "rank": "6294073481919208430",
    "refresh": "5355230232724935087",
    "cancel": "6237927637906364256",
    "settings": "5291873529464122510",
    "top": "5334628996887895660",
    "global": "5285439518130857782",
    "profile": "6237927637906364256",
    "rules": "5256227233642605352",
    "welcome": "6294070144729619431",
    "goodbye": "6228735269726586366",
    "notes": "6237491831869806976",
    "filter": "6244501154072368012",
    "afk": "5267334530171169409",
    "yes": "6116023147352298145",
    "no": "5433892975362995314",
    
}

GIFT_BUTTON_ICONS = {
    "ring": "5262922516426420894",
    "bouquet": "6293965450606812914",
    "teddy": "5206502842478638898",
    "rose": "6102617459204822706",
    "cake": "6118216466891281890",
    "ribbon": "6221961320321783118",
    "star": "6237718408574539239",
    "song": "5470135030393090150",
    "choco": "5321310634015482162",
    "lolly": "5262693362741308140",
    "crown": "5931567294265169011",
    "unicorn": "5467658895847608185",
}


def pbtn(
    text: str,
    *,
    callback_data: str | None = None,
    url: str | None = None,
    style: str | None = None,
    icon: str | None = None,
) -> Btn:
    api_kwargs = {}

    if style:
        api_kwargs["style"] = style

    if icon:
        api_kwargs["icon_custom_emoji_id"] = icon

    return Btn(
        text=text,
        callback_data=callback_data,
        url=url,
        api_kwargs=api_kwargs or None,
    )


def icon(name: str) -> str | None:
    return BUTTON_ICONS.get(name) or None


# ── Start Menu ────────────────────────────────────────────────────────────────

def start_keyboard(is_group: bool = False) -> Markup:
    add_url = f"https://t.me/{BOT_USERNAME}?startgroup=true"

    if is_group:
        return Markup([
            [
                pbtn(
                    "Add Me in Your Chat",
                    url=add_url,
                    style="success",
                    icon=icon("add"),
                )
            ]
        ])

    return Markup([
        [
            pbtn(
                "Add Me in Your Chat",
                url=add_url,
                style="success",
                icon=icon("add"),
            )
        ],
        [
            pbtn(
                "Help & Commands",
                callback_data="help:1",
                style="primary",
                icon=icon("help"),
            )
        ],
        [
            pbtn(
                "Support",
                url=SUPPORT_LINK,
                style="primary",
                icon=icon("support"),
            ),
            pbtn(
                "Updates",
                url=UPDATES_CHANNEL,
                style="primary",
                icon=icon("updates"),
            ),
        ],
        [
            pbtn(
                "Owner",
                callback_data="owner",
                style="danger",
                icon=icon("owner"),
            )
        ],
    ])


# ── Owner Panel ───────────────────────────────────────────────────────────────

def owner_keyboard() -> Markup:
    return Markup([
        [
            pbtn(
                "Back",
                callback_data="back_start",
                style="primary",
                icon=icon("back"),
            )
        ]
    ])


# ── Help Pages ────────────────────────────────────────────────────────────────

def help_keyboard(page: int, total_pages: int = 11) -> Markup:
    nav = []

    if page > 1:
        nav.append(
            pbtn(
                "Prev",
                callback_data=f"help:{page - 1}",
                style="primary",
                icon=icon("back"),
            )
        )

    nav.append(
        pbtn(
            f"{page}/{total_pages}",
            callback_data="noop",
            style="primary",
            icon=icon("help"),
        )
    )

    if page < total_pages:
        nav.append(
            pbtn(
                "Next",
                callback_data=f"help:{page + 1}",
                style="primary",
                icon=icon("next"),
            )
        )

    return Markup([
        nav,
        [
            pbtn(
                "Home",
                callback_data="back_start",
                style="success",
                icon=icon("home"),
            )
        ],
    ])


# ── Ranking Keyboards ─────────────────────────────────────────────────────────
# Use these in ranking.py instead of local rank_keyboard if you want centralized UI.

def rank_keyboard(mode: str = "top") -> Markup:
    if mode == "rank":
        return Markup([
            [
                pbtn(
                    "Top 10",
                    callback_data="rank_top",
                    style="primary",
                    icon=icon("top"),
                ),
                pbtn(
                    "Global Top",
                    callback_data="rank_global",
                    style="success",
                    icon=icon("global"),
                ),
            ]
        ])

    return Markup([
        [
            pbtn(
                "Today Rankings",
                callback_data="rank_today",
                style="success",
                icon=icon("rose"),
            )
        ],
        [
            pbtn(
                "Top 10",
                callback_data="rank_top",
                style="primary",
                icon=icon("top"),
            ),
            pbtn(
                "My Rank",
                callback_data="rank_me",
                style="primary",
                icon=icon("profile"),
            ),
        ],
        [
            pbtn(
                "Global Top",
                callback_data="rank_global",
                style="danger",
                icon=icon("global"),
            ),
        ],
    ])


# ── Gift Picker ───────────────────────────────────────────────────────────────

def gift_keyboard(gifts: list, target_user_id: int, page: int = 1) -> Markup:
    total_pages = 2
    per_page = 6

    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    end = start + per_page
    page_gifts = gifts[start:end]

    rows = []
    row = []

    for i, gift in enumerate(page_gifts):
        row.append(
            pbtn(
                gift["name"],
                callback_data=f"gift:{gift['id']}:{target_user_id}",
                style="primary",
                icon=GIFT_BUTTON_ICONS.get(gift["id"]) or icon("gift"),
            )
        )

        if (i + 1) % 2 == 0:
            rows.append(row)
            row = []

    if row:
        rows.append(row)

    nav = []

    if page > 1:
        nav.append(
            pbtn(
                "Back",
                callback_data=f"giftpage:{page - 1}:{target_user_id}",
                style="primary",
                icon=icon("back"),
            )
        )

    nav.append(
        pbtn(
            f"{page}/{total_pages}",
            callback_data="noop",
            style="primary",
            icon=icon("gift"),
        )
    )

    if page < total_pages:
        nav.append(
            pbtn(
                "Next",
                callback_data=f"giftpage:{page + 1}:{target_user_id}",
                style="primary",
                icon=icon("next"),
            )
        )

    rows.append(nav)

    rows.append([
        pbtn(
            "My Gifts",
            callback_data="my_gifts",
            style="success",
            icon=icon("gift"),
        )
    ])

    return Markup(rows)


def my_gifts_keyboard() -> Markup:
    return Markup([
        [
            pbtn(
                "Send a Gift",
                callback_data="open_gift_menu",
                style="success",
                icon=icon("gift"),
            )
        ],
    ])

# ── Profile ───────────────────────────────────────────────────────────────────

def profile_keyboard() -> Markup:
    return Markup([
        [
            pbtn(
                "My Gifts",
                callback_data="my_gifts",
                style="success",
                icon=icon("gift"),
            ),
            pbtn(
                "Leaderboard",
                callback_data="rank_top",
                style="primary",
                icon=icon("rank"),
            ),
        ],
    ])


# ── Welcome / Rules / Group Customization ─────────────────────────────────────

def welcome_settings_keyboard() -> Markup:
    return Markup([
        [
            pbtn(
                "Welcome ON",
                callback_data="welcome:on",
                style="success",
                icon=icon("welcome"),
            ),
            pbtn(
                "Welcome OFF",
                callback_data="welcome:off",
                style="danger",
                icon=icon("no"),
            ),
        ],
        [
            pbtn(
                "Rules",
                callback_data="rules",
                style="primary",
                icon=icon("rules"),
            ),
            pbtn(
                "Back",
                callback_data="back_start",
                style="primary",
                icon=icon("back"),
            ),
        ],
    ])


def rules_keyboard() -> Markup:
    return Markup([
        [
            pbtn(
                "Back",
                callback_data="back_start",
                style="primary",
                icon=icon("back"),
            )
        ]
    ])


# ── Notes / Filters / AFK ─────────────────────────────────────────────────────

def notes_keyboard() -> Markup:
    return Markup([
        [
            pbtn(
                "Notes",
                callback_data="notes",
                style="primary",
                icon=icon("notes"),
            ),
            pbtn(
                "Filters",
                callback_data="filters",
                style="primary",
                icon=icon("filter"),
            ),
        ],
        [
            pbtn(
                "Back",
                callback_data="back_start",
                style="primary",
                icon=icon("back"),
            )
        ],
    ])


def afk_keyboard() -> Markup:
    return Markup([
        [
            pbtn(
                "Back",
                callback_data="back_start",
                style="primary",
                icon=icon("back"),
            )
        ]
    ])


# ── Generic Back / Cancel / Confirm ───────────────────────────────────────────

def back_keyboard(cb: str = "back_start") -> Markup:
    return Markup([
        [
            pbtn(
                "Back",
                callback_data=cb,
                style="primary",
                icon=icon("back"),
            )
        ]
    ])


def cancel_keyboard() -> Markup:
    return Markup([
        [
            pbtn(
                "Cancel",
                callback_data="cancel",
                style="danger",
                icon=icon("cancel"),
            )
        ]
    ])


def confirm_keyboard(yes_cb: str, no_cb: str = "cancel") -> Markup:
    return Markup([
        [
            pbtn(
                "Confirm",
                callback_data=yes_cb,
                style="success",
                icon=icon("yes"),
            ),
            pbtn(
                "Cancel",
                callback_data=no_cb,
                style="danger",
                icon=icon("no"),
            ),
        ]
    ])


def noop_keyboard() -> Markup:
    return Markup([
        [
            pbtn("·", callback_data="noop", style="primary"),
        ]
    ])


# ── Active Users ──────────────────────────────────────────────────────────────

def active_keyboard() -> Markup:
    return Markup([
        [
            pbtn(
                "Refresh",
                callback_data="active_refresh",
                style="primary",
                icon=icon("refresh"),
            )
        ]
    ])


# ── Stats ────────────────────────────────────────────────────────────────────

def stats_keyboard() -> Markup:
    return Markup([
        [
            pbtn(
                "Refresh",
                callback_data="stats",
                style="primary",
                icon=icon("refresh"),
            )
        ]
    ])


# ── Maintenance ───────────────────────────────────────────────────────────────

def maintenance_keyboard(is_on: bool) -> Markup:
    if is_on:
        label = "Turn OFF"
        cb = "maintenance:off"
        style = "danger"
    else:
        label = "Turn ON"
        cb = "maintenance:on"
        style = "success"

    return Markup([
        [
            pbtn(
                label,
                callback_data=cb,
                style=style,
                icon=icon("settings"),
            )
        ],
        [
            pbtn(
                "Back",
                callback_data="back_start",
                style="primary",
                icon=icon("back"),
            )
        ],
    ])