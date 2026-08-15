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
        button_text = f"{act['emoji']} {act['title']}"
        row.append(InlineKeyboardButton(button_text, callback_data=f"actselect_{key}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("Отмена", callback_data="cancel_action")])
    return InlineKeyboardMarkup(keyboard)


def get_activity_quantity_keyboard(act_key: str):
    if act_key not in ACTIVITIES:
        return get_activities_keyboard()

    act = ACTIVITIES[act_key]
    keyboard = []
    row = []

    for val, label in act["presets"]:
        pts = act["calc_pts"](val)
        btn_text = f"{label} (+{pts} {act['stat_title']})"
        row.append(InlineKeyboardButton(btn_text, callback_data=f"actq_{act_key}_{val}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([
        InlineKeyboardButton("✏️ Ввести значение", callback_data=f"actcustom_{act_key}")
    ])
    keyboard.append([
        InlineKeyboardButton("⬅️ Назад", callback_data="act_back"),
        InlineKeyboardButton("Отмена", callback_data="cancel_action")
    ])

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

