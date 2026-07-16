"""
╔══════════════════════════════════════════════════════╗
║          Yuki Bot — AI Girlfriend & GC Bestie        ║
║          Version 1.1.0  |  Python 3.11               ║
╚══════════════════════════════════════════════════════╝
"""

import logging
import platform
from datetime import datetime
from telegram import BotCommand
from telegram.ext import Application, CallbackQueryHandler

from yuki.core.config import (
    BOT_TOKEN,
    MONGO_URI,
    MONGO_DB_NAME,
    LOG_GROUP_ID,
    WEBHOOK,
    WEBHOOK_URL,
    PORT,
    OWNER_USERNAME,
    BOT_VERSION,
    validate,
)
from yuki.core.logger import setup_logging, attach_telegram_handler, send_log
from yuki.core import database as db
from yuki.utils.locale import load as load_locale
from yuki.modules.profile.callbacks import profile_callback
from yuki.handlers.closebtn import CLOSE_HANDLER
from yuki.handlers.start import handler as start_h
from yuki.handlers.newcommands import cmd_handler as newcmds_cmd_h, callback_handler as newcmds_cb_h
from yuki.handlers.help import cmd_handler as help_cmd_h, callback_handler as help_cb_h
from yuki.handlers.ping import ping_cmd, ping_cb, health_cmd
from yuki.handlers.chat import (
    text_handler,
    photo_handler,
    video_handler,
    voice_handler,
    sticker_handler,
    init_bot_info,
)
...
from yuki.plugins.stickers import (
    addsticker_handler,
    stickers_count_handler,
    clearstickers_handler,
)

from yuki.handlers.gifts import (
    gift_cmd_handler,
    mygift_cmd_handler,
    gift_cb_handler,
    gift_page_cb_handler,
    cancel_gift_handler,
)

from yuki.plugins.stylish import (
    style_handler,
    style_page_handler,
    style_pick_handler,
)

from yuki.handlers.admin import (
    stats_cmd_h,
    stats_cb_h,
    active_cmd_h,

    ban_cmd_h,
    unban_cmd_h,
    mute_cmd_h,
    unmute_cmd_h,

    setprefix_cmd_h,
    logs_cmd_h,
    groupstats_cmd_h,
    resetdata_cmd_h,

    broadcast_cmd_h,
    maintenance_cmd_h,
    maintenance_cb_h,
    owner_cb_h,
)

from yuki.handlers.callbacks import (
    back_start_handler,
    noop_handler,
    cancel_handler,
    leaderboard_cb_h,
    help_router_handler,
)

from yuki.plugins.utilities import (
    id_handler,
    avatar_handler,
    calc_handler,
    password_handler,
    uuid_handler,
    base64_handler,
    json_handler,
    stickerid_handler,
    getfile_handler,
    url_handler,
    qr_handler,
    google_handler,
    wiki_handler,
    time_handler,
    weather_handler,
    wish_handler,
)

from yuki.plugins.notes import (
    savenote_handler,
    getnote_handler,
    notes_handler,
    delnote_handler,
)

from yuki.plugins.filters import (
    filter_handler,
    remove_handler,
    filters_handler,
    filter_watch_h,
)

from yuki.plugins.welcome import (
    bot_added_handler,
    auto_save_handler,
    setwelcome_handler,
    setgoodbye_handler,
    setrules_handler,
    rules_handler,
    welcome_toggle_handler,
    goodbye_toggle_handler,
    welcome_member_h,
    goodbye_member_h,
    welcome_callback_h,
    welcome_setup_text_h,
)
from yuki.modules.marriage.propose import PROPOSE, PROPOSE_CB
from yuki.modules.marriage.love import LOVE
from yuki.modules.marriage.couple import COUPLE
from yuki.modules.marriage.divorce import DIVORCE, DIVORCE_CB
from yuki.plugins.tagall import tag_handler, yukitag_handler, yukistop_handler, shutdown_telethon
from yuki.plugins.quote import qt_handler, quote_handler
from yuki.plugins.revival import register_revival_job
from yuki.plugins.whisper import whisper_inline_handler, whisper_read_handler
from yuki.plugins.afk import afk_handler, back_handler, afk_watch_h
from yuki.plugins.premium_debug import emojiid_handler
from yuki.handlers.group_events import group_event_handler
from yuki.modules.economy.rob import ROB
from yuki.modules.economy.kill import KILL
from yuki.modules.economy.shield import SHIELD
from yuki.modules.rankings.rankings import RANKINGS
from yuki.modules.rankings.callbacks import RANKINGS_CALLBACK
from yuki.modules.referral.refer import REFER
from yuki.modules.gacha.game import (
    GACHA,
    COLLECTION,
    COLLECTION_PAGE_CB,
    COLLECTION_CARD_CB,
    COLLECTION_BACK_CB,
)
from yuki.plugins.vibes import (
    shayari_h,
    horoscope_h,
    loveletter_h,
    roast_h,
    ship_h,
    compliment_h,
    dare_h,
    fact_h,
    dailymsg_h,
    register_daily_jobs,
)

from yuki.modules.wordgame.game import (
    WORD_STATS_CB,
    TESTWORD_CMD,
    register_word_game_job,
)

from yuki.modules.withdraw.withdraw import (
    WITHDRAW,
    WITHDRAW_TIER_CB,
    WITHDRAW_CONTACT_CAPTURE,
    WITHDRAW_ADMIN_CB,
)

from yuki.plugins.post import (
    create_cmd_h,
    posts_cmd_h,
    sendpost_cmd_h,
    delpost_cmd_h,
    created_post_details_h,
    created_posts_back_h,
    send_created_h,
    delete_created_h,
    post_cmd_h,
    post_to_channel_h,
    post_cancel_h,
    post_channel_event_h,
    connect_cmd_h,
    connect_forward_h,
)

# =========================
# Profile
# =========================
from yuki.modules.profile.profile import PROFILE
from yuki.modules.profile.xp_listener import XP_HANDLER

# =========================
# Economy
# =========================
from yuki.modules.economy.balance import BALANCE
from yuki.modules.economy.daily import DAILY
from yuki.modules.economy.pay import PAY

# =========================
# Social
# =========================
from yuki.modules.social.rep import REP

from yuki.plugins.birthday import (
    bday_h,
    mybirthday_h,
    upcomingbdays_h,
    register_birthday_job,
)

log = logging.getLogger("yuki.main")
def print_startup_banner():
    log.info("=" * 72)
    log.info("YUKI BOT")
    log.info("AI Girlfriend & Group Companion")
    log.info("-" * 72)
    log.info("Copyright (c) 2026 Jass")
    log.info("Developer     : Jass")
    log.info("Version       : 1.1.0")
    log.info("Python        : %s", platform.python_version())
    log.info("Platform      : %s", platform.system())
    log.info("Architecture  : %s", platform.machine())
    log.info("Started       : %s", datetime.now().strftime("%d %b %Y %H:%M:%S"))
    log.info("=" * 72)

async def post_init(app: Application):
    await db.connect(MONGO_URI, MONGO_DB_NAME)
    log.info("[ OK ] Database connection established")

    attach_telegram_handler(app.bot, LOG_GROUP_ID)
    

    me = await app.bot.get_me()
    init_bot_info(me.id, me.username or "")

    await send_log(
        app.bot,
        LOG_GROUP_ID,
        f"✅ <b>Yuki v1.1 Started</b>\n\n"
        f"🤖 Bot: @{me.username}\n"
        f"🆔 ID: <code>{me.id}</code>\n"
        f"💗 Status: Online",
    )

    await app.bot.set_my_commands([
        # ───────── Core ─────────
        BotCommand("start",         "Wake me up 🌸"),
        BotCommand("help",          "Command guide 📖"),
        BotCommand("newcommands", "See new features ✨"),
        BotCommand("ping",          "Check latency 🏓"),
        BotCommand("health",        "Bot health 💚"),
        BotCommand("withdraw",    "Redeem your points 💸"),

        # ───────── Profile & Ranking ─────────
        BotCommand("profile",            "Your profile 🌸"),
        BotCommand("stats",         "Global statistics 📊"),
        BotCommand("active",        "Most active members 🌟"),
        BotCommand("rankings",        "Hall of Fame 🏆"),

        BotCommand("profile",     "View a user's profile 👤"),

        BotCommand("daily",       "Claim your daily reward 💰"),
        BotCommand("bal",         "Check your balance 💵"),
        BotCommand("wallet",      "Open your wallet 👛"),
        BotCommand("balance",     "Check your wallet 💵"),
        BotCommand("pay",         "Send money to someone 💸"),

        BotCommand("rep",         "Give reputation ❤️"),

        BotCommand("rob",         "Rob someone 🥷"),
        BotCommand("kill",        "Eliminate someone ⚔️"),
        BotCommand("shield",      "Buy protection 🛡️"),

        BotCommand("gacha",       "Pull a companion 🎴"),
        BotCommand("collection",  "View your collection 📖"),

        # ───────── Gifts ─────────
        BotCommand("gift",          "Send a gift 🎁"),
        BotCommand("mygift",        "Your gift box 🎀"),

        # ───────── Birthdays ─────────
        BotCommand("bday",          "Save birthday 🎂"),
        BotCommand("mybirthday",    "Your birthday 🎈"),
        BotCommand("upcomingbdays", "Upcoming birthdays 🎉"),

        # ───────── Fun & Vibes ─────────
        BotCommand("ship",          "Love compatibility 💘"),
        BotCommand("loveletter",    "Write love letter 💌"),
        BotCommand("compliment",    "Sweet compliment 🌸"),
        BotCommand("roast",         "Funny roast 🔥"),
        BotCommand("shayari",       "Beautiful shayari 🌹"),
        BotCommand("horoscope",     "Daily horoscope 🔮"),
        BotCommand("dare",          "Random dare 🎯"),
        BotCommand("fact",          "Interesting fact 🧠"),
        BotCommand("dailymsg",      "Auto GM/GN 🌅"),

        BotCommand("propose",     "Propose to someone 💍"),
        BotCommand("couple",      "Couple profile 💑"),
        BotCommand("love",        "Daily love bonus ❤️"),
        BotCommand("divorce",     "End your marriage 💔"),

        BotCommand("refer",       "Get your referral link 🔗"),
        # ───────── Quote ─────────
        BotCommand("qt",            "Quote sticker ✨"),
        BotCommand("quote",         "Quote sticker ✨"),
        BotCommand("yukitag", "Tag all members 📢"),
        BotCommand("yukistop", "Stop active tagging"),

        # ───────── Utilities ─────────
        BotCommand("id",            "User & chat IDs 🆔"),
        BotCommand("avatar",        "User avatar 🖼"),
        BotCommand("calc",          "Calculator 🧮"),
        BotCommand("password",      "Generate password 🔐"),
        BotCommand("uuid",          "Generate UUID 🎲"),
        BotCommand("base64",        "Encode/Decode Base64 📦"),
        BotCommand("json",          "Pretty JSON 📄"),
        BotCommand("qr",            "Generate QR code 📱"),
        BotCommand("wish",          "Wish probability ✨"),
        BotCommand("google",        "Google search 🔎"),
        BotCommand("wiki",          "Wikipedia search 📚"),
        BotCommand("weather",       "Weather forecast 🌦"),
        BotCommand("time",          "World clock 🕒"),
        BotCommand("url",           "Telegram file URL 🔗"),
        BotCommand("stickerid",     "Sticker File ID 🧩"),
        BotCommand("getfile",       "Media File ID 📁"),

        # ───────── Sticker Library ─────────
        BotCommand("addsticker",    "Add safe sticker 🧸"),
        BotCommand("stickers",      "Sticker library 📦"),

        # ───────── Notes ─────────
        BotCommand("savenote",      "Save note 📝"),
        BotCommand("getnote",       "Open note 📖"),
        BotCommand("notes",         "List notes 📚"),
        BotCommand("delnote",       "Delete note ❌"),

        # ───────── Filters ─────────
        BotCommand("filter",        "Create filter 🤖"),
        BotCommand("filters",       "List filters 📋"),
        BotCommand("remove",        "Remove filter 🗑"),

        # ───────── AFK ─────────
        BotCommand("afk",           "Go AFK 😴"),
        BotCommand("back",          "I'm back 👋"),

        # ───────── Group Setup ─────────
        BotCommand("setwelcome",    "Set welcome 👋"),
        BotCommand("welcome",       "Toggle welcome 🌸"),
        BotCommand("setgoodbye",    "Set goodbye 🌙"),
        BotCommand("goodbye",       "Toggle goodbye 👋"),
        BotCommand("setrules",      "Save group rules 📜"),
        BotCommand("rules",         "Show group rules 📖"),

        # ───────── Post ─────────

        BotCommand("create", "Create reusable post 🕸️"),
        BotCommand("posts", "My saved posts 🦄"),
        BotCommand("sendpost", "Send a saved post 🕷️"),
        BotCommand("delpost", "Delete a saved post 🦋"),
        BotCommand("post", "Publish post to channel 🪼"),
        BotCommand("connect", "Connect a channel to bot 🪼"),

        # ───────── Admin ─────────
        BotCommand("broadcast",     "Broadcast 📡"),
        BotCommand("maintenance",   "Maintenance mode 🔧"),

        BotCommand("style",         "Stylish name fonts ✨"),

        BotCommand("ban", "Ban user 🔨"),
        BotCommand("unban", "Unban user ✅"),
        BotCommand("mute", "Mute user 🔇"),
        BotCommand("unmute", "Unmute user 🔊"),
        BotCommand("setprefix", "Set group prefix ⚙️"),
        BotCommand("logs", "Recent bot logs 📜"),
        BotCommand("groupstats", "Group statistics 📊"),
        BotCommand("resetdata", "Reset stored data 🧹"),
    ])


async def post_shutdown(app: Application):
    root = logging.getLogger("yuki")

    for h in list(root.handlers):
        if h.__class__.__name__ == "TelegramLogHandler":
            root.removeHandler(h)
            h.close()

    log.info("-" * 72)
    log.info("Stopping Yuki Bot")
    log.info("Closing Telethon session...")
    await shutdown_telethon()

    log.info("Disconnecting MongoDB...")
    await db.disconnect()

    log.info("Shutdown completed successfully.")
    log.info("Copyright (c) 2026 Jass")
    log.info("-" * 72)


def build_app() -> Application:
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .concurrent_updates(True)
        .read_timeout(60)
        .write_timeout(60)
        .connect_timeout(30)
        .pool_timeout(30)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    # ── Group 0: all commands & callbacks ─────────────────────────────────────
    group0_handlers = [
        start_h,

        # Moved to the very top so no broader/earlier MessageHandler
        # (e.g. help_router_handler, emojiid_handler) can shadow these commands.
        # NOTE: only actual command handlers belong here — connect_forward_h
        # is a broad content-filter MessageHandler and stays in its original spot below.
        create_cmd_h,
        posts_cmd_h,
        sendpost_cmd_h,
        delpost_cmd_h,
        created_post_details_h,
        created_posts_back_h,
        send_created_h,
        delete_created_h,
        post_cmd_h,
        post_to_channel_h,
        post_cancel_h,
        post_channel_event_h,
        connect_cmd_h,

        help_cmd_h,
        help_router_handler,
        help_cb_h,
        ping_cmd,
        ping_cb,
        health_cmd,
        newcmds_cmd_h,
        newcmds_cb_h,

         # =========================
    # Yuki Profile
    # =========================
        PROFILE,

    # =========================
    # Economy
    # =========================
        BALANCE,
        DAILY,
        PAY,
        ROB,
        KILL,
        SHIELD,
        CLOSE_HANDLER,
        PROPOSE,
        PROPOSE_CB,
        LOVE,
        COUPLE,
        DIVORCE,
        DIVORCE_CB,
        REFER,
        WITHDRAW,
        WITHDRAW_TIER_CB,
        WITHDRAW_CONTACT_CAPTURE,
        WITHDRAW_ADMIN_CB,
        WORD_STATS_CB,
        GACHA,
        COLLECTION,
        COLLECTION_PAGE_CB,
        COLLECTION_CARD_CB,
        COLLECTION_BACK_CB,
        TESTWORD_CMD,
    # =========================
    # Social
    # =========================
        REP,

        group_event_handler,

        stats_cmd_h,
        stats_cb_h,
        active_cmd_h,
        ban_cmd_h,
        unban_cmd_h,
        mute_cmd_h,
        unmute_cmd_h,
        setprefix_cmd_h,
        logs_cmd_h,
        groupstats_cmd_h,
        resetdata_cmd_h,
        broadcast_cmd_h,
        maintenance_cmd_h,
        maintenance_cb_h,
        owner_cb_h,

        RANKINGS,
        RANKINGS_CALLBACK,

        gift_cmd_handler,
        mygift_cmd_handler,
        gift_cb_handler,
        gift_page_cb_handler,
        cancel_gift_handler,

        shayari_h,
        horoscope_h,
        loveletter_h,
        roast_h,
        ship_h,
        compliment_h,
        dare_h,
        fact_h,
        dailymsg_h,

        bday_h,
        mybirthday_h,
        upcomingbdays_h,

        bot_added_handler,
        auto_save_handler,

        qt_handler,
        quote_handler,
        tag_handler,
        yukitag_handler,
        yukistop_handler,

        back_start_handler,
        noop_handler,
        cancel_handler,
        leaderboard_cb_h,

        id_handler,
        avatar_handler,
        calc_handler,
        password_handler,
        uuid_handler,
        base64_handler,
        json_handler,
        stickerid_handler,
        getfile_handler,
        url_handler,
        qr_handler,
        google_handler,
        wiki_handler,
        time_handler,
        weather_handler,
        wish_handler,

        style_handler,
        style_page_handler,
        style_pick_handler,

        setwelcome_handler,
        setgoodbye_handler,
        setrules_handler,
        rules_handler,
        welcome_toggle_handler,
        goodbye_toggle_handler,
        welcome_member_h,
        goodbye_member_h,
        welcome_callback_h,
        welcome_setup_text_h,

        whisper_inline_handler,
        whisper_read_handler,

        afk_handler,
        back_handler,

        savenote_handler,
        getnote_handler,
        notes_handler,
        delnote_handler,

        filter_handler,
        remove_handler,
        filters_handler,

        addsticker_handler,
        stickers_count_handler,
        clearstickers_handler,

        emojiid_handler,

        connect_forward_h,
    ]

    for h in group0_handlers:
        app.add_handler(h, group=0)

    # ── Group 1: watchers ─────────────────────────────────────────────────────
    app.add_handler(filter_watch_h,   group=1)
    app.add_handler(afk_watch_h,      group=1)
    # app.add_handler(WORD_ANSWER_HANDLER, group=2)
    app.add_handler(auto_save_handler, group=1)  # fallback group saver

    # ── Group 2: chat catch-all (always last) ─────────────────────────────────
    app.add_handler(sticker_handler, group=2)
    app.add_handler(photo_handler,   group=2)
    app.add_handler(video_handler,   group=2)
    app.add_handler(voice_handler,   group=2)
    # app.add_handler(WORD_ANSWER_HANDLER, group=2)
    app.add_handler(text_handler,    group=2)
    app.add_handler(XP_HANDLER, group=10)
    app.add_handler(
        CallbackQueryHandler(
          profile_callback,
          pattern=r"^(wallet|ring|profile_badges|profile_stats|profile_refresh|profile_back|my_gifts|profile_gacha)$"
          ),
          group=0
    )

    log.info("[ OK ] Message handlers registered: %d", len(group0_handlers) + 9)
    log.info("[ OK ] Dispatcher ready")
    return app


def main():
    setup_logging()
    print_startup_banner()

    validate()
    log.info("[ OK ] Configuration validated")

    load_locale("en")
    log.info("[ OK ] Locale loaded")

    app = build_app()

    register_revival_job(app)
    register_daily_jobs(app)
    register_birthday_job(app)
    register_word_game_job(app)

    log.info("[ OK ] Word game job registered")
    log.info("[ OK ] Job scheduler initialized")
    log.info("[ OK ] Revival job registered")
    log.info("[ OK ] Daily messages job registered")
    log.info("[ OK ] Birthday checker registered")

    log.info("-" * 72)
    log.info("System Status")
    log.info("-" * 72)
    log.info("Telegram API  : CONNECTED")
    log.info("Bot Session   : ACTIVE")
    log.info("Dispatcher    : READY")
    log.info("-" * 72)
    log.info("Yuki Bot is now accepting updates.")
    log.info("-" * 72)

    if WEBHOOK:
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=BOT_TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
            drop_pending_updates=True,
        )
    else:
        app.run_polling(
            drop_pending_updates=True,
            allowed_updates=[
                "message",
                "callback_query",
                "inline_query",
                "my_chat_member",   # ← REQUIRED for bot_added_handler to fire
                "chat_member",
            ],
        )


if __name__ == "__main__":
    main()
