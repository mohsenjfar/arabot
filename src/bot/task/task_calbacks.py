from datetime import date, datetime, timedelta
import re
import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from database.models.models_shim import Parent, Task, ResourceLog
from django.utils import timezone
task.task_keyboards import (
    task_edit_keyboard,
    calendar_keyboard,
    freq_selection_message
)
commons.commons_callbacks import (
    calendar_callback,
    time_callback,
    freq_to_date,
    bulk_insert,
    task_view_message
)

commons.constants import (
    VIEW, DELETE_TASK, DESCRIPTION, FREQUENCY,
    START, SUMMARY, END
)

async def complete_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    message_id = query.message.id
    task = Task.objects.get(message_id=message_id)
    logs = task.logs.filter(completed=False).filter(skipped=False)
    logs_to_update = []
    unavailable_logs = []
    for log in logs:
        available = log.resource.total_available()
        available += log.quantity
        if available < 0: unavailable_logs.append(log.id)
        else: logs_to_update.append(log.id)
    ResourceLog.objects.filter(id__in=logs_to_update).update(
        completed=True,
        modified=timezone.now()
    )
    if unavailable_logs:
        return VIEW
    task.completed = True
    task.save()
    await query.message.delete()
    return VIEW

async def skip_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    message_id = query.message.id
    task = Task.objects.get(message_id=message_id)
    task.logs.update(skipped=True)
    task.skipped = True
    task.save()
    await query.message.delete()
    return VIEW


async def task_undone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    message = query.message
    task = Task.objects.get(message_id=message.id)
    if query.data == 'completed':
        task.completed = False
    if query.data == 'skipped':
        task.skipped = False
    task.save()
    text, reply_markup = task_view_message(task)
    await message.edit_text(text=text, reply_markup=reply_markup)
    return VIEW

async def clear_task(update, context):
    query = update.callback_query
    await query.answer()
    message_id = query.message.id
    await query.message.delete()
    task = Task.objects.get(message_id=message_id)
    task.message_id = None
    task.save()
    del context.chat_data[message_id]
    return

async def create_task_from_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message_text = update.message.text
    chat_id = update.message.chat_id
    url = re.search("(?P<url>https?://[^\s]+)", message_text)
    if url:
        url = url.group("url")
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        message_text = soup.title.string
    parent = Parent.objects.create(
        project_id=abs(chat_id),
        title=message_text
    )
    Task.objects.create(
        parent=parent,
        summary=message_text,
        description=url,
        start=timezone.now()
    )
    await update.message.delete()
    return VIEW

async def edit_task(update, context):
    query = update.callback_query
    await query.answer()
    text = "Press 🗑️ to delete the task or 🟠🔵 to copy"
    reply_markup = task_edit_keyboard()
    await query.edit_message_text(text, reply_markup=reply_markup)

async def edit_task_callbacks(update, context):
    query = update.callback_query
    await query.answer()
    values = context.chat_data[query.message.id]
    task = Task.objects.get(id = values.get('task_id'))

    if query.data == 'back':
        text, reply_markup = task_view_message(task)
        await query.edit_message_text(text, reply_markup=reply_markup)
        return END

    elif query.data == 'delete':
        return await delete_task_message(update, context)

    elif query.data == 'sum':
        text = f'`{task.summary}`'
        await query.message.edit_text(text,parse_mode=ParseMode.MARKDOWN_V2)
        return SUMMARY

    elif query.data == 'des':
        text = f'`{task.description}`'
        await query.message.edit_text(text,parse_mode=ParseMode.MARKDOWN_V2)
        return DESCRIPTION

    elif query.data == 'time':
        values['time'] = task.start + timedelta(hours=3.5)
        text = f"Selected time: {values['time'].strftime('%x %X')}"
        reply_markup = calendar_keyboard(values['time'])
        await query.message.edit_text(text, reply_markup=reply_markup,parse_mode=ParseMode.MARKDOWN_V2)
        return START

    elif query.data == 'freq':
        text = 'Please add frequency to your task'
        await query.edit_message_text(text)
        return FREQUENCY

    elif query.data == 'archive':
        task.archived = True
        task.message_id = None
        task.save()
        await query.message.delete()
        return END

    elif query.data == 'copy':
        values = context.chat_data[query.message.id]
        task = Task.objects.get(id = values.get('task_id'))
        logs = [(log.resource, log.quantity) for log in task.logs.all()]
        parent = Parent.objects.create(title=task.parent.title)
        task = Task.objects.create(
            parent=parent, 
            summary=task.summary,
            description=task.description,
            start=timezone.now()
        )
        new_logs = [
            ResourceLog(
                task = task,
                resource = log[0],
                quantity = log[1] * log[0].get_conversion_factor() if log[1] > 0 else log[1]
            ) for log in logs
        ]
        ResourceLog.objects.bulk_create(new_logs)
        return

async def edit_summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()
        values = context.chat_data[query.message.id]
        task = Task.objects.get(id = values.get('task_id'))
        if query.data == 'future':
            task.parent.tasks.filter(start__gte=task.start).update(summary=values['summary'])
        text, reply_markup = task_view_message(task)
        await query.edit_message_text(text, reply_markup=reply_markup)
        return END
    message = update.message.reply_to_message
    values = context.chat_data[message.id]
    task = Task.objects.get(id = values.get('task_id'))
    summary = update.message.text
    task.summary = summary; task.save()
    await update.message.delete()
    if task.parent.freq:
        values['summary'] = summary
        text, reply_markup = freq_selection_message()
        await message.edit_text(text, reply_markup=reply_markup)
        return
    text, reply_markup = task_view_message(task)
    await message.edit_text(text, reply_markup=reply_markup)
    return END

async def edit_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()
        values = context.chat_data[query.message.id]
        task = Task.objects.get(id = values.get('task_id'))
        if query.data == 'future':
            task.parent.tasks.filter(start__gte=task.start).update(description=values['description'])
        text, reply_markup = task_view_message(task)
        await query.edit_message_text(text, reply_markup=reply_markup)
        return END
    message = update.message.reply_to_message
    values = context.chat_data[message.id]
    task = Task.objects.get(id = values.get('task_id'))
    description = update.message.text
    task.description = description; task.save()
    await update.message.delete()
    if task.parent.freq:
        values['description'] = description
        text, reply_markup = freq_selection_message()
        await message.edit_text(text, reply_markup=reply_markup)
        return
    text, reply_markup = task_view_message(task)
    await message.edit_text(text, reply_markup=reply_markup)
    return END

async def edit_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()
        values = context.chat_data[query.message.id]
        task = Task.objects.get(id = values.get('task_id'))
        if query.data in ['confirm', 'skip']:
            if timezone.is_naive(values['time']):
                values['time'] = timezone.make_aware(values['time'])
            if task.parent.freq:
                text, reply_markup = freq_selection_message()
                await query.edit_message_text(text, reply_markup=reply_markup)
                return
            else:
                task.start = values['time'] - timedelta(hours=3.5)
                task.save()
                text, reply_markup = task_view_message(task)
                await query.edit_message_text(text, reply_markup=reply_markup)
                return END
        elif query.data == 'now':
            del context.chat_data[task.message_id]
            task.start = timezone.now()
            task.message_id = None
            task.save()
            await query.message.delete()
            return END
        elif query.data == 'this':
            task.start = values['time'] - timedelta(hours=3.5)
            task.save()
            text, reply_markup = task_view_message(task)
            await query.edit_message_text(text, reply_markup=reply_markup)
            return END
        elif query.data == 'future':
            parent = task.parent
            values['freq'] = parent.freq
            values['start'] = values['time'] - timedelta(hours=3.5)
            values['summary'] = task.summary
            values['description'] = task.description
            logs = [(log.resource, log.quantity) for log in task.logs.all()]
            parent.tasks.filter(completed=False).delete()
            new_tasks = Task.objects.bulk_create(bulk_insert(parent, values))
            new_logs = [
                ResourceLog(
                    task=new_task, 
                    resource=log[0], 
                    quantity=log[1] * log[0].get_conversion_factor() if log[1] > 0 else log[1]
                ) for log in logs for new_task in new_tasks
            ]
            ResourceLog.objects.bulk_create(new_logs)
            del values
            await query.message.delete()
            return END
        elif query.data == 'cancel':
            text, reply_markup = task_view_message(task)
            await query.edit_message_text(text, reply_markup=reply_markup)
            return END
        else:
            await calendar_callback(update, context)
            return
    else:
        await time_callback(update, context)
        return

async def edit_freq(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()
        message = query.message
        message_id = message.id
        params = context.chat_data[message_id]
        if query.data == 'confirm':
            values = freq_to_date(params)
            task = Task.objects.get(message_id=message_id)
            parent = task.parent
            parent.freq = f"BYDAY={values[0]};UNTIL={params['time'].strftime('%x %X')}"
            parent.save()
            logs = [(log.resource, log.quantity) for log in task.logs.all()]
            parent.tasks.filter(completed=False).delete()
            new_tasks = Task.objects.bulk_create(bulk_insert(parent, params))
            new_logs = [
                ResourceLog(
                    task=new_task, 
                    resource=log[0], 
                    quantity=log[1] * log[0].get_conversion_factor() if log[1] > 0 else log[1]
                ) for log in logs for new_task in new_tasks
            ]
            ResourceLog.objects.bulk_create(new_logs)
            del params
            await query.message.delete()
            return END
        else:
            await calendar_callback(update, context)
            return
    else:
        message = update.message.reply_to_message
        message_id = message.id
        params = context.chat_data[message_id]
        task = Task.objects.get(message_id=message_id)
        params['time'] = datetime(date.today().year + 1, 3, 21)
        params['freq'] = f"BYDAY={update.message.text};UNTIL={params['time'].strftime('%x %X')}"
        params['start'] = task.start
        params['summary'] = task.summary
        params['description'] = task.description
        await update.message.delete()
        text = f"Selected until: {params['time'].strftime('%x %X')}"
        reply_markup = calendar_keyboard(params['time'])
        await message.edit_text(text, reply_markup=reply_markup)
        return

async def delete_task_message(update, context):
    query = update.callback_query
    await query.answer()
    message_id = query.message.id
    task = Task.objects.get(message_id=message_id)
    if task.parent.freq or task.parent.title in ["timer", "aladhan"]:
        text, reply_markup = freq_selection_message()
        await query.edit_message_text(text, reply_markup=reply_markup)
        return DELETE_TASK
    task.delete()
    del context.chat_data[message_id]
    await query.message.delete()
    return END

async def delete_task_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    message_id = query.message.id
    task = Task.objects.get(message_id=message_id)
    if query.data == 'this':
        task.delete()
    elif query.data == 'future':
        task.parent.tasks.filter(completed=False).delete()
    else:
        text, reply_markup = task_view_message(task)
        await query.edit_message_text(text, reply_markup=reply_markup)
        return END
    del context.chat_data[message_id]
    await query.message.delete()
    return END

async def insert_task_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    values = context.chat_data[query.message.id]
    task = Task.objects.get(id = values.get('task_id'))
    text, reply_markup = task_view_message(task)
    await query.edit_message_text(text, reply_markup=reply_markup)
    return END