from telegram import Update
from telegram.ext import ContextTypes
from database.models.models_shim import Project, Task
from django.utils import timezone
view.view_keyboards import (
    menu_keyboard
)
utils.timer import timer_start
utils.jobs import setup_jobs
task.task_calbacks import (
    edit_task,
    complete_task,
    skip_task,
    clear_task,
    task_undone
)
setting.setting_callbacks import settings
report.report_callbacks import report_menu
tags.tag_callbacks import tags_menu
resource.resource_callbacks import resources_menu
resource.task.task_resource_callbacks import task_resource_menu
commons.constants import (
    VIEW, TAG, EDIT_TASK, END, INSERT_RESOURCE
)

async def menu_message(update, context):
    chat_id = update.message.chat.id
    await update.message.delete()
    text = 'Please select a button'
    reply_markup = menu_keyboard()
    await context.bot.send_message(chat_id, text=text, reply_markup=reply_markup)
    return VIEW

async def remove_menu(update, context):
    query = update.callback_query
    await query.message.delete()
    return VIEW

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not context.chat_data.get('start_over'):
        chat_id = update.message.chat.id
        title = update.message.chat.title
        await update.message.delete()
        context.chat_data['start_over'] = True
        project, _ = Project.objects.get_or_create(id = abs(chat_id))
        project.title = title
        project.save()
        Task.objects.filter(
            parent__project = project,
            start__lte = timezone.now(),
        ).filter(completed=False,skipped=False).update(message_id=None)
        await setup_jobs(context, chat_id)
        return VIEW
    return await menu_message(update, context)

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    for job in context.job_queue.jobs():
        job.schedule_removal()
    context.chat_data['start_over'] = False
    await query.message.delete()
    text = "Task bot successfully stopped"
    await context.bot.send_message(chat_id, text=text)
    return END

async def view_query_handlers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'timer':
        await timer_start(update, context)
        return VIEW

    elif query.data == 'edit_task':
        await edit_task(update, context)
        return EDIT_TASK

    elif query.data == 'tag':
        await tags_menu(update, context)
        return TAG

    elif query.data == 'resource':
        await resources_menu(query.message, context)
        return INSERT_RESOURCE

    elif query.data == 'report':
        return await report_menu(update, context)

    elif query.data == 'stop':
        return await stop(update, context)

    elif query.data == 'complete_task':
        return await complete_task(update, context)

    elif query.data == 'skip_task':
        return await skip_task(update, context)

    elif query.data == 'clear_task':
        return await clear_task(update, context) 

    elif query.data == 'add_resource':
        return await task_resource_menu(update, context)

    elif query.data in ['completed', 'skipped']:
        return await task_undone(update, context)

    elif query.data == 'remove':
        return await remove_menu(update, context)

    elif query.data == 'settings':
        return await settings(update, context)