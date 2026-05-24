import logging

from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters
)

from .message_handlers import message_handler

from .command_handlers import (
    start_command_handler,
    restart_command_handler
)

from commons.constants import *

logger = logging.getLogger(__name__)

END = ConversationHandler.END

main_conversation = ConversationHandler(
    name="main_conversation",
    entry_points=[CommandHandler("start", start_command_handler)],
    states={
        CHAT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler),
        ]
    },
    fallbacks=[
        CommandHandler("start", restart_command_handler)
    ],
    persistent=True
)