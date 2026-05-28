import logging
from telegram import Update
from telegram.ext import (
    ContextTypes, 
    ConversationHandler
)
from services.user_service import (
    user_exists, 
    user_allowed,
    insert_user,
    activate_user,
    is_first_time_user
)
from services.message_service import insert_message
from config.constants import *

logger = logging.getLogger(__name__)


async def start_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not user_exists(user.id):
        insert_user(user.id, user.first_name)

    if not user_allowed(user.id):
        await update.message.reply_text(USER_NOT_ALLOWED)
        return ConversationHandler.END
    
    if is_first_time_user(user.id):
        insert_message(user.id, 'user', USER_INITIAL_GREETING)
        insert_message(user.id, 'assistant', ASSISTANT_INITIAL_GREETING.format(user.first_name))
        await update.message.reply_text(ASSISTANT_INITIAL_GREETING.format(user.first_name))
        return CHAT

    activate_user(user.id)
    insert_message(user.id, 'user', USER_COMEBACK_GREETING)
    insert_message(user.id, 'assistant', ASSISTANT_COMEBACK_GREETING.format(user.first_name))
    await update.message.reply_text(ASSISTANT_COMEBACK_GREETING.format(user.first_name))
    return CHAT

async def restart_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(RESTART_MESSAGE.format(user.first_name))
    return CHAT