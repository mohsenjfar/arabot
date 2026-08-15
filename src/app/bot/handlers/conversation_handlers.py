import logging

from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)

from .message_handlers import (
    create_activity_message_handler,
    llm_message_handler,
    edit_field_message_handler,
    resource_selected_message_handler,
    resource_quantity_message_handler,
    resource_view_selected_message_handler,
    resource_field_message_handler,
    tag_selected_message_handler,
    archive_selected_message_handler,
    tag_manage_selected_message_handler,
    tag_field_message_handler,
    command_keyboard_message_handler,
)

from .command_handlers import (
    start_command_handler,
    restart_command_handler,
    help_command_handler,
    stop_command_handler,
    report_command_handler,
    timer_command_handler,
    resource_command_handler,
    archive_command_handler,
    tags_command_handler,
)

from .query_handlers import (
    complete_activity_query_handler,
    edit_activity_query_handler,
    edit_menu_field_query_handler,
    edit_menu_back_query_handler,
    edit_menu_copy_query_handler,
    edit_menu_delete_query_handler,
    edit_menu_archive_query_handler,
    edit_menu_description_ai_query_handler,
    calendar_query_handler,
    skip_activity_query_handler,
    delete_activity_query_handler,
    confirm_delete_activity_query_handler,
    clear_activity_query_handler,
    resource_activity_query_handler,
    resource_remove_query_handler,
    resource_back_query_handler,
    resource_home_add_query_handler,
    resource_home_cancel_query_handler,
    resource_detail_query_handler,
    resource_back_to_detail_query_handler,
    resource_price_add_query_handler,
    resource_price_delete_query_handler,
    resource_delete_confirm_query_handler,
    resource_delete_cancel_query_handler,
    tags_home_add_query_handler,
    tags_home_cancel_query_handler,
    tag_edit_back_query_handler,
    tag_delete_query_handler,
    tag_rename_confirm_query_handler,
    tag_rename_cancel_query_handler,
    cancel_query_handler
)

from ..shared.constants import *

logger = logging.getLogger(__name__)

END = ConversationHandler.END

main_conversation = ConversationHandler(
    name="main_conversation",
    entry_points=[CommandHandler("start", start_command_handler)],
    states={
        ACTIVITY: [
            CommandHandler("help", help_command_handler),
            CommandHandler("report", report_command_handler),
            CommandHandler("timer", timer_command_handler),
            CommandHandler("resource", resource_command_handler),
            CommandHandler("archive", archive_command_handler),
            CommandHandler("tags", tags_command_handler),
            CommandHandler("stop", stop_command_handler),
            MessageHandler(filters.TEXT & ~filters.COMMAND, command_keyboard_message_handler),
            CallbackQueryHandler(complete_activity_query_handler, pattern="^complete:"),
            CallbackQueryHandler(skip_activity_query_handler, pattern="^skip:"),
            CallbackQueryHandler(delete_activity_query_handler, pattern="^delete:"),
            CallbackQueryHandler(confirm_delete_activity_query_handler, pattern="^confirm_delete:"),
            CallbackQueryHandler(edit_activity_query_handler, pattern="^edit:"),
            CallbackQueryHandler(clear_activity_query_handler, pattern="^clear:"),
            CallbackQueryHandler(resource_activity_query_handler, pattern="^resource:")
        ],
        LLM: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, llm_message_handler),
        ],
        EDIT_MENU: [
            CallbackQueryHandler(edit_menu_field_query_handler, pattern="^editfield:"),
            CallbackQueryHandler(edit_menu_copy_query_handler, pattern="^editcopy$"),
            CallbackQueryHandler(edit_menu_delete_query_handler, pattern="^editdelete$"),
            CallbackQueryHandler(confirm_delete_activity_query_handler, pattern="^confirm_delete:"),
            CallbackQueryHandler(edit_menu_archive_query_handler, pattern="^editarchive$"),
            CallbackQueryHandler(edit_menu_back_query_handler, pattern="^editback$"),
        ],
        EDIT_FIELD: [
            CallbackQueryHandler(calendar_query_handler, pattern="^caldate:"),
            CallbackQueryHandler(edit_menu_description_ai_query_handler, pattern="^editdescai$"),
            CallbackQueryHandler(edit_menu_back_query_handler, pattern="^editback$"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, edit_field_message_handler),
        ],
        RESOURCE_MENU: [
            CallbackQueryHandler(resource_remove_query_handler, pattern="^resrm:"),
            CallbackQueryHandler(resource_back_query_handler, pattern="^resback$"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, resource_selected_message_handler),
        ],
        RESOURCE_QTY: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, resource_quantity_message_handler),
        ],
        RESOURCE_HOME: [
            CallbackQueryHandler(resource_home_add_query_handler, pattern="^resnew$"),
            CallbackQueryHandler(resource_home_cancel_query_handler, pattern="^rescancel$"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, resource_view_selected_message_handler),
        ],
        RESOURCE_DETAIL: [
            CallbackQueryHandler(resource_detail_query_handler, pattern="^(reshome|resunit|respantry|resparity|resprice|restag|resdelete)$"),
        ],
        RESOURCE_FIELD: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, resource_field_message_handler),
        ],
        RESOURCE_TAG: [
            CallbackQueryHandler(resource_back_to_detail_query_handler, pattern="^resback_detail$"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, tag_selected_message_handler),
        ],
        RESOURCE_PRICE: [
            CallbackQueryHandler(resource_price_add_query_handler, pattern="^resprice_add$"),
            CallbackQueryHandler(resource_price_delete_query_handler, pattern="^resprice_del$"),
            CallbackQueryHandler(resource_back_to_detail_query_handler, pattern="^resback_detail$"),
        ],
        RESOURCE_DELETE: [
            CallbackQueryHandler(resource_delete_confirm_query_handler, pattern="^confirm_resdelete$"),
            CallbackQueryHandler(resource_delete_cancel_query_handler, pattern="^cancel_resdelete$"),
        ],
        ARCHIVE_BROWSE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, archive_selected_message_handler),
        ],
        TAG_HOME: [
            CallbackQueryHandler(tags_home_add_query_handler, pattern="^tagnew$"),
            CallbackQueryHandler(tags_home_cancel_query_handler, pattern="^tagcancel$"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, tag_manage_selected_message_handler),
        ],
        TAG_EDIT: [
            CallbackQueryHandler(tag_edit_back_query_handler, pattern="^tagback$"),
            CallbackQueryHandler(tag_delete_query_handler, pattern="^tagdelete$"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, tag_field_message_handler),
        ],
        TAG_CONFIRM: [
            CallbackQueryHandler(tag_rename_confirm_query_handler, pattern="^tagrenameconfirm$"),
            CallbackQueryHandler(tag_rename_cancel_query_handler, pattern="^tagrenamecancel$"),
        ],
    },
    fallbacks=[
        CommandHandler("start", restart_command_handler),
        CallbackQueryHandler(cancel_query_handler, pattern="^cancel:")
    ],
    persistent=False
)