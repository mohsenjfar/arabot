import logging

from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)

from .message_handlers import (
    create_activity_message_handler,
    llm_message_handler
)

from .command_handlers import (
    start_command_handler,
    restart_command_handler,
    help_command_handler,
    stop_command_handler,
    report_command_handler
)

from .query_handlers import (
    complete_activity_query_handler,
    edit_activity_query_handler,
    skip_activity_query_handler,
    delete_activity_query_handler,
    confirm_delete_activity_query_handler,
    clear_activity_query_handler,
    cancel_query_handler
)

from ..shared.constants import *

logger = logging.getLogger(__name__)

END = ConversationHandler.END

main_conversation = ConversationHandler(
    name="main_conversation",
    entry_points=[CommandHandler("start", start_command_handler)],
    states={
        ACTIVITY: [
            CommandHandler("help", help_command_handler),
            CommandHandler("report", report_command_handler),
            CommandHandler("stop", stop_command_handler),
            MessageHandler(filters.TEXT & ~filters.COMMAND, create_activity_message_handler),
            CallbackQueryHandler(complete_activity_query_handler, pattern="^complete:"),
            CallbackQueryHandler(skip_activity_query_handler, pattern="^skip:"),
            CallbackQueryHandler(delete_activity_query_handler, pattern="^delete:"),
            CallbackQueryHandler(confirm_delete_activity_query_handler, pattern="^confirm_delete:"),
            CallbackQueryHandler(edit_activity_query_handler, pattern="^edit:"),
            CallbackQueryHandler(clear_activity_query_handler, pattern="^clear:")
        ],
        LLM: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, llm_message_handler),
        ]
    },
    fallbacks=[
        CommandHandler("start", restart_command_handler),
        CallbackQueryHandler(cancel_query_handler, pattern="^cancel:")
    ],
    persistent=True
)