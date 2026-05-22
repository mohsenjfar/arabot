from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def freq_selection_message():
    text = 'Use 🔂 to apply only on this task,'
    text += 'Use 🔁 to apply to this and all the future tasks'
    buttons = [
        InlineKeyboardButton('🔙',callback_data='cancel'),
        InlineKeyboardButton('🔂',callback_data='this'),
        InlineKeyboardButton('🔁',callback_data='future')
    ]
    return text, InlineKeyboardMarkup([buttons])

def view_task_resources_keyboard(message_id, task_id):
    resources_by_title = f"task_resources_by_resource_title:{message_id}:{task_id}:"
    resources_by_tag = f"task_resources_by_resource_tag:{message_id}:{task_id}:"
    reduce = f"reduce:{message_id}:{task_id}:"
    increase = f"increase:{message_id}:{task_id}:"
    buttons = [
        InlineKeyboardButton('🔙', callback_data='back'),
        InlineKeyboardButton('🔍',switch_inline_query_current_chat=resources_by_title),
        InlineKeyboardButton('🗂️',switch_inline_query_current_chat=resources_by_tag),
        InlineKeyboardButton('➖',switch_inline_query_current_chat=reduce),
        InlineKeyboardButton('➕',switch_inline_query_current_chat=increase),
    ]
    return InlineKeyboardMarkup([buttons])

def log_keyboard(message_id, task_id):
    resources_by_title = f"resources_by_title:{message_id}:"
    buttons = [
        [
            InlineKeyboardButton('🗑️',callback_data='remove'),
            InlineKeyboardButton('⛔',callback_data='skip'),
            InlineKeyboardButton('✅',callback_data='used')
        ],
        [
            InlineKeyboardButton('🔙',callback_data='back'),
            InlineKeyboardButton('✏️',callback_data='edit'),
            InlineKeyboardButton('🔄',switch_inline_query_current_chat=resources_by_title)
        ]

    ]
    return InlineKeyboardMarkup(buttons)

