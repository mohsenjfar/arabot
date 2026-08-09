import logging
from telegram import Update
from telegram.ext import (
    ContextTypes
)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.error import BadRequest

from src.services.message_service import insert_message
from src.services.task_service import (
    delete_activity,
    clear_activity,
    skip_activity,
    complete_activity,
    is_timer_task,
)
from src.services.report_service import get_activity_details_by_id
from ..shared.commons import create_task_message
from ..shared.constants import *

logger = logging.getLogger(__name__)

async def _show_synced_timer_card(query, task_id):
    """Timer phases resync to the wall-clock grid on every ✔️/✖️ (see
    _sync_timer_phase), so a late confirm can land on a different phase than
    what was shown before. Surface that resynced phase right away instead of
    just deleting the message, otherwise the user has no way to know which
    session they're actually in until the next automatic reminder fires.
    `next_date` is overwritten with `dtstart` for display purposes only: the
    real `next_date` in the DB stays the future grid boundary that schedules
    the next automatic reminder."""
    task_details = get_activity_details_by_id(task_id)
    task_details["next_date"] = task_details["dtstart"]
    text, reply_markup = create_task_message(task_details)
    try:
        await query.message.edit_text(text=text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    except BadRequest as e:
        # A confirm/skip well before the phase actually ends resyncs to the
        # *same* session (nothing to show differently yet), so the rendered
        # card is byte-identical to what's already on screen and Telegram
        # rejects the no-op edit. The underlying row was still advanced
        # correctly (next_date/notified), so this is safe to ignore.
        if "Message is not modified" not in str(e):
            raise

async def complete_activity_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    task_id = query.data.split(':')[1]
    was_timer = is_timer_task(task_id)
    result = complete_activity(task_id)
    await query.answer(result)
    if was_timer:
        await _show_synced_timer_card(query, task_id)
    else:
        await query.message.delete()

async def skip_activity_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    task_id = query.data.split(':')[1]
    was_timer = is_timer_task(task_id)
    result = skip_activity(task_id)
    await query.answer(result)
    if was_timer:
        await _show_synced_timer_card(query, task_id)
    else:
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