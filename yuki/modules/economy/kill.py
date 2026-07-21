"""
Yuki Kill
Copyright © Jass
"""

from datetime import datetime, timedelta, timezone

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from yuki.core import config
from yuki.database.economy import (
    get,
    add,
    remove,
    set_pair_cooldown,
    pair_seconds_remaining,
    has_shield,
    has_permanent_shield,
    add_kill,
    get_kills,
    add_withdraw,
    set_dead,
    is_dead,
    dead_remaining,
)

from yuki.utils import premium
from yuki.utils.premium import reply
from yuki.utils.rewards import (
    kill_reward,
    KILL_COOLDOWN,
    kill_milestone_bonus,
    DEATH_PROTECTION,
)


def _fmt(seconds: int) -> str:
    h, rem = divmod(seconds, 3600)
    m, _ = divmod(rem, 60)
    if h:
        return f"{h}h {m}m"
    return f"{m}m"


async def kill_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    sender = update.effective_user

    if not message.reply_to_message:
        return await reply(
            message,
            """
:warning: <b>Reply Required</b>

Reply to someone's message to kill them.

Example:
<code>/kill</code>
""",
        )

    target = message.reply_to_message.from_user

    if target.id == sender.id:
        return await reply(message, ":warning: You can't kill yourself silly~")

    if target.is_bot:
        return await reply(message, ":warning: You can't kill a bot~")

    if has_permanent_shield(sender.id) and sender.id != config.OWNER_ID:
        return await reply(
            message,
            """
:shield: <b>You Gave Up Your Blade~</b>

You chose permanent protection, which means you can no longer attack others.
""",
        )

    if target.id == config.OWNER_ID:
        return await reply(
            message,
            """
:shield: <b>Blocked!</b>

You can't touch the owner~ 👑
""",
        )

    if is_dead(target.id):
        remaining = dead_remaining(target.id)
        return await reply(
            message,
            f"""
:skull: <b>Already Down~</b>

<b>{target.full_name}</b> is still recovering from their last elimination.
Try again in <code>{_fmt(remaining)}</code>.
""",
        )

    remaining = pair_seconds_remaining("kill", sender.id, target.id, KILL_COOLDOWN)
    if remaining:
        return await reply(
            message,
            f":clock: <b>Not Yet~</b>\n\nYou can kill <b>{target.full_name}</b> again in <code>{_fmt(remaining)}</code>.",
        )

    set_pair_cooldown("kill", sender.id, target.id, datetime.now(timezone.utc))

    if has_shield(target.id):
        return await reply(
            message,
            f"""
:shield: <b>Blocked!</b>

<b>{target.full_name}</b> is protected by a shield.
Your attack failed~
""",
        )

    target_balance = get(target.id)["balance"]
    amount = kill_reward(target_balance)

    if amount > 0:
        remove(target.id, amount)
        add(sender.id, amount)

    set_dead(target.id, datetime.now(timezone.utc) + timedelta(seconds=DEATH_PROTECTION))

    kills_before = get_kills(sender.id)
    add_kill(sender.id)
    kills = get_kills(sender.id)

    from yuki.database.achievements import check_kill_milestones
    check_kill_milestones(sender.id, kills)

    bonus = kill_milestone_bonus(kills_before, kills)
    bonus_text = ""
    if bonus:
        add_withdraw(sender.id, bonus)
        bonus_text = f"\n\n:gift: <b>Milestone Reached!</b>\n<code>+${bonus}</code> added to your withdrawable balance~"

        from yuki.utils.helpers import mention_html
        try:
            await premium.send(
                context.bot,
                sender.id,
                f":tada: <b>Kill Milestone!</b>\n\n{mention_html(sender)}, you've hit <code>{kills}</code> kills!\n:gift: <code>+${bonus}</code> added to your withdrawable balance~",
            )
        except Exception:
            pass

    await reply(
        message,
        f"""
:crossed_swords: <b>Elimination Successful!</b>

You took down <b>{target.full_name}</b> and looted <code>{amount:,}</code> coins~

:skull: <b>{target.full_name}</b> is down for <code>{_fmt(DEATH_PROTECTION)}</code>~

:fire: <b>Total Kills</b> <code>{kills:,}</code>
{bonus_text}
""",
    )


KILL = CommandHandler("kill", kill_cmd)
