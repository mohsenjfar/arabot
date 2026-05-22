from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def report_keyboard():
    buttons = [
        InlineKeyboardButton('🔙',callback_data='cancel'),
        InlineKeyboardButton('✅',callback_data='task'),
        InlineKeyboardButton('🛒',callback_data='purchase')
    ]
    return InlineKeyboardMarkup([buttons])