import logging
from telegram import Update
from telegram.ext import ContextTypes

from src.services.message_service import (
    insert_message,
    delete_message
)
from src.services.task_service import (
    create_activity,
    update_activity,
    notification
)
from src.services.report_service import (
    report_activities_by_time,
    report_activities_by_summary,
    get_activity_details_by_summary
)
from ..shared.commons import create_task_message
from ..shared.constants import *

import json
from src.llm.llm_client import (
    get_response_from_model, 
    # get_final_response_from_model
)

logger = logging.getLogger(__name__)


async def create_activity_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = {"user_id":user.id, "summary":update.message.text}
    result = create_activity(args)
    text, reply_markup = create_task_message(result)
    await update.message.reply_text(text=text, reply_markup=reply_markup)


async def llm_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not update.message or not update.message.text:
        return

    user_text = update.message.text.strip()
    if not user_text:
        return

    msg = await update.message.reply_text(PROCESSING)

    message_id = insert_message(user.id, 'user', user_text)

    try:

        response = get_response_from_model(user, limit=10)

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

            if function_name == "edit_activity":
                result = update_activity(args)
                text, reply_markup  = create_task_message(result)
                await msg.edit_text(text=text, reply_markup=reply_markup)
                notification(result.get("id"))
                result = json.dumps(result, indent=2, ensure_ascii=False)

            if function_name == "report_activities_by_time":
                result = report_activities_by_time(args)
                await msg.edit_text(text=result)

            if function_name == "report_activities_by_summary":
                result = report_activities_by_summary(args)
                await msg.edit_text(text=result)

            if function_name == "show_activity_detail":
                result = get_activity_details_by_summary(args)
                text, reply_markup = create_task_message(result)
                await msg.edit_text(text=text, reply_markup=reply_markup)
                notification(result.get('task_id'))
                
            insert_message(user.id, 'assistant', result)

            return ACTIVITY

    except Exception as e:
        delete_message(message_id)
        logger.warning(f"Initial model call failed: {e}")
        await msg.edit_text(AI_SERVER_ERROR)
