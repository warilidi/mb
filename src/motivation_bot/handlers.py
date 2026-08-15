import math
from aiogram import Router, F
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import motivation_bot.database as db
import motivation_bot.keyboards as kb
from motivation_bot.data_loader import load_ranks
from motivation_bot.states import ActivityForm

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

    text = (
        f"Привет, {user.first_name}.\n\n"
        f"Бот помогает превратить полезные привычки в систему прокачки персонажа.\n\n"
        f"**Начисление очков зависит от объема/времени:**\n"
        f"• 🏋️ Тренировка: **~0.35 очка/мин** (Сила)\n"
        f"• 📚 Чтение книги: **~0.5 очка/стр** (Интеллект)\n"
        f"• 🏃 Пробежка: **~3.0 очка/км** (Ловкость)\n"
        f"• 🧘 Медитация: **~0.5 очка/мин** (Мудрость)\n"
        f"• 🗣 Изучение языка: **~0.4 очка/мин** (Интеллект)\n"
        f"• 💧 Питьевой режим: **2.0 очка/литр** (Здоровье)\n"
        f"• 🛌 Полноценный сон: **~0.7 очка/час** (Здоровье)\n\n"
        f"Записывай активность, указывай объем, поднимай уровень и соревнуйся в лидерборде."
    )

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
        await message.answer("Профиль не найден. Введите /start")
        return

    total_xp = user_data["total_xp"]
    level = 1 + (total_xp // 50)
    xp_in_level = total_xp % 50
    progress_bar = make_progress_bar(xp_in_level, 50)
    rank = get_rank_title(level)
    streak = user_data["streak_days"] or 0

    profile_text = (
        f"👤 **Профиль: {user_data['first_name']}**\n"
        f"Звание: **{rank}** | Уровень: **{level}**\n"
        f"Прогресс: {progress_bar} ({xp_in_level}/50 XP)\n"
        f"Серия дней подряд: 🔥 **{streak}**\n\n"
        f"**Характеристики:**\n"
        f"💪 Сила: **{user_data['strength']}**\n"
        f"🧠 Интеллект: **{user_data['intelligence']}**\n"
        f"⚡ Ловкость: **{user_data['agility']}**\n"
        f"🔮 Мудрость: **{user_data['wisdom']}**\n"
        f"❤️ Здоровье: **{user_data['health']}**\n\n"
        f"Суммарный опыт: **{total_xp} XP**"
    )

    await message.answer(profile_text, parse_mode="Markdown")


@router.message(Command("log"))
@router.message(F.text == "⚡ Отметить активность")
async def log_activity_cmd(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Выберите активность для записи:",
        reply_markup=kb.get_activities_keyboard(),
    )


@router.callback_query(F.data == "cancel_action")
async def cancel_action_cb(query: CallbackQuery, state: FSMContext):
    await state.clear()
    await query.answer()
    await query.message.edit_text("Отменено.")


@router.callback_query(F.data == "act_back")
async def act_back_cb(query: CallbackQuery, state: FSMContext):
    await state.clear()
    await query.answer()
    await query.message.edit_text(
        "Выберите активность для записи:",
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
            f"{act['emoji']} **{act['title']}**\n{act['prompt']}",
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
            f"{act['emoji']} **{act['title']}**\n\n💬 {act['prompt']}\n\n_Отправьте число сообщением в чат._",
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
        msg = (
            f"Засчитано: **{act['title']} ({res['quantity_str']})**\n"
            f"Начислено: **+{res['gained']} к {act['stat_title']}**\n"
            f"Серия дней подряд: **{res['streak']}**"
        )

        if res["new_achievements"]:
            msg += "\n\n🏆 **Разблокировано новое достижение!**"
            for ach in res["new_achievements"]:
                if ach.get("secret"):
                    msg += f"\n- 🕵️ **Секретное достижение:** {ach['title']} — _{ach['desc']}_"
                else:
                    msg += f"\n- **{ach['title']}**: _{ach['desc']}_"

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
            await message.answer("Пожалуйста, введите положительное число (например: 30 или 1.5).")
            return

        user = message.from_user
        await db.register_user(user.id, user.username, user.first_name)
        res = await db.add_activity(user.id, pending_act, val)
        await state.clear()

        if not res:
            await message.answer("Ошибка записи.")
            return

        act = res["activity"]
        msg = (
            f"Засчитано: **{act['title']} ({res['quantity_str']})**\n"
            f"Начислено: **+{res['gained']} к {act['stat_title']}**\n"
            f"Серия дней подряд: **{res['streak']}**"
        )

        if res["new_achievements"]:
            msg += "\n\n🏆 **Разблокировано новое достижение!**"
            for ach in res["new_achievements"]:
                if ach.get("secret"):
                    msg += f"\n- 🕵️ **Секретное достижение:** {ach['title']} — _{ach['desc']}_"
                else:
                    msg += f"\n- **{ach['title']}**: _{ach['desc']}_"

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
    leaderboard_text = f"🏆 **Таблица лидеров — {stat_title}**\n\n"

    if not rows:
        leaderboard_text += "В этой категории пока нет записей."
    else:
        for idx, row in enumerate(rows, 1):
            name = row["first_name"] or row["username"] or f"ID {row['user_id']}"
            score = row["score"]
            leaderboard_text += f"{idx}. **{name}** — `{score}` pts\n"

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

    text = f"🏅 **Достижения ({unlocked_cnt}/{len(achievements)}):**\n\n"
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
        text = "История активностей пока пуста."
    else:
        text = "📜 **Последние записи:**\n\n"
        for log in logs:
            dt = log["timestamp"][:16] if log["timestamp"] else ""
            text += f"• **{log['activity_title']}** (+{log['stat_gained']} {log['stat_name']}) — _{dt}_\n"

    await message.answer(text, parse_mode="Markdown")


@router.message(Command("help"))
@router.message(F.text == "❓ Помощь")
async def help_cmd(message: Message, state: FSMContext):
    await state.clear()
    help_text = (
        "ℹ️ **Справка по работе с ботом**\n\n"
        "Каждое выполненное целевое действие развивает характеристики профиля.\n\n"
        "**Система начислений:**\n"
        "• 🏋️ **Тренировка:** ~0.35 очка/мин\n"
        "• 📚 **Чтение книги:** ~0.5 очка/стр\n"
        "• 🏃 **Пробежка:** ~3.0 очка/км\n"
        "• 🧘 **Медитация:** ~0.5 очка/мин\n"
        "• 🗣 **Изучение языка:** ~0.4 очка/мин\n"
        "• 💧 **Питьевой режим:** 2.0 очка/литр\n"
        "• 🛌 **Полноценный сон:** ~0.7 очка/час\n\n"
        "**Опыт и уровни:**\n"
        "Каждые 50 XP повышают уровень персонажа и обновляют звание.\n\n"
        "**Серия (Streak):**\n"
        "Фиксируйте хотя бы одно действие каждый день, чтобы поддерживать счетчик дней."
    )
    await message.answer(help_text, parse_mode="Markdown")
