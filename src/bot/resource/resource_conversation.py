from telegram.ext import (
    ConversationHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler
)

resource.resource_callbacks import (
    resource_entry_points_callbacks,
    insert_new_resource,
    edit_resource_callbacks,
    add_tag_to_resource_callbacks,
    resource_unit,
    minimum_pantry,
    resource_delete_callbacks,
    add_resource_parity_callbacks,
    add_price_callbacks
)

commons.constants import (
    ADD, EDIT, TAG, UNIT, PANTRY, REMOVE, PARITY,
    PRICE, RESTART, END, VIEW
)

resource_conversation = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(resource_entry_points_callbacks),
        MessageHandler(filters.TEXT & ~filters.COMMAND, resource_entry_points_callbacks)
    ],
    states={
        ADD: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, insert_new_resource)
        ],
        EDIT: [
            CallbackQueryHandler(edit_resource_callbacks),
            MessageHandler(filters.TEXT & ~filters.COMMAND, edit_resource_callbacks)
        ],
        TAG: [
            CallbackQueryHandler(add_tag_to_resource_callbacks), 
            MessageHandler(filters.TEXT & ~filters.COMMAND, add_tag_to_resource_callbacks)
        ],
        UNIT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, resource_unit)
        ],
        PANTRY: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, minimum_pantry)
        ],
        REMOVE: [
            CallbackQueryHandler(resource_delete_callbacks)
        ],
        PARITY: [
            CallbackQueryHandler(add_resource_parity_callbacks),
            MessageHandler(filters.TEXT & ~filters.COMMAND, add_resource_parity_callbacks)
        ],
        PRICE: [
            CallbackQueryHandler(add_price_callbacks),
            MessageHandler(filters.TEXT & ~filters.COMMAND, add_price_callbacks)
        ],
        RESTART: [
            CallbackQueryHandler(resource_entry_points_callbacks),
            MessageHandler(filters.TEXT & ~filters.COMMAND, resource_entry_points_callbacks)
        ]
    },
    fallbacks = [],
    map_to_parent = {END: VIEW},
)