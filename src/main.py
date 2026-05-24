import os
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
if BASE_DIR not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import logging

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.WARNING)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

logger.info(f'BASE_DIR: {BASE_DIR}')

from telegram.ext import (
    Application, 
    ConversationHandler,
    PicklePersistence,
)

from app.conversation_handlers import main_conversation

from commons.constants import *

END = ConversationHandler.END

BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_PERSISTENCE_URL = os.getenv("BOT_PERSISTENCE_URL")
BOT_URL = os.getenv("BOT_URL")

def main() -> None:

    persistence = PicklePersistence(filepath=BOT_PERSISTENCE_URL, update_interval=5)

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .base_url(BOT_URL)
        .persistence(persistence)
        .read_timeout(30)
        .connect_timeout(30)
        .build()
    )

    application.add_handler(main_conversation)

    logger.info("Start polling...")

    application.run_polling()

if __name__ == "__main__":
    main()
