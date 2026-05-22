from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def menu_keyboard():
    resource_inline = "resources_by_title:"
    buttons = [
        [
            InlineKeyboardButton('⏲️ Timer', callback_data='timer'),
            InlineKeyboardButton('🗂️ Tags', callback_data='tag')
        ],
        [
            InlineKeyboardButton('⛽ Resources', callback_data='resource'),
            InlineKeyboardButton('ℹ️ Report', callback_data='report'),
        ],
        [
            InlineKeyboardButton('🛑', callback_data='stop'),
            InlineKeyboardButton('⚙️', callback_data='settings'),
            InlineKeyboardButton('✖️', callback_data='remove')
        ]
    ]

    return InlineKeyboardMarkup(buttons)

