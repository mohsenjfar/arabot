import logging
from datetime import timedelta
from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler
)
from src.services.user_service import (
    user_exists,
    user_allowed,
    insert_user,
    activate_user
)
from src.services.task_service import create_activity, link_related_tasks, complete_activity
from src.services.report_service import get_activity_details_by_id
from src.core import timezone
from ..shared.commons import create_task_message
from ..shared.constants import *
from src.llm.llm_client import get_help_response_from_model

logger = logging.getLogger(__name__)


async def start_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not user_exists(user.id):
        insert_user(user.id, user.first_name)
        await update.message.reply_text(USER_INITIAL_GREETING.format(user.first_name))
        await update.message.delete()
        return ACTIVITY

    if not user_allowed(user.id):
        await update.message.reply_text(USER_NOT_ALLOWED)
        await update.message.delete()
        return ConversationHandler.END

    activate_user(user.id)
    await update.message.reply_text(USER_COMEBACK_GREETING.format(user.first_name))
    await update.message.delete()
    return ACTIVITY

async def restart_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(RESTART_MESSAGE.format(user.first_name))
    await update.message.delete()
    return ACTIVITY

async def help_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = await update.message.reply_text(PROCESSING)
    await update.message.delete()
    try:
        await msg.edit_text(get_help_response_from_model(user))
    except Exception as e:
        await msg.edit_text(AI_SERVER_ERROR)
        logger.warning(e)
        raise

async def stop_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(STOP_BOT.format(user.first_name))
    await update.message.delete()
    return ConversationHandler.END

async def report_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    prompt_msg = await update.message.reply_text(REPORT_PROMPT.format(user.first_name))
    context.user_data["prompt_message_id"] = prompt_msg.message_id
    await update.message.delete()
    return LLM

async def timer_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    now = timezone.now().replace(microsecond=0, tzinfo=None)

    # Align the 25-min work / 5-min break cycle to the wall-clock half-hour
    # grid (:00/:30 = work starts, :25/:55 = break starts), rather than to
    # whatever minute /timer happens to be run at.
    block_start = now.replace(minute=0 if now.minute < 30 else 30, second=0)
    minute_in_block = (now - block_start).total_seconds() / 60

    if minute_in_block < 25:
        work_dtstart = block_start
        break_dtstart = block_start + timedelta(minutes=25)
        current_task_summary = TIMER_RESUME_MESSAGE
    else:
        break_dtstart = block_start + timedelta(minutes=25)
        work_dtstart = block_start + timedelta(minutes=30)
        current_task_summary = TIMER_BREAK_MESSAGE

    break_task = create_activity({
        "user_id": user.id,
        "summary": TIMER_BREAK_MESSAGE,
        "dtstart": break_dtstart,
        "is_recurrent": True,
        "rrule": TIMER_RRULE,
        "rrule_human": TIMER_RRULE_HUMAN,
    })
    work_task = create_activity({
        "user_id": user.id,
        "summary": TIMER_RESUME_MESSAGE,
        "dtstart": work_dtstart,
        "is_recurrent": True,
        "rrule": TIMER_RRULE,
        "rrule_human": TIMER_RRULE_HUMAN,
    })
    link_related_tasks(break_task["id"], work_task["id"])

    current_task = break_task if current_task_summary == TIMER_BREAK_MESSAGE else work_task
    task_details = get_activity_details_by_id(current_task["id"])
    text, reply_markup = create_task_message(task_details)
    await update.message.reply_text(text=text, reply_markup=reply_markup)
    complete_activity(current_task["id"])

    await update.message.delete()
    return ACTIVITY
