from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from database import ACTIVITIES


def get_main_keyboard():
    keyboard = [
        ["⚡ Отметить активность", "👤 Профиль"],
        ["🏆 Лидерборд", "🏅 Достижения"],
        ["📜 История", "❓ Помощь"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_activities_keyboard():
    keyboard = []
    row = []
    for key, act in ACTIVITIES.items():
        button_text = f"{act['emoji']} {act['title']} (+{act['reward']} {act['stat_title']})"
        row.append(InlineKeyboardButton(button_text, callback_data=f"act_{key}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("Отмена", callback_data="cancel_action")])
    return InlineKeyboardMarkup(keyboard)


def get_leaderboard_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("Общий рейтинг", callback_data="top_total_xp"),
            InlineKeyboardButton("Сила", callback_data="top_strength"),
        ],
        [
            InlineKeyboardButton("Интеллект", callback_data="top_intelligence"),
            InlineKeyboardButton("Ловкость", callback_data="top_agility"),
        ],
        [
            InlineKeyboardButton("Мудрость", callback_data="top_wisdom"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

