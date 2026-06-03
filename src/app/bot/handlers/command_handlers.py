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
    activate_user,
    is_first_time_user
)
from src.services.message_service import (
    insert_message,
    delete_message
)
from src.commons.constants import *
from src.llm.llm_client import get_final_response_from_model

logger = logging.getLogger(__name__)


async def start_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not user_exists(user.id):
        insert_user(user.id, user.first_name)

    if not user_allowed(user.id):
        await update.message.reply_text(USER_NOT_ALLOWED)
        return ConversationHandler.END
    
    if is_first_time_user(user.id):
        message_id = insert_message(user.id, 'user', USER_INITIAL_GREETING)
    else:
        activate_user(user.id)
        message_id = insert_message(user.id, 'user', USER_COMEBACK_GREETING)
    
    try:
        response = get_final_response_from_model(user, 1)
        insert_message(user.id, 'assistant', response)
        await update.message.reply_text(response)
        return CHAT
    except Exception as e:
        delete_message(message_id)
        logger.warning(e)
        await update.message.reply_text(AI_SERVER_ERROR)

async def restart_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(RESTART_MESSAGE.format(user.first_name))
    return CHAT