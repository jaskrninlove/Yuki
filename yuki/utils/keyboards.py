"""
Yuki Bot - Keyboard Builder
Premium styled inline keyboard layouts.

Colored buttons and button icons use Bot API extra fields through api_kwargs.
If the Telegram client supports them, they will render.
Otherwise Telegram will safely ignore them.
"""

from telegram import InlineKeyboardButton as Btn, InlineKeyboardMarkup as Markup
from yuki.core.config import SUPPORT_LINK, UPDATES_CHANNEL
from yuki.utils.premium import PREMIUM


BOT_USERNAME = "yukkichitbot"


BUTTON_ICONS = {
    "add": "5258362837411045098",
    "help": "5454371323595744068",
    "support": "5172893417717367746",
    "updates": "4904936030232117798",
    "owner": "4904565554943099861",
    "back": "6039539366177541657",
    "close": "5774077015388852135",
    "next": "5884123981706956210",
    "home": "5873147866364514353",
    "gift": "6294236798050638950",
    "rank": "6294073481919208430",
    "refresh": "5355230232724935087",
    "cancel": "5774077015388852135",
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
    "yes": "5123163417326126159",
    "no": "5121063440311386962",
    "feature": "5258024802010026053",
    
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
        # If icon name is given, convert to emoji id
        emoji_id = PREMIUM.get(icon) or BUTTON_ICONS.get(icon) or icon

        if emoji_id:
            api_kwargs["icon_custom_emoji_id"] = str(emoji_id)

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
                "New Features",
                callback_data="newcmds:1",
                style="primary",
                icon=icon("feature"),
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

# ── New Commands Pages ───────────────────────────────────────────────────────
def newcmds_keyboard(page: int, total_pages: int = 4) -> Markup:
    nav = []
    if page > 1:
        nav.append(
            pbtn(
                "Prev",
                callback_data=f"newcmds:{page - 1}",
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
                callback_data=f"newcmds:{page + 1}",
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

# def profile_keyboard() -> Markup:
#     return Markup([
#         [
#             pbtn(
#                 "My Gifts",
#                 callback_data="my_gifts",
#                 style="success",
#                 icon=icon("gift"),
#             ),
#             pbtn(
#                 "Leaderboard",
#                 callback_data="rank_top",
#                 style="primary",
#                 icon=icon("rank"),
#             ),
#         ],
#     ])


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

# ==========================================================
# Profile Keyboard
# ==========================================================

# ==========================================================
# Profile Keyboard
# ==========================================================

# ── Profile ──────────────────────────────────────────────

def profile_keyboard(owner: bool = True):
    return Markup([
        [
            pbtn(" My Gifts", callback_data="my_gifts", style="success", icon="gift"),
            pbtn(" Wallet", callback_data="wallet", style="primary", icon="gold"),
        ],
        [
            pbtn(" Marriage", callback_data="ring", style="primary", icon="ring"),
            pbtn(" Gacha Collection", callback_data="profile_gacha", style="success", icon="gift"),
        ],
        [
            pbtn(" Badges", callback_data="profile_badges", style="primary", icon="trophy"),
            pbtn(" Statistics", callback_data="profile_stats", style="primary", icon="chart"),
        ],
        [
            pbtn(" Refresh", callback_data="profile_refresh", style="success", icon="sparkle"),
        ],
    ])


def profile_back_keyboard() -> Markup:
    """Use on my_gifts / wallet / ring / badges / stats sub-pages so Back returns to Profile, not somewhere else."""
    return Markup([
        [
            pbtn(" Back", callback_data="profile_back", style="primary", icon="back"),
        ]
    ])

# ==========================================================
# Rankings
# ==========================================================

def rankings_keyboard(page: int = 1):
    if page == 1:
        return Markup([
            [
                pbtn(" Richest", callback_data="rk_rich", style="success", icon="gold"),
                pbtn(" Levels", callback_data="rk_level", style="primary", icon="star"),
            ],
            [
                pbtn(" Reputation", callback_data="rk_rep", style="primary", icon="heart"),
                pbtn(" Activity", callback_data="rk_active", style="primary", icon="chart"),
            ],
            [
                pbtn(" Chat Top", callback_data="rk_top", style="primary", icon="trophy"),
                pbtn(" Global Top", callback_data="rk_globaltop", style="primary", icon="signal"),
            ],
            [
                pbtn(" Next", callback_data="rk_page:2", style="primary", icon="next"),
            ],
            [
                pbtn(" Close", callback_data="close", style="danger", icon="close"),
            ],
        ])

    return Markup([
        [
            pbtn(" My Rank", callback_data="rk_rank", style="primary", icon="rank"),
            pbtn(" Today", callback_data="rk_today", style="primary", icon="calendar"),
        ],
        [
            pbtn(" Statistics", callback_data="rk_stats", style="success", icon="database"),
            pbtn(" Love", callback_data="rk_love", style="primary", icon="heart"),
        ],
        [
            pbtn(" Referrals", callback_data="rk_refer", style="primary", icon="signal"),
        ],
        [
            pbtn(" Back", callback_data="rk_page:1", style="primary", icon="back"),
            pbtn(" Close", callback_data="close", style="danger", icon="close"),
        ],
    ])

def rankings_back_keyboard():
    return Markup([
        [
            pbtn(" Back", callback_data="rk_back", style="primary", icon="back"),
            pbtn(" Close", callback_data="close", style="danger", icon="close"),
        ],
    ])
# ==========================================================
# Marriage
# ==========================================================

def propose_keyboard(proposer_id: int, target_id: int) -> Markup:
    return Markup([
        [
            pbtn(" Accept", callback_data=f"marry_accept:{proposer_id}:{target_id}", style="success", icon="yes"),
            pbtn(" Reject", callback_data=f"marry_reject:{proposer_id}:{target_id}", style="danger", icon="no"),
        ]
    ])


def divorce_confirm_keyboard(user_id: int) -> Markup:
    return Markup([
        [
            pbtn(" Yes, Divorce", callback_data=f"divorce_confirm:{user_id}", style="danger", icon="warning"),
            pbtn(" Cancel", callback_data="cancel", style="primary", icon="no"),
        ]
    ])

# ==========================================================
# Withdrawal
# ==========================================================

def withdraw_tiers_keyboard(tiers: list) -> Markup:
    rows = []
    for cost, label in tiers:
        rows.append([
            pbtn(f" {label} — {cost:,} pts", callback_data=f"wd_pick:{cost}", style="primary", icon="gold"),
        ])
    rows.append([
        pbtn(" Back", callback_data="wd_back", style="primary", icon="back"),
        pbtn(" Cancel", callback_data="cancel", style="danger", icon="no"),
    ])
    return Markup(rows)

def withdraw_info_keyboard() -> Markup:
    return Markup([
        [pbtn(" Withdraw", callback_data="wd_open", style="success", icon="gold")],
        [pbtn(" Owner", callback_data="owner", style="primary", icon="owner")],
    ])

def withdraw_admin_keyboard(req_id: int) -> Markup:
    return Markup([
        [
            pbtn(" Approve", callback_data=f"wd_approve:{req_id}", style="success", icon="yes"),
            pbtn(" Reject", callback_data=f"wd_reject:{req_id}", style="danger", icon="no"),
        ]
    ])

# ==========================================================
# Gacha Collection (paginated card browser)
# ==========================================================
# Add this near the other rankings/gacha related sections in keyboards.py

COLLECTION_PER_PAGE = 8  # 4 rows x 2 columns


def collection_keyboard(companion_ids: list, all_companions: dict, page: int, total_pages: int) -> Markup:
    """
    companion_ids: OWNED companion ids to show on THIS page (already sliced).
    Only pass ids the user actually owns — locked ones are not shown at all.
    """
    rows = []
    row = []

    for cid in companion_ids:
        data = all_companions[cid]

        row.append(
            pbtn(
                data["name"],
                callback_data=f"col_card:{cid}:{page}",
                style="success",
            )
        )

        if len(row) == 2:
            rows.append(row)
            row = []

    if row:
        rows.append(row)

    nav = []

    if page > 1:
        nav.append(pbtn("Back", callback_data=f"col_page:{page - 1}", style="primary", icon="back"))

    nav.append(pbtn(f"{page}/{total_pages}", callback_data="noop", style="primary"))

    if page < total_pages:
        nav.append(pbtn("Next", callback_data=f"col_page:{page + 1}", style="primary", icon="next"))

    rows.append(nav)
    rows.append([pbtn("Close", callback_data="close", style="danger", icon="close")])

    return Markup(rows)


def collection_card_keyboard(page: int) -> Markup:
    """Shown when viewing a single companion's card — returns to the same collection page."""
    return Markup([
        [
            pbtn("Back", callback_data=f"col_back:{page}", style="primary", icon="back"),
            pbtn("Close", callback_data="close", style="danger", icon="close"),
        ]
    ])

def wordgrid_rankings_keyboard() -> Markup:
    return Markup([
        [
            pbtn(" Group", callback_data="wgrank_group", style="primary", icon="chat"),
            pbtn(" Global", callback_data="wgrank_global", style="success", icon="signal"),
        ],
        [
            pbtn(" Today", callback_data="wgrank_today", style="primary", icon="calendar"),
            pbtn(" My Points", callback_data="wgrank_me", style="danger", icon="star"),
        ],
        [
            pbtn(" Close", callback_data="close", style="danger", icon="warning"),
        ],
    ])