from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import calendar

def task_view_keyboard(task):
    inline = f"task_id:{task.id}:"
    buttons = [
        InlineKeyboardButton('✔️', callback_data='complete_task'),
        InlineKeyboardButton('✖️', callback_data='skip_task'),
        InlineKeyboardButton('🔚', callback_data='clear_task'),
        InlineKeyboardButton('✏️', callback_data='edit_task'),
        InlineKeyboardButton('⛽', callback_data='add_resource', 
                             switch_inline_query_current_chat=inline)
    ]
    if task.completed: 
        buttons = [
            InlineKeyboardButton('✅',callback_data='completed')
        ]
    if task.skipped: 
        buttons = [
            InlineKeyboardButton('⛔',callback_data='skipped')
        ]
    return InlineKeyboardMarkup([buttons])

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

def cancel_or_confirm_keyboard():
    buttons = [
        InlineKeyboardButton('Cancel',callback_data='cancel'),
        InlineKeyboardButton('Confirm',callback_data='confirm')
    ]
    return InlineKeyboardMarkup([buttons])

def skip_keyboard():
    buttons = [
        InlineKeyboardButton('Skip',callback_data='skip')
    ]
    return InlineKeyboardMarkup([buttons])