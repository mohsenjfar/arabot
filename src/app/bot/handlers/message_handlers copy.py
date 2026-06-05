import logging
from telegram import Update
from telegram.ext import (
    ContextTypes, 
    ConversationHandler
)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from src.services.user_service import keep_in_mind
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
    get_activity_details_by_summary,
    get_activity_details_by_id,
    get_due_tasks
)

from src.core.constants import *
import json
from src.llm.llm_client import (
    get_response_from_model, 
    # get_final_response_from_model
)

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

            if function_name == "end_conversation":
                text = "مکالمه پایان یافت."
                await msg.edit_text(text)
                insert_message(user.id, 'assistant', text)
                return ConversationHandler.END

            if function_name == "keep_in_mind":
                result = keep_in_mind(args)
                await msg.edit_text(result)

            if function_name == "create_activity":
                result = create_activity(args)
                text, reply_markup  = create_task_message(result)
                await msg.edit_text(text=text, reply_markup=reply_markup)
                notification(result.get("id"))
                result = json.dumps(result, indent=2, ensure_ascii=False)

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

    except Exception as e:
        delete_message(message_id)
        logger.warning(f"Initial model call failed: {e}")
        await msg.edit_text(AI_SERVER_ERROR)

def create_task_message(task_details):
    summary = task_details.get('summary')
    description = task_details.get('description')
    next_date = task_details.get('next_date')
    rrule_human = task_details.get('rrule_human')
    lines = (
        f"🔖 *{summary}*",
        f"\n📝 {description}" if description else "",
        f"\n📆 {next_date}" if next_date else "",
        f"🔄 {rrule_human}" if rrule_human else ""
    )
    task_id = task_details.get('id')
    buttons = [
        [
            InlineKeyboardButton('📦',callback_data=f'resource:{task_id}'),
            InlineKeyboardButton('✔️',callback_data=f'complete:{task_id}'),
        ],
        [
            InlineKeyboardButton('🗑️',callback_data=f'delete:{task_id}'),
            InlineKeyboardButton('✏️',callback_data=f'edit:{task_id}'),
            InlineKeyboardButton('🧹',callback_data=f'clear:{task_id}'),
        ]
    ]
    if task_details.get('is_recurrent'):
        buttons[0].insert(2, InlineKeyboardButton('➡️',callback_data=f'skip:{task_id}'),)
    return '\n'.join(lines), InlineKeyboardMarkup(buttons)

async def task_details_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    task_id = context.user_data.get("task_id")
    task = get_activity_details_by_id(task_id)
    text, reply_markup = create_task_message(task)
    notification(task_id)
    await update.message.reply_text(text=text, reply_markup=reply_markup)

async def check_and_send_tasks(context):
    try:
        tasks = get_due_tasks()
        
        if not tasks:
            return

        for task in tasks:
            try:
                task_details = get_activity_details_by_id(task.id)
                text, reply_markup  = create_task_message(task_details)
                await context.bot.send_message(task.user_id, text=text, reply_markup=reply_markup)
                notification(task.id)
            except Exception as e:
                logger.info(f"Error sending message for task {task.id} to chat {task.user_id}: {e}")
    except Exception as e:
        logger.info(f"An error occurred in scheduled_tasks for user {task.user_id}: {e}")
