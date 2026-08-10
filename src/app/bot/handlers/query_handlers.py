import logging
from telegram import Update
from telegram.ext import (
    ContextTypes
)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode

from src.services.message_service import insert_message
from src.services.task_service import (
    delete_activity,
    clear_activity,
    skip_activity,
    complete_activity,
)
from src.services.report_service import get_activity_details_by_id
from ..shared.commons import create_task_message
from ..shared.constants import *

logger = logging.getLogger(__name__)

async def complete_activity_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    task_id = query.data.split(':')[1]
    result = complete_activity(task_id)
    await query.answer(result)
    await query.message.delete()

async def skip_activity_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    task_id = query.data.split(':')[1]
    result = skip_activity(task_id)
    await query.answer(result)
    await query.message.delete()

async def delete_activity_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    task_id = query.data.split(':')[1]
    text = "آیا از حذف این فعالیت اطمینان داری؟"
    buttons = [[
        InlineKeyboardButton('بله',callback_data=f'confirm_delete:{task_id}'),
        InlineKeyboardButton('منصرف شدم',callback_data=f'cancel:{task_id}')
    ]]
    reply_markup = InlineKeyboardMarkup(buttons)
    await query.message.edit_text(text=text, reply_markup=reply_markup)

async def confirm_delete_activity_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    task_id = query.data.split(':')[1]
    result = delete_activity(task_id)
    await query.answer(result)
    await query.message.delete()

async def clear_activity_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    task_id = query.data.split(':')[1]
    result = clear_activity(task_id)
    await query.answer(result)
    await query.message.delete()

async def edit_activity_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = update.effective_user
    task_id = query.data.split(':')[1]
    context.user_data["task_id"] = task_id
    task = get_activity_details_by_id(task_id)
    insert_message(user.id, 'user', EDIT_ACTIVITY_PROMPT.format(task))
    insert_message(user.id, 'assistant', EDIT_ACTIVITY_RESPONSE.format(user.first_name))
    await query.message.edit_text(EDIT_ACTIVITY_RESPONSE.format(user.first_name), reply_markup=None)
    context.user_data["prompt_message_id"] = query.message.message_id
    return LLM

async def cancel_query_handler(update, context):
    query = update.callback_query
    task_id = query.data.split(':')[1]
    task_details = get_activity_details_by_id(task_id)
    text, reply_markup = create_task_message(task_details)
    await query.message.edit_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)