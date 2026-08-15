import math
from telegram import Update
from telegram.ext import ContextTypes
import database as db
import keyboards as kb


def get_rank_title(level: int) -> str:
    ranks = [
        (3, "Новичок"),
        (6, "Ученик"),
        (10, "Искатель"),
        (15, "Практик"),
        (20, "Знаток"),
        (30, "Мастер"),
        (50, "Грандмастер"),
    ]
    for max_lvl, title in ranks:
        if level < max_lvl:
            return title
    return "Легенда"


def make_progress_bar(xp_in_level: int, max_xp: int = 50, length: int = 10) -> str:
    percent = min(1.0, max(0.0, xp_in_level / max_xp))
    filled = math.floor(percent * length)
    bar = "█" * filled + "░" * (length - filled)
    return f"[{bar}] {int(percent * 100)}%"


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.register_user(user.id, user.username, user.first_name)

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

    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=kb.get_main_keyboard(),
    )


async def profile_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.register_user(user.id, user.username, user.first_name)
    user_data = db.get_user(user.id)

    if not user_data:
        await update.message.reply_text("Профиль не найден. Введите /start")
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

    await update.message.reply_text(profile_text, parse_mode="Markdown")


async def log_activity_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("pending_act", None)
    await update.message.reply_text(
        "Выберите активность для записи:",
        reply_markup=kb.get_activities_keyboard(),
    )


async def activity_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    user = query.from_user
    db.register_user(user.id, user.username, user.first_name)

    if data == "cancel_action":
        context.user_data.pop("pending_act", None)
        await query.edit_message_text("Отменено.")
        return

    if data == "act_back":
        context.user_data.pop("pending_act", None)
        await query.edit_message_text(
            "Выберите активность для записи:",
            reply_markup=kb.get_activities_keyboard()
        )
        return

    if data.startswith("actselect_"):
        act_key = data.replace("actselect_", "")
        if act_key in db.ACTIVITIES:
            act = db.ACTIVITIES[act_key]
            await query.edit_message_text(
                f"{act['emoji']} **{act['title']}**\n{act['prompt']}",
                parse_mode="Markdown",
                reply_markup=kb.get_activity_quantity_keyboard(act_key)
            )
        return

    if data.startswith("actcustom_"):
        act_key = data.replace("actcustom_", "")
        if act_key in db.ACTIVITIES:
            act = db.ACTIVITIES[act_key]
            context.user_data["pending_act"] = act_key
            await query.edit_message_text(
                f"{act['emoji']} **{act['title']}**\n\n💬 {act['prompt']}\n\n_Отправьте число сообщением в чат._",
                parse_mode="Markdown"
            )
        return

    if data.startswith("actq_"):
        parts = data.split("_")
        if len(parts) >= 3:
            act_key = parts[1]
            val = float(parts[2])
            res = db.add_activity(user.id, act_key, val)

            if not res:
                await query.edit_message_text("Ошибка: Неизвестная активность.")
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

            await query.edit_message_text(msg, parse_mode="Markdown")
        return


async def text_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text_val = update.message.text.strip()

    pending_act = context.user_data.get("pending_act")
    if pending_act and pending_act in db.ACTIVITIES:
        try:
            val = float(text_val.replace(",", "."))
            if val <= 0:
                raise ValueError()
        except ValueError:
            await update.message.reply_text(
                "Пожалуйста, введите положительное число (например: 30 или 1.5)."
            )
            return

        user = update.effective_user
        db.register_user(user.id, user.username, user.first_name)
        res = db.add_activity(user.id, pending_act, val)
        context.user_data.pop("pending_act", None)

        if not res:
            await update.message.reply_text("Ошибка записи.")
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

        await update.message.reply_text(
            msg,
            parse_mode="Markdown",
            reply_markup=kb.get_main_keyboard()
        )
        return



async def leaderboard_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await render_leaderboard(update, context, "total_xp", is_callback=False)


async def leaderboard_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    stat_type = query.data.replace("top_", "")
    await render_leaderboard(update, context, stat_type, is_callback=True)


async def render_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE, stat_type: str, is_callback: bool):
    rows, stat_title = db.get_leaderboard(stat_type, limit=10)

    leaderboard_text = f"🏆 **Таблица лидеров — {stat_title}**\n\n"

    if not rows:
        leaderboard_text += "В этой категории пока нет записей."
    else:
        for idx, row in enumerate(rows, 1):
            name = row["first_name"] or row["username"] or f"ID {row['user_id']}"
            score = row["score"]
            leaderboard_text += f"{idx}. **{name}** — `{score}` pts\n"

    if is_callback:
        await update.callback_query.edit_message_text(
            leaderboard_text,
            parse_mode="Markdown",
            reply_markup=kb.get_leaderboard_keyboard(),
        )
    else:
        await update.message.reply_text(
            leaderboard_text,
            parse_mode="Markdown",
            reply_markup=kb.get_leaderboard_keyboard(),
        )


async def achievements_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.register_user(user.id, user.username, user.first_name)

    achievements = db.get_user_achievements(user.id)
    unlocked_cnt = sum(1 for a in achievements if a["unlocked"])

    text = f"🏅 **Достижения ({unlocked_cnt}/{len(achievements)}):**\n\n"

    for ach in achievements:
        status = "✅" if ach["unlocked"] else "🔒"
        text += f"{status} **{ach['title']}**\n   _{ach['desc']}_\n\n"

    await update.message.reply_text(text, parse_mode="Markdown")


async def history_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.register_user(user.id, user.username, user.first_name)

    logs = db.get_user_activity_history(user.id, limit=8)

    if not logs:
        text = "История активностей пока пуста."
    else:
        text = "📜 **Последние записи:**\n\n"
        for log in logs:
            dt = log["timestamp"][:16] if log["timestamp"] else ""
            text += f"• **{log['activity_title']}** (+{log['stat_gained']} {log['stat_name']}) — _{dt}_\n"

    await update.message.reply_text(text, parse_mode="Markdown")


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "ℹ️ **Справка по работе с ботом**\n\n"
        "Каждое выполненное целевое действие развивает характеристики профиля.\n\n"
        "**Система начислений:**\n"
        "• 🏋️ **Тренировка:** +5 Сила\n"
        "• 📚 **Чтение книги:** +10 Интеллект\n"
        "• 🏃 **Пробежка:** +5 Ловкость\n"
        "• 🧘 **Медитация:** +5 Мудрость\n"
        "• 🗣 **Изучение языка:** +8 Интеллект\n"
        "• 💧 **Питьевой режим:** +3 Здоровье\n"
        "• 🛌 **Полноценный сон:** +5 Здоровье\n\n"
        "**Опыт и уровни:**\n"
        "Каждые 50 XP повышают уровень персонажа и обновляют звание.\n\n"
        "**Серия (Streak):**\n"
        "Фиксируйте хотя бы одно действие каждый день, чтобы поддерживать счетчик дней."
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

