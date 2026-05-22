from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import calendar

def freq_selection_message():
    text = 'Use 🔂 to apply only on this task,'
    text += 'Use 🔁 to apply to this and all the future tasks'
    buttons = [
        InlineKeyboardButton('🔙',callback_data='cancel'),
        InlineKeyboardButton('🔂',callback_data='this'),
        InlineKeyboardButton('🔁',callback_data='future')
    ]
    return text, InlineKeyboardMarkup([buttons])

def calendar_keyboard(selected_dt):
    year, month = selected_dt.year, selected_dt.month
    buttons = []
    buttons.append([
        InlineKeyboardButton(calendar.month_name[month]+" "+str(year),callback_data='ignore')
    ])
    buttons.append([
        InlineKeyboardButton(day,callback_data='ignore')
        for day in ["Mo","Tu","We","Th","Fr","Sa","Su"]
    ])
    my_calendar = calendar.monthcalendar(year, month)
    for week in my_calendar:
        row=[]
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(" ",callback_data='ignore'))
            else:
                if selected_dt.day == day:
                    row.append(
                        InlineKeyboardButton('🟠', callback_data=f"{month}/{day}/{str(year)[-2:]}")
                    )
                else:
                    row.append(
                        InlineKeyboardButton(str(day), callback_data=f"{month}/{day}/{str(year)[-2:]}")
                    )
        buttons.append(row)
    buttons.append(
        [
            InlineKeyboardButton('<', callback_data='previous'),
            InlineKeyboardButton('✖️', callback_data='skip'),
            InlineKeyboardButton('⏰', callback_data='time'),
            InlineKeyboardButton('now', callback_data='now'),
            InlineKeyboardButton('✔️', callback_data='confirm'),
            InlineKeyboardButton('>', callback_data='next'),
        ]
    )
    return InlineKeyboardMarkup(buttons)

def task_edit_keyboard():
    buttons = [
        [
            InlineKeyboardButton('🏷️', callback_data='sum'),
            InlineKeyboardButton('📋', callback_data='des'),
            InlineKeyboardButton('📆', callback_data='time'),
            InlineKeyboardButton('🔄', callback_data='freq'),
        ],
        [
            InlineKeyboardButton('🔙', callback_data='back'),
            InlineKeyboardButton('🗑️', callback_data='delete'),
            InlineKeyboardButton('🟠🔵', callback_data='copy'),
            InlineKeyboardButton('🗃️', callback_data='archive'),
        ]
    ]
    return InlineKeyboardMarkup(buttons)

