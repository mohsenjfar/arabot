import asyncio
import logging
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (
    ContextTypes,
    ConversationHandler
)
from src.services.user_service import (
    user_exists,
    user_allowed,
    insert_user,
    activate_user
)
from src.services.task_service import create_activity
from ..shared.commons import resource_home_keyboard, archive_browse_keyboard, tags_home_keyboard, main_reply_keyboard
from ..shared.constants import *
from src.llm.llm_client import get_help_response_from_model

logger = logging.getLogger(__name__)


async def _show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows the command keyboard alongside a "pick from the menu" prompt -
    tracked so _clear_menu can collapse both once an option is picked."""
    msg = await update.message.reply_text(MENU_SELECT_PROMPT, reply_markup=main_reply_keyboard())
    context.user_data["menu_prompt_id"] = msg.message_id


async def _clear_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Called at the top of every command handler reachable from the /start
    menu: deletes the tracked "pick from the menu" prompt, and collapses the
    ReplyKeyboardMarkup itself. Telegram only lets a keyboard be attached or
    removed via a genuine sendMessage (never editMessageText), and there's no
    way to remove one without sending *something* - so this sends a
    throwaway message with ReplyKeyboardRemove and immediately deletes it."""
    menu_prompt_id = context.user_data.pop("menu_prompt_id", None)
    if not menu_prompt_id:
        return
    chat_id = update.effective_chat.id
    try:
        await context.bot.delete_message(chat_id, menu_prompt_id)
    except Exception as e:
        logger.info(f"Could not delete menu prompt: {e}")
    blip = await context.bot.send_message(chat_id, "🔽", reply_markup=ReplyKeyboardRemove())
    await blip.delete()


async def start_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not user_exists(user.id):
        insert_user(user.id, user.first_name)
        await _show_menu(update, context)
        await update.message.delete()
        return ACTIVITY

    if not user_allowed(user.id):
        await update.message.reply_text(USER_NOT_ALLOWED)
        await update.message.delete()
        return ConversationHandler.END

    activate_user(user.id)
    await _show_menu(update, context)
    await update.message.delete()
    return ACTIVITY

async def restart_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await _show_menu(update, context)
    await update.message.delete()
    return ACTIVITY

async def help_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await _clear_menu(update, context)
    msg = await update.message.reply_text(PROCESSING)
    await update.message.delete()
    try:
        await msg.edit_text(await asyncio.to_thread(get_help_response_from_model, user))
    except Exception as e:
        await msg.edit_text(AI_SERVER_ERROR)
        logger.warning(e)
        raise

async def stop_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await _clear_menu(update, context)
    await update.message.reply_text(STOP_BOT.format(user.first_name))
    await update.message.delete()
    return ConversationHandler.END

async def report_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await _clear_menu(update, context)
    prompt_msg = await update.message.reply_text(REPORT_PROMPT.format(user.first_name))
    context.user_data["prompt_message_id"] = prompt_msg.message_id
    await update.message.delete()
    return LLM

async def resource_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manual (button-driven, no LLM) resource management - see resource_service.py
    and the RESOURCE_* states in conversation_handlers.py."""
    await _clear_menu(update, context)
    prompt_msg = await update.message.reply_text(RESOURCE_HOME_TEXT, reply_markup=resource_home_keyboard())
    context.user_data["prompt_message_id"] = prompt_msg.message_id
    await update.message.delete()
    return RESOURCE_HOME

async def archive_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Browsing archived activities is inline-query only (see the 🗃️ button
    in the ✏️ menu for archiving one) - this just opens the picker."""
    await _clear_menu(update, context)
    prompt_msg = await update.message.reply_text(ARCHIVE_PROMPT_TEXT, reply_markup=archive_browse_keyboard())
    context.user_data["prompt_message_id"] = prompt_msg.message_id
    await update.message.delete()
    return ARCHIVE_BROWSE

async def tags_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manual (button-driven, no LLM) tag management - mirrors legacy-bot-version's
    tag_conversation.py."""
    await _clear_menu(update, context)
    prompt_msg = await update.message.reply_text(TAGS_HOME_TEXT, reply_markup=tags_home_keyboard())
    context.user_data["prompt_message_id"] = prompt_msg.message_id
    await update.message.delete()
    return TAG_HOME

async def timer_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await _clear_menu(update, context)

    # create_activity seeds the row with the *next* block (work vs break)
    # from the wall-clock grid, not the block in progress right now - same
    # as every ✔️/✖️ afterwards. There is no card shown here: delivery is
    # always through the background job once next_date is reached.
    create_activity({"user_id": user.id, "activity_type": "timer"})

    await update.message.delete()
    return ACTIVITY
