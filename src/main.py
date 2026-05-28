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

from telegram.ext import (
    Application, 
    ConversationHandler,
    PicklePersistence, 
    JobQueue,
)

from handlers.message_handlers import check_and_send_tasks
from handlers.conversation_handlers import main_conversation

from config.constants import *

END = ConversationHandler.END

BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_PERSISTENCE_URL = os.getenv("BOT_PERSISTENCE_URL")
BOT_URL = os.getenv("BOT_URL")

def main() -> None:

    persistence = PicklePersistence(filepath=BOT_PERSISTENCE_URL, update_interval=5)

    job_queue = JobQueue()

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .base_url(BOT_URL)
        .persistence(persistence)
        .job_queue(job_queue)
        .read_timeout(30)
        .connect_timeout(30)
        .build()
    )

    logger.info("Start job with name: task_reminder_job")
    if not job_queue.get_jobs_by_name("task_reminder_job"):
        job_queue.run_repeating(
            callback=check_and_send_tasks,
            interval=60,
            first=10,
            name="task_reminder_job"
        )

    application.add_handler(main_conversation)

    logger.info("Start polling...")

    application.run_polling()

if __name__ == "__main__":
    main()
