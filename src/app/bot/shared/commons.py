import logging

from telegram import Update
from telegram.ext import ContextTypes
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from src.services.task_service import notification, complete_activity
from src.services.report_service import (
    get_activity_details_by_id,
    get_due_tasks
)

logger = logging.getLogger(__name__)


def create_task_message(task_details):
    summary = task_details.get('summary')
    description = task_details.get('description')
    next_date = task_details.get('next_date')
    rrule_human = task_details.get('rrule_human')
    lines = (
        f"🔖 *{summary}*",
        f"\n📝 {description}" if description else "",
        f"\n📆 {next_date}" if next_date else "",
        f"🔄 {rrule_human}" if rrule_human else ""
    )
    task_id = task_details.get('id')
    buttons = [
        [
            InlineKeyboardButton('✔️',callback_data=f'complete:{task_id}'),
            InlineKeyboardButton('🗑️',callback_data=f'delete:{task_id}'),
            InlineKeyboardButton('✏️',callback_data=f'edit:{task_id}'),
            InlineKeyboardButton('🧹',callback_data=f'clear:{task_id}'),
        ]
    ]
    if task_details.get('is_recurrent'):
        buttons[0].insert(2, InlineKeyboardButton('✖️',callback_data=f'skip:{task_id}'),)
    return '\n'.join(lines), InlineKeyboardMarkup(buttons)

async def task_details_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    task_id = context.user_data.get("task_id")
    task = get_activity_details_by_id(task_id)
    text, reply_markup = create_task_message(task)
    notification(task_id)
    await update.message.reply_text(text=text, reply_markup=reply_markup)

async def check_and_send_tasks(context):
    try:
        tasks = get_due_tasks()
        
        if not tasks:
            return

        for task in tasks:
            try:
                task_details = get_activity_details_by_id(task.id)
                text, reply_markup  = create_task_message(task_details)
                await context.bot.send_message(task.user_id, text=text, reply_markup=reply_markup)
                if task_details.get('related_task_id'):
                    # paired recurring activities (e.g. the /timer pomodoro
                    # cycle) advance to their next occurrence automatically
                    # instead of waiting for a manual complete tap
                    complete_activity(task.id)
                else:
                    notification(task.id)
            except Exception as e:
                logger.info(f"Error sending message for task {task.id} to chat {task.user_id}: {e}")
    except Exception as e:
        logger.info(f"An error occurred in scheduled_tasks for user {task.user_id}: {e}")