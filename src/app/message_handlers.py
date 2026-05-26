import logging
from telegram import Update
from telegram.ext import (
    ContextTypes, 
    ConversationHandler
)
from services.user_service import keep_in_mind
from services.message_service import (
    insert_message,
    delete_message
)
from commons.constants import *
import json
from llm.llm_client import get_response_from_model

logger = logging.getLogger(__name__)


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not update.message or not update.message.text:
        return

    user_text = update.message.text.strip()
    if not user_text:
        return

    msg = await update.message.reply_text(PROCESSING)

    message_id = insert_message(user.id, 'user', user_text)

    try:
        response = get_response_from_model(user=user, limit=10, attempt='first', request='primary')

    except Exception as e:
        logger.error(f"Main model failed: {e}")
        
        await msg.edit_text(MAIN_MODEL_NOT_RESPOND)
        
        try:
            response = get_response_from_model(user=user, limit=10, attempt='second', request='primary')
        except Exception as sub_e:
            logger.error(f"Sub model also failed: {sub_e}")
            await msg.edit_text(SUB_MODEL_NOT_RESPOND)
            delete_message(message_id)
            return

    function_calls = [
        item for item in response.output
        if getattr(item, "type", None) == "function_call"
    ]

    if not function_calls:
        final_text = getattr(response, "output_text", None)
        if final_text:
            insert_message(user.id, 'assistant', final_text)
            await msg.edit_text(final_text)
        else:
            delete_message(message_id)
            await msg.edit_text(AI_SERVER_ERROR)
        return

    for item in function_calls:
        function_name = item.name

        args = json.loads(item.arguments)
        args['user_id'] = user.id

        logger.info(args)

        if function_name == "keep_in_mind":
            result = keep_in_mind(args)
            await msg.edit_text(result)
            insert_message(user.id, 'assistant', result)
            
        if function_name == "end_conversation":
            text = STOP_BOT.format(user.first_name)
            await msg.edit_text(text)
            insert_message(user.id, 'assistant', text)
            return ConversationHandler.END
