import logging
import sys
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

import config
import database as db
import handlers

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("bot")


def main() -> None:
    if not config.BOT_TOKEN or config.BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        logger.error("BOT_TOKEN is not configured in .env")
        sys.exit(1)

    db.init_db()

    app = Application.builder().token(config.BOT_TOKEN).build()

    commands = {
        "start": handlers.start_handler,
        "profile": handlers.profile_handler,
        "log": handlers.log_activity_menu_handler,
        "leaderboard": handlers.leaderboard_menu_handler,
        "achievements": handlers.achievements_handler,
        "history": handlers.history_handler,
        "help": handlers.help_handler,
    }
    for cmd, handler in commands.items():
        app.add_handler(CommandHandler(cmd, handler))

    menu_buttons = {
        "^⚡ Отметить активность$": handlers.log_activity_menu_handler,
        "^👤 Профиль$": handlers.profile_handler,
        "^🏆 Лидерборд$": handlers.leaderboard_menu_handler,
        "^🏅 Достижения$": handlers.achievements_handler,
        "^📜 История$": handlers.history_handler,
        "^❓ Помощь$": handlers.help_handler,
    }
    for pattern, handler in menu_buttons.items():
        app.add_handler(MessageHandler(filters.Regex(pattern), handler))

    app.add_handler(CallbackQueryHandler(handlers.activity_callback_handler, pattern="^(act_|cancel_action)"))
    app.add_handler(CallbackQueryHandler(handlers.leaderboard_callback_handler, pattern="^top_"))

    logger.info("Motivation bot started successfully.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

