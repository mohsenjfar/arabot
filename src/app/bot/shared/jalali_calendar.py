import jdatetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from src.core.timezone import PERSIAN_MONTH_NAMES, PERSIAN_WEEKDAY_NAMES_SHORT


def _days_in_jmonth(year: int, month: int) -> int:
    if month == 12:
        return 30 if jdatetime.date(year, 1, 1).isleap() else 29
    return jdatetime.j_days_in_month[month - 1]


def calendar_keyboard(selected_date: jdatetime.date) -> InlineKeyboardMarkup:
    """A Jalali month-grid picker, mirroring the legacy bot's Gregorian
    calendar_keyboard but in the calendar the rest of this bot actually uses
    (see src.core.timezone). Day buttons carry the picked date in their
    callback_data; navigation/time/confirm state lives in user_data since a
    single user only ever has one edit flow open at a time."""
    year, month = selected_date.year, selected_date.month

    buttons = [[
        InlineKeyboardButton(f"{PERSIAN_MONTH_NAMES[month - 1]} {year}", callback_data="caldate:ignore")
    ]]
    buttons.append([
        InlineKeyboardButton(name, callback_data="caldate:ignore")
        for name in PERSIAN_WEEKDAY_NAMES_SHORT
    ])

    first_weekday = jdatetime.date(year, month, 1).weekday()
    days_in_month = _days_in_jmonth(year, month)

    week = [None] * first_weekday
    weeks = []
    for day in range(1, days_in_month + 1):
        week.append(day)
        if len(week) == 7:
            weeks.append(week)
            week = []
    if week:
        weeks.append(week + [None] * (7 - len(week)))

    for week in weeks:
        row = []
        for day in week:
            if day is None:
                row.append(InlineKeyboardButton(" ", callback_data="caldate:ignore"))
            else:
                label = f"🟠{day}" if day == selected_date.day else str(day)
                row.append(InlineKeyboardButton(label, callback_data=f"caldate:day:{year}-{month}-{day}"))
        buttons.append(row)

    buttons.append([
        InlineKeyboardButton("<", callback_data="caldate:prev"),
        InlineKeyboardButton("⏰", callback_data="caldate:time"),
        InlineKeyboardButton("امروز", callback_data="caldate:now"),
        InlineKeyboardButton("✔️", callback_data="caldate:confirm"),
        InlineKeyboardButton(">", callback_data="caldate:next"),
    ])
    buttons.append([InlineKeyboardButton("🔙", callback_data="editback")])

    return InlineKeyboardMarkup(buttons)


def shift_month(selected_date: jdatetime.date, delta: int) -> jdatetime.date:
    month = selected_date.month + delta
    year = selected_date.year
    if month < 1:
        month = 12
        year -= 1
    elif month > 12:
        month = 1
        year += 1
    day = min(selected_date.day, _days_in_jmonth(year, month))
    return jdatetime.date(year, month, day)
