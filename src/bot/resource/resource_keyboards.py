from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def resources_keyboard(message_id):
    resources_by_title = f"resources_by_title:{message_id}:"
    resources_by_tag = f"resources_by_tag:{message_id}:"
    buttons = [
        InlineKeyboardButton('🔙',callback_data='back'),
        InlineKeyboardButton('🔍',switch_inline_query_current_chat=resources_by_title),
        InlineKeyboardButton('🗂️',switch_inline_query_current_chat=resources_by_tag),
        InlineKeyboardButton('➕',callback_data='add'),
    ]
    return InlineKeyboardMarkup([buttons])

def resource_keyboard():
    buttons = [
        [
            InlineKeyboardButton('🗂️',callback_data='tag'),
            InlineKeyboardButton('📏',callback_data='unit'),
            InlineKeyboardButton('🔄',callback_data='parity')
        ],
        [
            InlineKeyboardButton('🔙',callback_data='back'),
            InlineKeyboardButton('🗑️',callback_data='remove'),
            InlineKeyboardButton('🫙',callback_data='pantry'),
            InlineKeyboardButton('🧾',callback_data='price')
        ]
    ]

    return InlineKeyboardMarkup(buttons)

def add_tag_to_resource_keyboard(message_id):
    inline = f"tags:{message_id}:"
    buttons = [
        InlineKeyboardButton('🔙', callback_data='back'),
        InlineKeyboardButton('🔍',switch_inline_query_current_chat=inline)
    ]
    return InlineKeyboardMarkup([buttons])

def add_price_to_resource_message(resource):
    values = resource.prices.order_by('date')[:5]
    values = [
        f"{v.date.strftime('%x')}: {v.price:,} تومان"
        for v in values
    ]
    text = '\n'.join(values) or "No price"
    buttons = [
        InlineKeyboardButton('🔙',callback_data='cancel'),
        InlineKeyboardButton('➕',callback_data='price'),
        InlineKeyboardButton('🗑️',callback_data='delete')
    ]
    return text, InlineKeyboardMarkup([buttons])




