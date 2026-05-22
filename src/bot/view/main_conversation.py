from telegram.ext import (
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
    InlineQueryHandler
)

task.task_calbacks import create_task_from_input
view.view_callbacks import start, view_query_handlers
setting.setting_callbacks import settings_callbacks
commons.inline_callback import inline_query

task.task_conversation import task_conversation
report.report_conversation import report_conversation
resource.resource_conversation import resource_conversation
resource.task.task_resource_conversation import task_resource_conversation
tags.tag_conversation import tag_conversation

commons.constants import (
    VIEW, RESOURCE, REPORT, TAG,     
    INSERT_RESOURCE, EDIT_TASK, SETTINGS
)

main_conv = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        VIEW: [
            CallbackQueryHandler(view_query_handlers),
            MessageHandler(filters.TEXT & ~filters.COMMAND, create_task_from_input)
        ],
        EDIT_TASK: [task_conversation],
        REPORT: [report_conversation],
        SETTINGS: [
            CallbackQueryHandler(settings_callbacks),
            MessageHandler((filters.TEXT | filters.LOCATION ) & ~filters.COMMAND, settings_callbacks)
        ],
        TAG: [tag_conversation],
        INSERT_RESOURCE: [resource_conversation],
        RESOURCE: [task_resource_conversation]
    },
    fallbacks=[CommandHandler("start", start)]
)

inline_handler = InlineQueryHandler(inline_query)