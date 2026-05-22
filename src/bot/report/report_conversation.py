from telegram.ext import (
    ConversationHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler
)

report.report_callbacks import (
    report_callbacks,
    select_task_start,
    select_task_due,
    task_report,
    select_resource_balance_end
)

commons.constants import (
    START, DUE, SUMMARY, UNTIL, END, VIEW
)

report_conversation = ConversationHandler(
    entry_points=[CallbackQueryHandler(report_callbacks)],
    states={
        START: [
            CallbackQueryHandler(select_task_start),
            MessageHandler(filters.TEXT & ~filters.COMMAND, select_task_start)
        ],
        DUE: [
            CallbackQueryHandler(select_task_due),
            MessageHandler(filters.TEXT & ~filters.COMMAND, select_task_due)
        ],
        SUMMARY:[
            CallbackQueryHandler(task_report),
            MessageHandler(filters.TEXT & ~filters.COMMAND, task_report)
        ],
        UNTIL: [
            CallbackQueryHandler(select_resource_balance_end),
            MessageHandler(filters.TEXT & ~filters.COMMAND, select_resource_balance_end)
        ]
    },
    fallbacks = [],
    map_to_parent = {END: VIEW},
)