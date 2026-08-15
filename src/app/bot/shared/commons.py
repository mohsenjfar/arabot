import logging
from html import escape

from telegram import Update
from telegram.ext import ContextTypes
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode

from src.services.task_service import notification
from src.services.report_service import (
    get_activity_details_by_id,
    get_due_tasks
)
from .constants import RESOURCE_LINKS_HEADER, RESOURCE_EMPTY

logger = logging.getLogger(__name__)


def create_task_message(task_details):
    summary = task_details.get('summary')
    description = task_details.get('description')
    next_date = task_details.get('next_date')
    rrule_human = task_details.get('rrule_human')
    # description is wrapped in <code> so Telegram lets users copy it with a
    # single tap, instead of the manual select-and-copy other fields get.
    lines = (
        f"🔖 <b>{escape(summary)}</b>",
        f"\n📝 <code>{escape(description)}</code>" if description else "",
        f"\n📆 {escape(next_date)}" if next_date else "",
        f"🔄 {escape(rrule_human)}" if rrule_human else ""
    )
    task_id = task_details.get('id')
    buttons = [
        [
            InlineKeyboardButton('✔️',callback_data=f'complete:{task_id}'),
            InlineKeyboardButton('✏️',callback_data=f'edit:{task_id}'),
            InlineKeyboardButton('🧹',callback_data=f'clear:{task_id}'),
            InlineKeyboardButton('🧺',callback_data=f'resource:{task_id}'),
        ]
    ]
    if task_details.get('is_recurrent'):
        buttons[0].insert(1, InlineKeyboardButton('✖️',callback_data=f'skip:{task_id}'),)
    return '\n'.join(lines), InlineKeyboardMarkup(buttons)

def edit_menu_keyboard():
    """Manual (button-driven, no LLM) edit menu opened by ✏️ - mirrors the
    legacy Django bot's task_edit_keyboard. task_id itself isn't embedded in
    these callback_data: it's stashed in user_data by edit_activity_query_handler
    when the menu is opened, since this whole submenu only ever applies to
    that one task."""
    buttons = [
        [
            InlineKeyboardButton('🏷️', callback_data='editfield:summary'),
            InlineKeyboardButton('📋', callback_data='editfield:description'),
            InlineKeyboardButton('📆', callback_data='editfield:date'),
            InlineKeyboardButton('🔄', callback_data='editfield:freq'),
        ],
        [
            InlineKeyboardButton('🔙', callback_data='editback'),
            InlineKeyboardButton('🗑️', callback_data='editdelete'),
            InlineKeyboardButton('🟠🔵', callback_data='editcopy'),
            InlineKeyboardButton('🗃️', callback_data='editarchive'),
        ]
    ]
    return InlineKeyboardMarkup(buttons)

def format_resource_links_text(links):
    if not links:
        return RESOURCE_EMPTY
    lines = [RESOURCE_LINKS_HEADER]
    for link in links:
        direction = "افزایش" if link["quantity"] > 0 else "کاهش"
        lines.append(f"- {link['title']}: {direction} {abs(link['quantity'])} {link['unit']}")
    return "\n".join(lines)

def resource_menu_keyboard(task_id, links):
    """Manual (button-driven, no LLM) resource-link menu opened by 🧺: one
    ✖️ row per linked resource, plus 🔍 (inline-query picker, see
    resource_inline_query_handler) to add another and 🔙 to go back."""
    buttons = [
        [InlineKeyboardButton(f"✖️ {link['title']}", callback_data=f"resrm:{link['resource_id']}")]
        for link in links
    ]
    buttons.append([
        InlineKeyboardButton('🔍', switch_inline_query_current_chat=f'resource:{task_id}:'),
        InlineKeyboardButton('🔙', callback_data='resback'),
    ])
    return InlineKeyboardMarkup(buttons)

def resource_home_keyboard():
    """/resource landing menu - mirrors the legacy bot's resources_keyboard
    (minus the by-tag search, not asked for here): 🔍 browse/search existing
    resources via inline query, ➕ define a new one, 🔙 to back out (without
    it there was no way to abandon this screen once opened)."""
    buttons = [[
        InlineKeyboardButton('🔍', switch_inline_query_current_chat='resdef:'),
        InlineKeyboardButton('➕', callback_data='resnew'),
        InlineKeyboardButton('🔙', callback_data='rescancel'),
    ]]
    return InlineKeyboardMarkup(buttons)

def archive_browse_keyboard():
    """/archive - browsing is inline-query only, this button opens it
    pre-filled (see resource_inline_query_handler's `archive:` prefix)."""
    buttons = [[InlineKeyboardButton('🔍', switch_inline_query_current_chat='archive:')]]
    return InlineKeyboardMarkup(buttons)

def resource_details_text(resource):
    lines = [f"عنوان: {resource['title']}"]
    if resource.get('unit'):
        lines.append(f"واحد: {resource['unit']}")
    if resource.get('min_pantry') is not None:
        lines.append(f"حداقل موجودی: {resource['min_pantry']}")
    if resource.get('tags'):
        lines.append(f"تگ‌ها: {', '.join(resource['tags'])}")
    if resource.get('consumption_unit'):
        lines.append(f"واحد مصرف: {resource['consumption_unit']} (ضریب تبدیل: {resource['conversion_factor']})")
    return '\n'.join(lines)

def resource_details_keyboard():
    """Per-resource details/edit menu - mirrors the legacy bot's
    resource_keyboard. resource_id lives in user_data (same convention as
    edit_menu_keyboard's task_id), not embedded in callback_data."""
    buttons = [
        [
            InlineKeyboardButton('🗂️', callback_data='restag'),
            InlineKeyboardButton('📏', callback_data='resunit'),
            InlineKeyboardButton('🔄', callback_data='resparity'),
        ],
        [
            InlineKeyboardButton('🔙', callback_data='reshome'),
            InlineKeyboardButton('🗑️', callback_data='resdelete'),
            InlineKeyboardButton('🫙', callback_data='respantry'),
            InlineKeyboardButton('🧾', callback_data='resprice'),
        ],
    ]
    return InlineKeyboardMarkup(buttons)

def resource_tag_text(resource):
    tags = ', '.join(resource['tags']) if resource.get('tags') else 'هیچکدام'
    return f"تگ‌های مرتبط: {tags}\n\nبرای افزودن/حذف یه تگ موجود از 🔍 استفاده کن، یا اسم یه تگ جدید رو مستقیم بفرست"

def resource_tag_keyboard(resource_id):
    buttons = [[
        InlineKeyboardButton('🔍', switch_inline_query_current_chat=f'restag:{resource_id}:'),
        InlineKeyboardButton('🔙', callback_data='resback_detail'),
    ]]
    return InlineKeyboardMarkup(buttons)

def resource_price_text(prices):
    if not prices:
        return "قیمتی ثبت نشده"
    lines = ["آخرین قیمت‌ها:"]
    for p in prices:
        lines.append(f"- {p['price']:,} در {p['date']}")
    return '\n'.join(lines)

def resource_price_keyboard():
    buttons = [[
        InlineKeyboardButton('🔙', callback_data='resback_detail'),
        InlineKeyboardButton('➕', callback_data='resprice_add'),
        InlineKeyboardButton('🗑️', callback_data='resprice_del'),
    ]]
    return InlineKeyboardMarkup(buttons)

def resource_delete_confirm_keyboard():
    """Distinct callback prefixes from the activity-delete confirm
    (confirm_delete:/cancel:) so they don't collide."""
    buttons = [[
        InlineKeyboardButton('بله', callback_data='confirm_resdelete'),
        InlineKeyboardButton('منصرف شدم', callback_data='cancel_resdelete'),
    ]]
    return InlineKeyboardMarkup(buttons)

async def task_details_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    task_id = context.user_data.get("task_id")
    task = get_activity_details_by_id(task_id)
    text, reply_markup = create_task_message(task)
    notification(task_id)
    await update.message.reply_text(text=text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

async def check_and_send_tasks(context):
    try:
        tasks = get_due_tasks()
        
        if not tasks:
            return

        for task in tasks:
            try:
                task_details = get_activity_details_by_id(task.id)
                text, reply_markup  = create_task_message(task_details)
                await context.bot.send_message(task.user_id, text=text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
                notification(task.id)
            except Exception as e:
                logger.info(f"Error sending message for task {task.id} to chat {task.user_id}: {e}")
    except Exception as e:
        logger.info(f"An error occurred in scheduled_tasks for user {task.user_id}: {e}")