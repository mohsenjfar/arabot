import ast
import json
import logging

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from src.services.message_service import (
    insert_message,
    delete_message
)
from src.services.task_service import (
    create_activity,
    update_activity,
    notification,
    clear_activity
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


def _parse_json_ish(content):
    """Best-effort parse of `content` as a JSON object, tolerating Python
    literals (True/False/None) some models emit instead of JSON's
    true/false/null. Returns the dict, or None if it's not a JSON object."""
    if not content:
        return None
    try:
        data = json.loads(content)
    except (ValueError, TypeError):
        try:
            data = ast.literal_eval(content)
        except (ValueError, TypeError, SyntaxError):
            return None
    return data if isinstance(data, dict) else None


def _extract_fake_tool_call(content):
    """Smaller models sometimes emit a tool call as JSON text in the message
    content instead of using the API's structured tool_calls field. Recover
    the intended call instead of showing raw JSON to the user."""
    data = _parse_json_ish(content)
    if not data or data.get("name") not in _TOOL_NAMES:
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
    await msg.edit_text(text=text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    notification(result.get("id"))


async def _show_task_results(context, chat_id, msg, results):
    """Time-based reports render each matching activity as its own full
    card with buttons - exactly like the reminder job - instead of bundling
    them into one summary. The first one reuses `msg` (the in-progress
    prompt bubble); the rest are sent as new messages. Each one shown is
    marked notified so it isn't repeated by a later report or double-sent
    by the reminder job."""
    if not results:
        await msg.edit_text("فعالیتی وجود نداره")
        return

    first, *rest = results
    text, reply_markup = create_task_message(first)
    await msg.edit_text(text=text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    notification(first.get("id"))

    for result in rest:
        text, reply_markup = create_task_message(result)
        await context.bot.send_message(chat_id, text=text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
        notification(result.get("id"))


class _TrackedMessage:
    """Adapts a (chat_id, message_id) pair to the same edit_text(...) interface
    telegram.Message exposes, so callers don't care whether they're editing a
    freshly sent message or an existing tracked one."""

    def __init__(self, bot, chat_id, message_id):
        self._bot = bot
        self._chat_id = chat_id
        self._message_id = message_id

    @property
    def message_id(self):
        return self._message_id

    async def edit_text(self, text=None, reply_markup=None, parse_mode=None):
        await self._bot.edit_message_text(
            chat_id=self._chat_id,
            message_id=self._message_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
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
    await update.message.reply_text(text=text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    notification(result.get("id"))
    await update.message.delete()


async def llm_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not update.message or not update.message.text:
        return ACTIVITY

    user_text = update.message.text.strip()
    if not user_text:
        return ACTIVITY

    # Set only by the ✏️ button, which strips that activity's card down to a
    # bare prompt (no buttons). If this turn ends without successfully
    # editing it (error, or the model never gets to a confirmed tool call),
    # the user is left with no way to interact with it - reset its
    # `notified` flag so the reminder job resends the full card with
    # buttons. Popped once the edit either finalizes or gives up.
    editing_task_id = context.user_data.get("task_id")

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
            # Never show a raw JSON/dict blob to the user: if the model
            # dumped an object here that _extract_fake_tool_call didn't
            # recognize as one of the known tools (e.g. a TaskResponse-
            # shaped dict), treat it as a failure instead of leaking it.
            if final_text and _parse_json_ish(final_text) is None:
                insert_message(user.id, 'assistant', final_text)
                await msg.edit_text(final_text)
                # The system prompt requires a confirmation preview before
                # *every* function call (edit, reports, everything) - a
                # plain-text reply here is almost always that preview, not a
                # final answer. Stay in LLM so the user's next message
                # (their "بله") keeps talking to the model instead of being
                # treated as a brand new plain-text activity. The escape
                # hatch is /start, which always resets to ACTIVITY.
                context.user_data["prompt_message_id"] = msg.message_id
                return LLM
            else:
                delete_message(message_id)
                if editing_task_id:
                    context.user_data.pop("task_id", None)
                    clear_activity(editing_task_id)
                await msg.edit_text(AI_SERVER_ERROR)
            return ACTIVITY

        # A tool is actually about to run - whichever one it is, this turn
        # is the terminal step of the edit conversation, so stop tracking it.
        if editing_task_id:
            context.user_data.pop("task_id", None)

        for function_name, raw_args in calls:
            args = json.loads(raw_args)
            args['user_id'] = user.id

            logger.info(args)

            if function_name == "edit_activity":
                result = update_activity(args)
                if editing_task_id and isinstance(result, dict) and result.get("status") == "error":
                    clear_activity(editing_task_id)
                await _show_task_result(msg, result)
                result = json.dumps(result, indent=2, ensure_ascii=False)

            elif function_name == "report_activities_by_time":
                result = report_activities_by_time(args)
                if isinstance(result, list):
                    await _show_task_results(context, update.effective_chat.id, msg, result)
                    result = json.dumps(
                        {"count": len(result), "summaries": [r.get("summary") for r in result]},
                        ensure_ascii=False,
                    )
                else:
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
        if editing_task_id:
            context.user_data.pop("task_id", None)
            clear_activity(editing_task_id)
        logger.warning(f"Initial model call failed: {e}")
        await msg.edit_text(AI_SERVER_ERROR)
        return ACTIVITY
