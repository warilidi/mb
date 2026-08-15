import math
from aiogram import Router, F
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import motivation_bot.database as db
import motivation_bot.keyboards as kb
from motivation_bot.data_loader import load_ranks
from motivation_bot.states import ActivityForm
from motivation_bot.i18n import t

router = Router()
RANKS_LIST = load_ranks()


def get_rank_title(level: int) -> str:
    for rank_item in RANKS_LIST:
        if level < rank_item["max_lvl"]:
            return rank_item["title"]
    return "Легенда"


def make_progress_bar(xp_in_level: int, max_xp: int = 50, length: int = 10) -> str:
    percent = min(1.0, max(0.0, xp_in_level / max_xp))
    filled = math.floor(percent * length)
    bar = "█" * filled + "░" * (length - filled)
    return f"[{bar}] {int(percent * 100)}%"


@router.message(CommandStart())
async def start_cmd(message: Message, state: FSMContext):
    await state.clear()
    user = message.from_user
    await db.register_user(user.id, user.username, user.first_name)

    text = t("welcome", first_name=user.first_name)

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=kb.get_main_keyboard(),
    )


@router.message(Command("profile"))
@router.message(F.text == "👤 Профиль")
async def profile_cmd(message: Message, state: FSMContext):
    await state.clear()
    user = message.from_user
    await db.register_user(user.id, user.username, user.first_name)
    user_data = await db.get_user(user.id)

    if not user_data:
        await message.answer(t("profile_not_found"))
        return

    total_xp = user_data["total_xp"]
    level = 1 + (total_xp // 50)
    xp_in_level = total_xp % 50
    progress_bar = make_progress_bar(xp_in_level, 50)
    rank = get_rank_title(level)
    streak = user_data["streak_days"] or 0

    profile_text = t(
        "profile",
        first_name=user_data["first_name"],
        rank=rank,
        level=level,
        progress_bar=progress_bar,
        xp_in_level=xp_in_level,
        streak=streak,
        strength=user_data["strength"],
        intelligence=user_data["intelligence"],
        agility=user_data["agility"],
        wisdom=user_data["wisdom"],
        health=user_data["health"],
        total_xp=total_xp,
    )

    await message.answer(profile_text, parse_mode="Markdown")


@router.message(Command("log"))
@router.message(F.text == "⚡ Отметить активность")
async def log_activity_cmd(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        t("select_activity"),
        reply_markup=kb.get_activities_keyboard(),
    )


@router.callback_query(F.data == "cancel_action")
async def cancel_action_cb(query: CallbackQuery, state: FSMContext):
    await state.clear()
    await query.answer()
    await query.message.edit_text(t("action_cancelled"))


@router.callback_query(F.data == "act_back")
async def act_back_cb(query: CallbackQuery, state: FSMContext):
    await state.clear()
    await query.answer()
    await query.message.edit_text(
        t("select_activity"),
        reply_markup=kb.get_activities_keyboard(),
    )


@router.callback_query(F.data.startswith("actselect_"))
async def act_select_cb(query: CallbackQuery, state: FSMContext):
    await state.clear()
    await query.answer()
    act_key = query.data.replace("actselect_", "")

    if act_key in db.ACTIVITIES:
        act = db.ACTIVITIES[act_key]
        await query.message.edit_text(
            t("activity_prompt", emoji=act["emoji"], title=act["title"], prompt=act["prompt"]),
            parse_mode="Markdown",
            reply_markup=kb.get_activity_quantity_keyboard(act_key),
        )


@router.callback_query(F.data.startswith("actcustom_"))
async def act_custom_cb(query: CallbackQuery, state: FSMContext):
    await query.answer()
    act_key = query.data.replace("actcustom_", "")

    if act_key in db.ACTIVITIES:
        act = db.ACTIVITIES[act_key]
        await state.set_state(ActivityForm.waiting_for_quantity)
        await state.update_data(pending_act=act_key)
        await query.message.edit_text(
            t("custom_activity_prompt", emoji=act["emoji"], title=act["title"], prompt=act["prompt"]),
            parse_mode="Markdown",
        )


@router.callback_query(F.data.startswith("actq_"))
async def act_preset_cb(query: CallbackQuery, state: FSMContext):
    await state.clear()
    await query.answer()
    parts = query.data.split("_")

    if len(parts) >= 3:
        act_key = parts[1]
        val = float(parts[2])
        user = query.from_user
        await db.register_user(user.id, user.username, user.first_name)
        res = await db.add_activity(user.id, act_key, val)

        if not res:
            await query.message.edit_text("Ошибка: Неизвестная активность.")
            return

        act = res["activity"]
        msg = t(
            "activity_recorded",
            title=act["title"],
            quantity_str=res["quantity_str"],
            gained=res["gained"],
            stat_title=act["stat_title"],
            streak=res["streak"],
        )

        if res["new_achievements"]:
            msg += t("new_achievements_header")
            for ach in res["new_achievements"]:
                if ach.get("secret"):
                    msg += t("achievement_secret_item", title=ach["title"], desc=ach["desc"])
                else:
                    msg += t("achievement_unlocked_item", title=ach["title"], desc=ach["desc"])

        await query.message.edit_text(msg, parse_mode="Markdown")


@router.message(StateFilter(ActivityForm.waiting_for_quantity))
async def text_quantity_input(message: Message, state: FSMContext):
    text_val = message.text.strip()
    data = await state.get_data()
    pending_act = data.get("pending_act")

    if pending_act and pending_act in db.ACTIVITIES:
        try:
            val = float(text_val.replace(",", "."))
            if val <= 0:
                raise ValueError()
        except ValueError:
            await message.answer(t("invalid_number_input"))
            return

        user = message.from_user
        await db.register_user(user.id, user.username, user.first_name)
        res = await db.add_activity(user.id, pending_act, val)
        await state.clear()

        if not res:
            await message.answer("Ошибка записи.")
            return

        act = res["activity"]
        msg = t(
            "activity_recorded",
            title=act["title"],
            quantity_str=res["quantity_str"],
            gained=res["gained"],
            stat_title=act["stat_title"],
            streak=res["streak"],
        )

        if res["new_achievements"]:
            msg += t("new_achievements_header")
            for ach in res["new_achievements"]:
                if ach.get("secret"):
                    msg += t("achievement_secret_item", title=ach["title"], desc=ach["desc"])
                else:
                    msg += t("achievement_unlocked_item", title=ach["title"], desc=ach["desc"])

        await message.answer(msg, parse_mode="Markdown", reply_markup=kb.get_main_keyboard())


@router.message(Command("leaderboard"))
@router.message(F.text == "🏆 Лидерборд")
async def leaderboard_cmd(message: Message, state: FSMContext):
    await state.clear()
    await render_leaderboard(message, "total_xp", is_callback=False)


@router.callback_query(F.data.startswith("top_"))
async def leaderboard_cb(query: CallbackQuery):
    await query.answer()
    stat_type = query.data.replace("top_", "")
    await render_leaderboard(query, stat_type, is_callback=True)


async def render_leaderboard(event, stat_type: str, is_callback: bool):
    rows, stat_title = await db.get_leaderboard(stat_type, limit=10)
    leaderboard_text = t("leaderboard_header", stat_title=stat_title)

    if not rows:
        leaderboard_text += t("leaderboard_empty")
    else:
        for idx, row in enumerate(rows, 1):
            name = row["first_name"] or row["username"] or f"ID {row['user_id']}"
            score = row["score"]
            leaderboard_text += t("leaderboard_row", idx=idx, name=name, score=score)

    if is_callback:
        await event.message.edit_text(
            leaderboard_text,
            parse_mode="Markdown",
            reply_markup=kb.get_leaderboard_keyboard(),
        )
    else:
        await event.answer(
            leaderboard_text,
            parse_mode="Markdown",
            reply_markup=kb.get_leaderboard_keyboard(),
        )


@router.message(Command("achievements"))
@router.message(F.text == "🏅 Достижения")
async def achievements_cmd(message: Message, state: FSMContext):
    await state.clear()
    user = message.from_user
    await db.register_user(user.id, user.username, user.first_name)

    achievements = await db.get_user_achievements(user.id)
    unlocked_cnt = sum(1 for a in achievements if a["unlocked"])

    text = t("achievements_header", unlocked_cnt=unlocked_cnt, total_cnt=len(achievements))
    for ach in achievements:
        status = "✅" if ach["unlocked"] else "🔒"
        text += f"{status} **{ach['title']}**\n   _{ach['desc']}_\n\n"

    await message.answer(text, parse_mode="Markdown")


@router.message(Command("history"))
@router.message(F.text == "📜 История")
async def history_cmd(message: Message, state: FSMContext):
    await state.clear()
    user = message.from_user
    await db.register_user(user.id, user.username, user.first_name)

    logs = await db.get_user_activity_history(user.id, limit=8)

    if not logs:
        text = t("history_empty")
    else:
        text = t("history_header")
        for log in logs:
            dt = log["timestamp"][:16] if log["timestamp"] else ""
            text += t("history_item", title=log["activity_title"], gained=log["stat_gained"], stat_name=log["stat_name"], dt=dt)

    await message.answer(text, parse_mode="Markdown")


@router.message(Command("help"))
@router.message(F.text == "❓ Помощь")
async def help_cmd(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(t("help"), parse_mode="Markdown")

