import logging
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
from src.services.task_service import create_activity, notification
from src.services.report_service import get_activity_details_by_id
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

    # Which phase we start in (work vs break) is decided by create_activity
    # itself from the wall-clock grid. From there the cycle is driven by the
    # task's own rrule: completing/skipping it toggles rrule+summary to the
    # other phase and schedules it via the normal recurrence mechanism, so
    # it only becomes due after its interval elapses.
    task = create_activity({"user_id": user.id, "activity_type": "timer"})

    task_details = get_activity_details_by_id(task["id"])
    text, reply_markup = create_task_message(task_details)
    await update.message.reply_text(text=text, reply_markup=reply_markup)
    notification(task["id"])

    await update.message.delete()
    return ACTIVITY
