from database.models.models_shim import Task
from django.utils import timezone
import re
from datetime import datetime, timedelta, date
commons.common_keyboards import (
    calendar_keyboard,
    task_view_keyboard
)
import calendar
from telegram.constants import ParseMode
from telegram import Update
from telegram.ext import ContextTypes

def freq_to_date(values):
    values = re.findall(r'\d+', values['freq'])
    ttime = f"{values[1]}/{values[2]}/{values[3]} {values[4]}:{values[5]}:{values[6]}"
    until = datetime.strptime(ttime,'%x %X')
    return int(values[0]), timezone.make_aware(until)

def bulk_insert(parent, values):
    freq, until = freq_to_date(values)
    tasks = []
    while values['start'] <= until:
        tasks.append(
            Task(
                parent = parent,
                summary = values.get('summary'),
                start = values.get('start'),
                description = values.get('description')
            )
        )
        values['start'] += timedelta(days=freq)
    return tasks

def month_increment(sourcedate, add=True):
    month = sourcedate.month
    year = sourcedate.year + month // 12
    month = month % 12 + 1 if add else month % 12 - 1
    day = min(sourcedate.day, calendar.monthrange(year,month)[1])
    return date(year, month, day)

async def calendar_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    values = context.chat_data[query.message.id]
    if query.data == 'now':
        values['time'] = timezone.now() + timedelta(hours=3.5)
    elif query.data == 'next':
        dtime = month_increment(values['time'].date())
        values['time'] = timezone.datetime.combine(dtime,values['time'].time())
    elif query.data == 'previous':
        dtime = month_increment(values['time'].date(), add=False)
        values['time'] = timezone.datetime.combine(dtime,values['time'].time())
    elif query.data == 'time':
        text = 'Please enter time in the following format: '
        text += f"`{values['time'].strftime('%X')}`"
        await query.edit_message_text(text,parse_mode=ParseMode.MARKDOWN_V2)
        return
    elif query.data == 'ignore':
        return
    else:
        dtime = timezone.datetime.strptime(query.data, '%x')
        values['time'] = timezone.datetime.combine(dtime,values['time'].time())
    text = F"Selected time: {values['time'].strftime('%x %X')}"
    reply_markup = calendar_keyboard(values['time'])
    await query.edit_message_text(text, reply_markup=reply_markup)
    return

async def time_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message.reply_to_message
    params = context.chat_data[message.message_id]
    ttime = timezone.datetime.strptime(update.message.text, '%X').time()
    params['time'] = timezone.datetime.combine(params['time'].date(),ttime)
    await update.message.delete()
    text = F"Selected time: {params['time'].strftime('%x %X')}"
    reply_markup = calendar_keyboard(params['time'])
    await message.edit_text(text, reply_markup=reply_markup)
    return

def task_view_message(task):
    lines = [f'{task.summary}']
    if task.description: lines.append(f"{task.description}")
    if task.start: lines.append(f"📅 Start: {(task.start + timedelta(hours=3.5)).strftime('%x %X')}")
    if task.parent.freq:
        count = task.parent.tasks.exclude(completed=True).count()
        values = re.findall(r'\d+', task.parent.freq)
        until = f"{values[1]}/{values[2]}/{values[3]} {values[4]}:{values[5]}:{values[6]}"
        if values[0] == '1': text = f"🔁 Every day until {until} for {count} times"
        else: text = f"🔁 Every {values[0]} days until {until} for {count} times"
        lines.append(text)
    return '\n\n'.join(lines), task_view_keyboard(task)