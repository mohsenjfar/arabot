from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def settings_keyboard():
    inline = "archive:"
    buttons = (
        InlineKeyboardButton('🔙',callback_data='back'),
        InlineKeyboardButton('🗄️',switch_inline_query_current_chat=inline),
        InlineKeyboardButton('🌍',callback_data='location'),
        InlineKeyboardButton('❓',callback_data='help')
    )
    return InlineKeyboardMarkup([buttons])
