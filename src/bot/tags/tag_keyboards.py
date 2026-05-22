from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def insert_new_tag_keyboard(message_id):
    inline = f"tags:{message_id}:"
    buttons = [
        InlineKeyboardButton('🔙',callback_data='back'),
        InlineKeyboardButton('🔍',switch_inline_query_current_chat=inline),
        InlineKeyboardButton('➕',callback_data='add'),
    ]
    return InlineKeyboardMarkup([buttons])

def edit_tag_keyboard():
    buttons = [
        InlineKeyboardButton('🔙',callback_data='cancel'),
        InlineKeyboardButton('🗑️',callback_data='delete')
    ]
    return InlineKeyboardMarkup([buttons])

def cancel_or_confirm_keyboard():
    buttons = [
        InlineKeyboardButton('Cancel',callback_data='cancel'),
        InlineKeyboardButton('Confirm',callback_data='confirm')
    ]
    return InlineKeyboardMarkup([buttons])
