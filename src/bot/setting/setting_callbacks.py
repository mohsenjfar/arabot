utils.aladhan import update_aladhan
setting.setting_keyboards import (
    settings_keyboard
)
commons.constants import (
    VIEW, SETTINGS, help_dict
)
from database.models.models_shim import Task

async def settings(update, context):
    query = update.callback_query
    await query.answer()
    message = query.message
    context.chat_data[message.id] = {'task_page':0}
    text = "Please choose an option"
    reply_markup = settings_keyboard()
    await message.edit_text(text, reply_markup=reply_markup)
    return SETTINGS

async def settings_callbacks(update, context):
    query = update.callback_query
    if query:
        await query.answer()
        message = query.message
        if query.data == "back":
            await message.delete()
            return VIEW
        elif query.data == "location":
            text = "Please send your current location"
            await query.edit_message_text(text)
            return
        elif query.data == "help":
            text = help_dict.get('main', "No Text")
            await query.edit_message_text(text)
            return
        elif query.data == "archive":
            text = "Select a task to unarchive:"
            await message.edit_text(text)
            return
    else:
        loc = update.message.location
        if loc:
            prev_message = update.message.reply_to_message
            await update.message.delete()
            update_aladhan(loc.longitude, loc.latitude)
            text = f"New location updated: Long: {loc.longitude}, Lat: {loc.latitude}"
            await prev_message.edit_text(text)
            return VIEW
        message = update.message
        if "__task_selected__" in message.text:
            task_id = message.text.split(':')[1]
            task = Task.objects.get(id=task_id)
            task.archived = not task.archived
            task.save()
            await update.message.delete()
            return
