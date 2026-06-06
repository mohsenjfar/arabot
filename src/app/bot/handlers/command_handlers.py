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
from ..shared.constants import *
from src.llm.llm_client import get_help_response_from_model

logger = logging.getLogger(__name__)


async def start_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not user_exists(user.id):
        insert_user(user.id, user.first_name)
        await update.message.reply_text(USER_INITIAL_GREETING.format(user.first_name))
        return ACTIVITY

    if not user_allowed(user.id):
        await update.message.reply_text(USER_NOT_ALLOWED)
        return ConversationHandler.END
    
    activate_user(user.id)
    await update.message.reply_text(USER_COMEBACK_GREETING.format(user.first_name))
    return ACTIVITY

async def restart_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(RESTART_MESSAGE.format(user.first_name))
    return ACTIVITY

async def help_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = await update.message.reply_text(PROCESSING)
    try:
        await msg.edit_text(get_help_response_from_model(user))
    except Exception as e:
        await msg.edit_text(AI_SERVER_ERROR)
        logger.warning(e)
        raise

async def stop_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(STOP_BOT.format(user.first_name))
    return ConversationHandler.END

async def report_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(STOP_BOT.format(user.first_name))
    return ConversationHandler.END