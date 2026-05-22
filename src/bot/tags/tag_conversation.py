from telegram.ext import (
    ConversationHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler
)

tags.tag_callbacks import (
    tag_entry_points_callbacks,
    insert_tag_callback,
    edit_tag_query_callbacks,
    edit_tag_message_callbacks
)

commons.constants import (
    VIEW, ADD, EDIT, END, RESTART
)

tag_conversation = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(tag_entry_points_callbacks),
        MessageHandler(filters.TEXT & ~filters.COMMAND, tag_entry_points_callbacks)
    ],
    states={
        ADD: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, insert_tag_callback)
        ],
        EDIT: [
            CallbackQueryHandler(edit_tag_query_callbacks),
            MessageHandler(filters.TEXT & ~filters.COMMAND, edit_tag_message_callbacks)
        ],
        RESTART: [
            CallbackQueryHandler(tag_entry_points_callbacks),
            MessageHandler(filters.TEXT & ~filters.COMMAND, tag_entry_points_callbacks)
        ]
    },
    fallbacks = [],
    map_to_parent = {END: VIEW},
)