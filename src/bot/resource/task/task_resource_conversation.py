from telegram.ext import (
    ConversationHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler
)

resource.task.task_resource_callbacks import (
    task_resource_entry_points,
    add_task_resource_amount,
    edit_task_resource_callbacks,
    remove_resource_from_task,
    edit_task_resource_amount
)

commons.constants import (
    EDIT, AMOUNT, REMOVE, EDIT_AMOUNT, RESTART, END, VIEW
)

task_resource_conversation = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(task_resource_entry_points),
        MessageHandler(filters.TEXT & ~filters.COMMAND, task_resource_entry_points)
    ],
    states={
        EDIT: [
            CallbackQueryHandler(edit_task_resource_callbacks),
            MessageHandler(filters.TEXT & ~filters.COMMAND, edit_task_resource_callbacks)
        ],
        AMOUNT: [
            CallbackQueryHandler(add_task_resource_amount),
            MessageHandler(filters.TEXT & ~filters.COMMAND, add_task_resource_amount)
        ],
        REMOVE: [CallbackQueryHandler(remove_resource_from_task)],
        EDIT_AMOUNT: [
            CallbackQueryHandler(edit_task_resource_amount),
            MessageHandler(filters.TEXT & ~filters.COMMAND, edit_task_resource_amount)
        ],
        RESTART: [
            CallbackQueryHandler(task_resource_entry_points),
            MessageHandler(filters.TEXT & ~filters.COMMAND, task_resource_entry_points)
        ]
    },
    fallbacks=[],
    map_to_parent={END: VIEW},
)