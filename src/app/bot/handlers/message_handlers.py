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
from .commons import create_task_message

from src.core.constants import *
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

async def edit_activity_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    result = create_activity(args)
    text, reply_markup  = create_task_message(result)
    await msg.edit_text(text=text, reply_markup=reply_markup)
    notification(result.get("id"))
    result = json.dumps(result, indent=2, ensure_ascii=False)
    return CHAT

async def report_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    result = create_activity(args)
    text, reply_markup  = create_task_message(result)
    await msg.edit_text(text=text, reply_markup=reply_markup)
    notification(result.get("id"))
    result = json.dumps(result, indent=2, ensure_ascii=False)
    return CHAT

