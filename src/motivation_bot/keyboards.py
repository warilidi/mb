from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from motivation_bot.database import ACTIVITIES


def get_main_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text="⚡ Отметить активность"), KeyboardButton(text="👤 Профиль")],
        [KeyboardButton(text="🏆 Лидерборд"), KeyboardButton(text="🏅 Достижения")],
        [KeyboardButton(text="📜 История"), KeyboardButton(text="❓ Помощь")],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def get_activities_keyboard() -> InlineKeyboardMarkup:
    keyboard = []
    row = []
    for key, act in ACTIVITIES.items():
        button_text = f"{act['emoji']} {act['title']}"
        row.append(InlineKeyboardButton(text=button_text, callback_data=f"actselect_{key}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton(text="Отмена", callback_data="cancel_action")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_activity_quantity_keyboard(act_key: str) -> InlineKeyboardMarkup:
    if act_key not in ACTIVITIES:
        return get_activities_keyboard()

    act = ACTIVITIES[act_key]
    keyboard = []
    row = []

    for val, label in act["presets"]:
        pts = act["calc_pts"](val)
        btn_text = f"{label} (+{pts} {act['stat_title']})"
        row.append(InlineKeyboardButton(text=btn_text, callback_data=f"actq_{act_key}_{val}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([
        InlineKeyboardButton(text="✏️ Ввести значение", callback_data=f"actcustom_{act_key}")
    ])
    keyboard.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data="act_back"),
        InlineKeyboardButton(text="Отмена", callback_data="cancel_action")
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_leaderboard_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(text="Общий рейтинг", callback_data="top_total_xp"),
            InlineKeyboardButton(text="Сила", callback_data="top_strength"),
        ],
        [
            InlineKeyboardButton(text="Интеллект", callback_data="top_intelligence"),
            InlineKeyboardButton(text="Ловкость", callback_data="top_agility"),
        ],
        [
            InlineKeyboardButton(text="Мудрость", callback_data="top_wisdom"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
