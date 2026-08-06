import ast
import json
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

from src.llm.llm_client import get_response_from_model

logger = logging.getLogger(__name__)

_TOOL_NAMES = {
    "edit_activity",
    "report_activities_by_time",
    "report_activities_by_summary",
    "show_activity_detail",
}


def _extract_fake_tool_call(content):
    """Smaller models sometimes emit a tool call as JSON text in the message
    content instead of using the API's structured tool_calls field. Recover
    the intended call instead of showing raw JSON to the user."""
    if not content:
        return None
    try:
        data = json.loads(content)
    except (ValueError, TypeError):
        try:
            # Some models write Python-literal True/False/None instead of JSON's
            # true/false/null; ast.literal_eval safely parses that shape too.
            data = ast.literal_eval(content)
        except (ValueError, TypeError, SyntaxError):
            return None
    if not isinstance(data, dict) or data.get("name") not in _TOOL_NAMES:
        return None
    args = data.get("parameters") or data.get("arguments") or {}
    return data["name"], json.dumps(args, ensure_ascii=False)


async def _show_task_result(msg, result):
    """Render a task dict as a task card, or an {"status": "error", ...} dict
    as plain error text. Service functions return the latter on failure
    (missing activity, invalid input, etc) instead of raising."""
    if not isinstance(result, dict) or result.get("status") == "error":
        message = result.get("message") if isinstance(result, dict) else str(result)
        await msg.edit_text(message or AI_SERVER_ERROR)
        return

    text, reply_markup = create_task_message(result)
    await msg.edit_text(text=text, reply_markup=reply_markup)
    notification(result.get("id"))


class _TrackedMessage:
    """Adapts a (chat_id, message_id) pair to the same edit_text(...) interface
    telegram.Message exposes, so callers don't care whether they're editing a
    freshly sent message or an existing tracked one."""

    def __init__(self, bot, chat_id, message_id):
        self._bot = bot
        self._chat_id = chat_id
        self._message_id = message_id

    async def edit_text(self, text=None, reply_markup=None):
        await self._bot.edit_message_text(
            chat_id=self._chat_id,
            message_id=self._message_id,
            text=text,
            reply_markup=reply_markup,
        )


async def _get_working_message(update, context):
    """The ✏️/`/report` prompt is the same bubble that started as (or will
    become) the activity card: reuse and keep editing that one message
    through card -> prompt -> card, instead of deleting it and sending a new
    one. Falls back to a fresh reply if there's no tracked prompt or editing
    it fails (e.g. it was already deleted)."""
    prompt_message_id = context.user_data.pop("prompt_message_id", None)
    if prompt_message_id:
        msg = _TrackedMessage(context.bot, update.effective_chat.id, prompt_message_id)
        try:
            await msg.edit_text(text=PROCESSING)
            return msg
        except Exception as e:
            logger.info(f"Could not reuse prompt message, sending a new one: {e}")

    return await update.message.reply_text(PROCESSING)


async def create_activity_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = {"user_id":user.id, "summary":update.message.text}
    result = create_activity(args)
    text, reply_markup = create_task_message(result)
    await update.message.reply_text(text=text, reply_markup=reply_markup)
    await update.message.delete()


async def llm_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not update.message or not update.message.text:
        return ACTIVITY

    user_text = update.message.text.strip()
    if not user_text:
        return ACTIVITY

    msg = await _get_working_message(update, context)
    await update.message.delete()

    message_id = insert_message(user.id, 'user', user_text)

    try:
        response = get_response_from_model(user, limit=10)
        message = response.choices[0].message
        calls = [(tc.function.name, tc.function.arguments) for tc in (message.tool_calls or [])]

        if not calls:
            fallback = _extract_fake_tool_call(message.content)
            if fallback:
                calls = [fallback]

        if not calls:
            final_text = message.content
            if final_text:
                insert_message(user.id, 'assistant', final_text)
                await msg.edit_text(final_text)
            else:
                delete_message(message_id)
                await msg.edit_text(AI_SERVER_ERROR)
            return ACTIVITY

        for function_name, raw_args in calls:
            args = json.loads(raw_args)
            args['user_id'] = user.id

            logger.info(args)

            if function_name == "edit_activity":
                result = update_activity(args)
                await _show_task_result(msg, result)
                result = json.dumps(result, indent=2, ensure_ascii=False)

            elif function_name == "report_activities_by_time":
                result = report_activities_by_time(args)
                await _show_task_result(msg, result)
                result = json.dumps(result, indent=2, ensure_ascii=False)

            elif function_name == "report_activities_by_summary":
                result = report_activities_by_summary(args)
                await _show_task_result(msg, result)
                result = json.dumps(result, indent=2, ensure_ascii=False)

            elif function_name == "show_activity_detail":
                result = get_activity_details_by_summary(args)
                await _show_task_result(msg, result)
                result = json.dumps(result, indent=2, ensure_ascii=False)

            else:
                logger.warning(f"Unknown function call from model: {function_name}")
                result = json.dumps({"status": "error", "message": "unknown function"}, ensure_ascii=False)

            insert_message(user.id, 'assistant', result)

        return ACTIVITY

    except Exception as e:
        delete_message(message_id)
        logger.warning(f"Initial model call failed: {e}")
        await msg.edit_text(AI_SERVER_ERROR)
        return ACTIVITY
