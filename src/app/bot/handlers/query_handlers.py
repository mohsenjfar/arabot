import logging
import jdatetime
from telegram import Update
from telegram.ext import (
    ContextTypes
)
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InputTextMessageContent,
)
from telegram.constants import ParseMode

from src.core import timezone as tz
from src.services.task_service import (
    delete_activity,
    clear_activity,
    skip_activity,
    complete_activity,
    skip_future_activities,
    copy_activity,
    get_activity_datetime,
    update_activity,
)
from src.services.report_service import get_activity_details_by_id
from src.services.resource_service import (
    task_has_resource_history,
    list_task_resource_links,
    search_resources,
    unlink_task_resource_by_id,
    get_resource_title,
)
from ..shared.commons import create_task_message, edit_menu_keyboard, resource_menu_keyboard, format_resource_links_text
from ..shared.jalali_calendar import calendar_keyboard, shift_month
from ..shared.constants import *

logger = logging.getLogger(__name__)

async def complete_activity_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    task_id = query.data.split(':')[1]
    result = complete_activity(task_id)
    await query.answer(result)
    await query.message.delete()

async def skip_activity_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    task_id = query.data.split(':')[1]
    result = skip_activity(task_id)
    await query.answer(result)
    await query.message.delete()

async def delete_activity_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    task_id = query.data.split(':')[1]
    text = "آیا از حذف این فعالیت اطمینان داری؟"
    buttons = [[
        InlineKeyboardButton('بله',callback_data=f'confirm_delete:{task_id}'),
        InlineKeyboardButton('منصرف شدم',callback_data=f'cancel:{task_id}')
    ]]
    reply_markup = InlineKeyboardMarkup(buttons)
    await query.message.edit_text(text=text, reply_markup=reply_markup)

async def confirm_delete_activity_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    task_id = query.data.split(':')[1]
    if task_has_resource_history(task_id):
        result = skip_future_activities(task_id)
    else:
        result = delete_activity(task_id)
    await query.answer(result)
    await query.message.delete()

async def clear_activity_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    task_id = query.data.split(':')[1]
    result = clear_activity(task_id)
    await query.answer(result)
    await query.message.delete()

async def edit_activity_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """✏️ - opens the manual (button-driven, no LLM) edit menu instead of an
    LLM chat. edit_activity/manage_task_resource stay wired up in tools.json
    for the LLM elsewhere; this flow just no longer calls them."""
    query = update.callback_query
    task_id = query.data.split(':')[1]
    context.user_data["task_id"] = task_id
    await query.message.edit_text(EDIT_MENU_TEXT, reply_markup=edit_menu_keyboard())
    return EDIT_MENU

async def edit_menu_back_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    task_id = context.user_data.get("task_id")
    for key in ("task_id", "edit_field", "edit_calendar_date", "edit_time"):
        context.user_data.pop(key, None)
    task = get_activity_details_by_id(task_id)
    text, reply_markup = create_task_message(task)
    await query.message.edit_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    return ACTIVITY

async def edit_menu_copy_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    task_id = context.user_data.pop("task_id", None)
    new_task = copy_activity(task_id)
    text, reply_markup = create_task_message(new_task)
    await context.bot.send_message(update.effective_chat.id, text=text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    await query.answer(COPY_DONE.format(new_task.get("summary")))
    task = get_activity_details_by_id(task_id)
    text, reply_markup = create_task_message(task)
    await query.message.edit_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    return ACTIVITY

async def edit_menu_field_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    task_id = context.user_data.get("task_id")
    field = query.data.split(':')[1]
    task = get_activity_details_by_id(task_id)

    context.user_data["prompt_message_id"] = query.message.message_id

    if field == "summary":
        context.user_data["edit_field"] = "summary"
        await query.message.edit_text(EDIT_SUMMARY_PROMPT.format(task.get("summary")), parse_mode=ParseMode.HTML)
        return EDIT_FIELD

    if field == "description":
        context.user_data["edit_field"] = "description"
        await query.message.edit_text(EDIT_DESCRIPTION_PROMPT.format(task.get("description") or "-"), parse_mode=ParseMode.HTML)
        return EDIT_FIELD

    if field == "freq":
        context.user_data["edit_field"] = "freq"
        await query.message.edit_text(EDIT_FREQ_PROMPT.format(task.get("rrule_human") or "-"), parse_mode=ParseMode.HTML)
        return EDIT_FIELD

    if field == "date":
        context.user_data["edit_field"] = "date"
        current_dt = get_activity_datetime(task_id)
        jdt = tz.to_jal(current_dt)
        context.user_data["edit_calendar_date"] = jdatetime.date(jdt.year, jdt.month, jdt.day)
        context.user_data["edit_time"] = (jdt.hour, jdt.minute)
        await query.message.edit_text(
            f"📆 {task.get('summary')}",
            reply_markup=calendar_keyboard(context.user_data["edit_calendar_date"]),
        )
        return EDIT_FIELD

    return EDIT_MENU

async def _finalize_date_edit(query, context, task_id):
    jdate = context.user_data["edit_calendar_date"]
    hour, minute = context.user_data.get("edit_time", (0, 0))
    new_dt = tz.jalali_parts_to_utc(jdate.year, jdate.month, jdate.day, hour, minute)
    result = update_activity({"activity_id": task_id, "user_id": query.from_user.id, "new_dtstart": new_dt})
    for key in ("task_id", "edit_field", "edit_calendar_date", "edit_time"):
        context.user_data.pop(key, None)
    text, reply_markup = create_task_message(result)
    await query.message.edit_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

async def calendar_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    task_id = context.user_data.get("task_id")
    action = query.data.split(':', 2)[1:]

    if action[0] == "ignore":
        await query.answer()
        return EDIT_FIELD

    if action[0] == "prev":
        context.user_data["edit_calendar_date"] = shift_month(context.user_data["edit_calendar_date"], -1)
        await query.message.edit_reply_markup(reply_markup=calendar_keyboard(context.user_data["edit_calendar_date"]))
        return EDIT_FIELD

    if action[0] == "next":
        context.user_data["edit_calendar_date"] = shift_month(context.user_data["edit_calendar_date"], 1)
        await query.message.edit_reply_markup(reply_markup=calendar_keyboard(context.user_data["edit_calendar_date"]))
        return EDIT_FIELD

    if action[0] == "day":
        year, month, day = map(int, action[1].split('-'))
        context.user_data["edit_calendar_date"] = jdatetime.date(year, month, day)
        await query.message.edit_reply_markup(reply_markup=calendar_keyboard(context.user_data["edit_calendar_date"]))
        return EDIT_FIELD

    if action[0] == "now":
        now_j = tz.jnow()
        context.user_data["edit_calendar_date"] = jdatetime.date(now_j.year, now_j.month, now_j.day)
        context.user_data["edit_time"] = (now_j.hour, now_j.minute)
        await _finalize_date_edit(query, context, task_id)
        return ACTIVITY

    if action[0] == "time":
        context.user_data["edit_field"] = "date_time"
        await query.message.edit_text(EDIT_DATE_PROMPT_TIME)
        return EDIT_FIELD

    if action[0] == "confirm":
        await _finalize_date_edit(query, context, task_id)
        return ACTIVITY

    await query.answer()
    return EDIT_FIELD

async def resource_activity_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🧺 - manual (button-driven, no LLM) resource-link menu, merged with
    the 🔍 inline-query picker: pick an existing resource instead of the LLM
    fuzzy-matching a typed title (create_resource/manage_task_resource stay
    available for the LLM elsewhere, e.g. /resource)."""
    query = update.callback_query
    task_id = query.data.split(':')[1]
    context.user_data["task_id"] = task_id
    context.user_data["prompt_message_id"] = query.message.message_id
    links = list_task_resource_links(task_id)
    await query.message.edit_text(format_resource_links_text(links), reply_markup=resource_menu_keyboard(task_id, links))
    return RESOURCE_MENU

async def resource_remove_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    task_id = context.user_data.get("task_id")
    resource_id = int(query.data.split(':')[1])
    title = get_resource_title(resource_id)
    unlink_task_resource_by_id(task_id, resource_id)
    await query.answer(RESOURCE_REMOVED.format(title))

    links = list_task_resource_links(task_id)
    await query.message.edit_text(format_resource_links_text(links), reply_markup=resource_menu_keyboard(task_id, links))
    return RESOURCE_MENU

async def resource_back_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    task_id = context.user_data.pop("task_id", None)
    task = get_activity_details_by_id(task_id)
    text, reply_markup = create_task_message(task)
    await query.message.edit_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    return ACTIVITY

async def resource_inline_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    inline_query = update.inline_query
    parts = (inline_query.query or "").split(':', 2)
    if len(parts) < 2 or parts[0] != "resource":
        await inline_query.answer([])
        return

    task_id = parts[1]
    search_text = parts[2] if len(parts) > 2 else ""
    resources = search_resources(inline_query.from_user.id, search_text)

    results = [
        InlineQueryResultArticle(
            id=str(resource["id"]),
            title=resource["title"],
            description=resource.get("unit") or "",
            # Posted as a real chat message when picked - the RESOURCE_MENU
            # state's message handler intercepts this sentinel (see
            # resource_selected_message_handler).
            input_message_content=InputTextMessageContent(
                f"__resource_selected__:{task_id}:{resource['id']}"
            ),
        )
        for resource in resources
    ]
    await inline_query.answer(results, cache_time=0)

async def cancel_query_handler(update, context):
    query = update.callback_query
    task_id = query.data.split(':')[1]
    task_details = get_activity_details_by_id(task_id)
    text, reply_markup = create_task_message(task_details)
    await query.message.edit_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
