import ast
import json
import logging
import re

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from src.core.timezone import jalali_parts_to_utc
from src.services.message_service import (
    insert_message,
    delete_message
)
from src.services.task_service import (
    create_activity,
    update_activity,
    update_activity_frequency,
    notification,
    clear_activity,
    unarchive_activity,
)
from src.services.report_service import (
    report_activities_by_time,
    report_activities_by_summary,
    get_activity_details_by_summary
)
from src.services.resource_service import (
    create_resource,
    manage_task_resource,
    get_resource_title,
    link_task_resource_by_id,
    list_task_resource_links,
    get_resource_details,
    update_resource_unit,
    update_resource_min_pantry,
    add_resource_price,
    list_resource_prices,
    set_resource_parity,
    toggle_resource_tag,
    add_new_resource_tag,
    get_tag_title,
    create_tag,
)
from ..shared.commons import (
    create_task_message,
    resource_menu_keyboard,
    format_resource_links_text,
    resource_details_text,
    resource_details_keyboard,
    resource_tag_text,
    resource_tag_keyboard,
    resource_price_text,
    resource_price_keyboard,
    tags_home_keyboard,
    tag_edit_keyboard,
    tag_rename_confirm_keyboard,
)
from ..shared.constants import *
from .command_handlers import (
    report_command_handler,
    resource_command_handler,
    archive_command_handler,
    tags_command_handler,
    timer_command_handler,
    help_command_handler,
    stop_command_handler,
)

from src.llm.llm_client import get_response_from_model

logger = logging.getLogger(__name__)

_TOOL_NAMES = {
    "edit_activity",
    "report_activities_by_time",
    "report_activities_by_summary",
    "show_activity_detail",
    "create_resource",
    "manage_task_resource",
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


async def _show_message_result(msg, result):
    """Renders a plain {"status": ..., "message": ...} dict as text - for
    tools with no task card of their own (create_resource,
    manage_task_resource)."""
    message = result.get("message") if isinstance(result, dict) else str(result)
    await msg.edit_text(message or AI_SERVER_ERROR)


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
                # update_activity (the generic mapper-based path) only ever
                # recomputes next_date when new_dtstart is given - a rrule
                # change needs update_activity_frequency's recompute too, or
                # the displayed next occurrence goes stale until the next
                # confirm/skip (same bug fixed earlier for the manual path).
                if isinstance(result, dict) and result.get("status") != "error":
                    if args.get("new_rrule") is not None:
                        result = update_activity_frequency(args["activity_id"], args["new_rrule"], args.get("new_rrule_human"))
                    elif args.get("make_recurrent") is False:
                        result = update_activity_frequency(args["activity_id"], None)
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

            elif function_name == "create_resource":
                result = create_resource(args)
                await _show_message_result(msg, result)
                result = json.dumps(result, ensure_ascii=False)

            elif function_name == "manage_task_resource":
                result = manage_task_resource(args)
                if editing_task_id and isinstance(result, dict) and result.get("status") == "error":
                    clear_activity(editing_task_id)
                await _show_message_result(msg, result)
                result = json.dumps(result, ensure_ascii=False)

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


async def _finish_edit(update, context, result):
    """Common tail for every manual (✏️) field edit: drop the tracked task_id
    (this turn is terminal either way) and show the resulting card - or the
    error text - on the same bubble the field prompt was shown on."""
    context.user_data.pop("task_id", None)
    msg = await _get_working_message(update, context)
    await _show_task_result(msg, result)
    return ACTIVITY


async def _reprompt(update, context, text, state=EDIT_FIELD):
    """Re-shows `text` on the tracked bubble and stays in `state` - used
    when the user's reply couldn't be applied (bad time format, bad number)
    so they can just try again without losing their place."""
    msg = await _get_working_message(update, context)
    await msg.edit_text(text)
    context.user_data["prompt_message_id"] = msg.message_id
    return state


async def edit_field_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Text reply to one of the manual ✏️ edit-menu prompts (🏷️/📋, or the
    ⏰ time-of-day step of 📆) - manual counterpart of edit_activity, calling
    update_activity directly instead of going through the LLM. 🔄 frequency
    and the optional 🤖 description path hand off to the LLM instead (see
    query_handlers.py)."""
    user = update.effective_user
    task_id = context.user_data.get("task_id")
    field = context.user_data.get("edit_field")
    text = (update.message.text or "").strip()
    await update.message.delete()

    if not task_id or not field:
        return ACTIVITY

    if field == "summary":
        result = update_activity({"activity_id": task_id, "user_id": user.id, "new_summary": text})
        context.user_data.pop("edit_field", None)
        return await _finish_edit(update, context, result)

    if field == "description":
        result = update_activity({"activity_id": task_id, "user_id": user.id, "new_description": text})
        context.user_data.pop("edit_field", None)
        return await _finish_edit(update, context, result)

    if field == "date_time":
        match = re.fullmatch(r"([01]?\d|2[0-3]):([0-5]\d)", text)
        if not match:
            return await _reprompt(update, context, EDIT_DATE_INVALID_TIME)
        hour, minute = int(match.group(1)), int(match.group(2))
        jdate = context.user_data.get("edit_calendar_date")
        new_dt = jalali_parts_to_utc(jdate.year, jdate.month, jdate.day, hour, minute)
        result = update_activity({"activity_id": task_id, "user_id": user.id, "new_dtstart": new_dt})
        for key in ("edit_field", "edit_calendar_date", "edit_time"):
            context.user_data.pop(key, None)
        return await _finish_edit(update, context, result)

    return ACTIVITY


async def resource_selected_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Catches the sentinel message posted when the user picks a resource
    from the 🔍 inline-query picker inside the 🧺 menu (see
    resource_inline_query_handler) - never a genuine user message, so it's
    intercepted here instead of being treated as free text."""
    user_text = (update.message.text or "").strip()
    await update.message.delete()

    if not user_text.startswith("__resource_selected__:"):
        return RESOURCE_MENU

    _, task_id, resource_id = (user_text.split(':') + [None, None])[:3]
    resource_title = get_resource_title(resource_id)
    if not resource_title:
        context.user_data.pop("task_id", None)
        msg = await _get_working_message(update, context)
        await msg.edit_text(AI_SERVER_ERROR)
        return ACTIVITY

    context.user_data["task_id"] = task_id
    context.user_data["resource_id"] = resource_id
    msg = await _get_working_message(update, context)
    await msg.edit_text(RESOURCE_QTY_PROMPT.format(resource_title))
    context.user_data["prompt_message_id"] = msg.message_id
    return RESOURCE_QTY


async def resource_quantity_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Text reply to RESOURCE_QTY_PROMPT - manual counterpart of
    manage_task_resource, linking by the exact resource_id the 🔍 picker
    already resolved instead of fuzzy-matching a typed title."""
    task_id = context.user_data.get("task_id")
    resource_id = context.user_data.get("resource_id")
    text = (update.message.text or "").strip()
    await update.message.delete()

    try:
        quantity = float(text)
    except ValueError:
        msg = await _get_working_message(update, context)
        await msg.edit_text(RESOURCE_QTY_INVALID)
        context.user_data["prompt_message_id"] = msg.message_id
        return RESOURCE_QTY

    link_task_resource_by_id(task_id, int(resource_id), quantity)
    context.user_data.pop("resource_id", None)

    links = list_task_resource_links(task_id)
    msg = await _get_working_message(update, context)
    await msg.edit_text(format_resource_links_text(links), reply_markup=resource_menu_keyboard(task_id, links))
    context.user_data["prompt_message_id"] = msg.message_id
    return RESOURCE_MENU


async def resource_view_selected_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Catches the sentinel message posted when the user picks a resource
    from the 🔍 inline-query picker on the /resource home menu (see
    resource_inline_query_handler's `resdef:` prefix) - shows its details."""
    user_text = (update.message.text or "").strip()
    await update.message.delete()

    if not user_text.startswith("__resource_view__:"):
        return RESOURCE_HOME

    _, resource_id = user_text.split(':')
    resource_id = int(resource_id)
    resource = get_resource_details(resource_id)
    if not resource:
        msg = await _get_working_message(update, context)
        await msg.edit_text(RESOURCE_NOT_FOUND)
        return RESOURCE_HOME

    context.user_data["resource_id"] = resource_id
    msg = await _get_working_message(update, context)
    await msg.edit_text(resource_details_text(resource), reply_markup=resource_details_keyboard())
    context.user_data["prompt_message_id"] = msg.message_id
    return RESOURCE_DETAIL


async def resource_field_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Text reply to one of the manual /resource field prompts (title on
    create, unit, pantry, price, or the two-step parity) - manual
    counterpart of create_resource, no LLM involved."""
    user = update.effective_user
    field = context.user_data.get("resource_field")
    resource_id = context.user_data.get("resource_id")
    text = (update.message.text or "").strip()
    await update.message.delete()

    if field == "new_title":
        result = create_resource({"user_id": user.id, "title": text})
        if result.get("status") == "error":
            msg = await _get_working_message(update, context)
            await msg.edit_text(result.get("message") or AI_SERVER_ERROR)
            context.user_data["prompt_message_id"] = msg.message_id
            return RESOURCE_FIELD
        context.user_data["resource_id"] = result["id"]
        context.user_data.pop("resource_field", None)
        resource = get_resource_details(result["id"])
        msg = await _get_working_message(update, context)
        await msg.edit_text(resource_details_text(resource), reply_markup=resource_details_keyboard())
        return RESOURCE_DETAIL

    if field == "unit":
        update_resource_unit(resource_id, text)
        context.user_data.pop("resource_field", None)
        return await _finish_resource_field(update, context, resource_id)

    if field == "pantry":
        try:
            min_pantry = int(float(text))
        except ValueError:
            return await _reprompt(update, context, RESOURCE_PANTRY_INVALID, state=RESOURCE_FIELD)
        update_resource_min_pantry(resource_id, min_pantry)
        context.user_data.pop("resource_field", None)
        return await _finish_resource_field(update, context, resource_id)

    if field == "price":
        try:
            price = int(float(text))
        except ValueError:
            return await _reprompt(update, context, RESOURCE_PRICE_INVALID, state=RESOURCE_FIELD)
        add_resource_price(resource_id, price)
        context.user_data.pop("resource_field", None)
        prices = list_resource_prices(resource_id)
        msg = await _get_working_message(update, context)
        await msg.edit_text(resource_price_text(prices), reply_markup=resource_price_keyboard())
        return RESOURCE_PRICE

    if field == "parity_unit":
        context.user_data["resource_parity_unit"] = text
        context.user_data["resource_field"] = "parity_factor"
        msg = await _get_working_message(update, context)
        await msg.edit_text(RESOURCE_PARITY_FACTOR_PROMPT)
        context.user_data["prompt_message_id"] = msg.message_id
        return RESOURCE_FIELD

    if field == "parity_factor":
        try:
            factor = float(text)
        except ValueError:
            return await _reprompt(update, context, RESOURCE_PARITY_INVALID, state=RESOURCE_FIELD)
        consumption_unit = context.user_data.pop("resource_parity_unit", None)
        set_resource_parity(resource_id, consumption_unit, factor)
        context.user_data.pop("resource_field", None)
        return await _finish_resource_field(update, context, resource_id)

    return RESOURCE_HOME


async def _finish_resource_field(update, context, resource_id):
    resource = get_resource_details(resource_id)
    msg = await _get_working_message(update, context)
    await msg.edit_text(resource_details_text(resource), reply_markup=resource_details_keyboard())
    return RESOURCE_DETAIL


async def tag_selected_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Catches either the sentinel from the 🔍 tag picker (toggles an
    existing tag) or plain typed text (creates a new tag and links it) -
    both re-render the 🗂️ tag view and stay in RESOURCE_TAG."""
    user_text = (update.message.text or "").strip()
    resource_id = context.user_data.get("resource_id")
    await update.message.delete()

    if user_text.startswith("__tag_selected__:"):
        _, tag_id, _resource_id = user_text.split(':')
        toggle_resource_tag(resource_id, int(tag_id))
    elif user_text:
        add_new_resource_tag(resource_id, user_text)

    resource = get_resource_details(resource_id)
    msg = await _get_working_message(update, context)
    await msg.edit_text(resource_tag_text(resource), reply_markup=resource_tag_keyboard(resource_id))
    context.user_data["prompt_message_id"] = msg.message_id
    return RESOURCE_TAG


async def archive_selected_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Catches the sentinel posted when the user picks an archived activity
    from /archive's 🔍 picker (see resource_inline_query_handler's `archive:`
    prefix) - picking it out of the archive restores it, no extra confirm."""
    user_text = (update.message.text or "").strip()
    await update.message.delete()

    if not user_text.startswith("__archive_selected__:"):
        return ARCHIVE_BROWSE

    _, task_id = user_text.split(':')
    result = unarchive_activity(task_id)
    msg = await _get_working_message(update, context)
    await _show_task_result(msg, result)
    return ACTIVITY


async def tag_manage_selected_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Catches the sentinel posted when the user picks a tag from /tags' 🔍
    picker (see resource_inline_query_handler's `tagmgmt:` prefix) - shows
    its rename/delete view."""
    user_text = (update.message.text or "").strip()
    await update.message.delete()

    if not user_text.startswith("__tag_manage_selected__:"):
        return TAG_HOME

    _, tag_id = user_text.split(':')
    title = get_tag_title(tag_id)
    if not title:
        msg = await _get_working_message(update, context)
        await msg.edit_text(TAG_NOT_FOUND)
        return TAG_HOME

    context.user_data["tag_id"] = tag_id
    msg = await _get_working_message(update, context)
    await msg.edit_text(TAG_EDIT_TEXT.format(title), reply_markup=tag_edit_keyboard())
    context.user_data["prompt_message_id"] = msg.message_id
    return TAG_EDIT


async def tag_field_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Text reply in the /tags edit view: no tag_id yet means this is the
    ➕ step (create), otherwise it's a rename request that needs confirming."""
    tag_id = context.user_data.get("tag_id")
    text = (update.message.text or "").strip()
    await update.message.delete()

    if not tag_id:
        new_id = create_tag(text)
        context.user_data["tag_id"] = new_id
        msg = await _get_working_message(update, context)
        await msg.edit_text(TAG_EDIT_TEXT.format(get_tag_title(new_id)), reply_markup=tag_edit_keyboard())
        context.user_data["prompt_message_id"] = msg.message_id
        return TAG_EDIT

    context.user_data["tag_pending_title"] = text
    msg = await _get_working_message(update, context)
    await msg.edit_text(TAG_RENAME_CONFIRM.format(get_tag_title(tag_id), text), reply_markup=tag_rename_confirm_keyboard())
    context.user_data["prompt_message_id"] = msg.message_id
    return TAG_CONFIRM


_COMMAND_KEYBOARD_DISPATCH = {
    CMD_LABEL_REPORT: report_command_handler,
    CMD_LABEL_RESOURCE: resource_command_handler,
    CMD_LABEL_ARCHIVE: archive_command_handler,
    CMD_LABEL_TAGS: tags_command_handler,
    CMD_LABEL_TIMER: timer_command_handler,
    CMD_LABEL_HELP: help_command_handler,
    CMD_LABEL_STOP: stop_command_handler,
}


async def command_keyboard_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """The persistent reply-keyboard (see commons.main_reply_keyboard) sends
    its button label as plain text - recognize known labels and dispatch to
    the same handler /command would use, falling through to
    create_activity_message_handler for anything else (typed free text)."""
    text = (update.message.text or "").strip()
    handler = _COMMAND_KEYBOARD_DISPATCH.get(text)
    if handler:
        return await handler(update, context)
    return await create_activity_message_handler(update, context)
