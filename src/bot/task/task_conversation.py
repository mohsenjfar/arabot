from telegram.ext import (
    ConversationHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler
)

commons.constants import (
    VIEW, DELETE_TASK, DESCRIPTION, FREQUENCY,
    START, EDIT_TASK, END, SUMMARY
)

task.task_calbacks import (
    edit_task_callbacks,
    edit_summary,
    edit_description,
    edit_start,
    edit_freq,
    delete_task_callback,
    insert_task_cancel
)

task_conversation = ConversationHandler(
        entry_points=[CallbackQueryHandler(edit_task_callbacks)],
        states={
            SUMMARY: [
                CallbackQueryHandler(edit_summary),
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_summary)
            ],
            DESCRIPTION: [
                CallbackQueryHandler(edit_description),
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_description)
            ],
            START: [
                CallbackQueryHandler(edit_start),
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_start)
            ],
            FREQUENCY: [
                CallbackQueryHandler(edit_freq),
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_freq)
            ],
            DELETE_TASK: [CallbackQueryHandler(delete_task_callback)]
        },
        fallbacks=[CallbackQueryHandler(insert_task_cancel)],
        map_to_parent={END: VIEW, EDIT_TASK:EDIT_TASK},
    )