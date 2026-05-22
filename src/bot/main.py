from telegram import __version__ as TG_VER
import os
import sys
import logging
from telegram import Update
from telegram.ext import Application
from warnings import filterwarnings
from telegram.warnings import PTBUserWarning

# Keep imports working when this file is executed from project root.
HERE = os.path.dirname(__file__)
SRC = os.path.abspath(os.path.join(HERE, ".."))
if SRC not in sys.path:
    sys.path.insert(0, SRC)

filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.WARNING
)

try:
    from bot.handlers.commons.constants import token
    from src.bot.view.main_conversation import main_conv, inline_handler
except Exception:
    # graceful fallback if moved; try alternate import paths
    try:
        from handlers.commons.constants import token
        from src.bot.view.main_conversation import main_conv, inline_handler
    except Exception:
        token = None
        main_conv = inline_handler = None


def main() -> None:
    """Run the bot (wrapper)."""
    if not token:
        raise RuntimeError("Bot token not found; check handlers.commons.constants")

    application = Application.builder().token(token).read_timeout(10).build()
    if inline_handler:
        application.add_handler(inline_handler)
    if main_conv:
        application.add_handler(main_conv)
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()