from telegram import Update
from telegram.ext import ContextTypes
from database.models.models_shim import Tag
tags.tag_keyboards import (
    insert_new_tag_keyboard,
    edit_tag_keyboard,
    cancel_or_confirm_keyboard
)
commons.constants import (
    ADD, EDIT, END, RESTART
)

async def tags_menu(update, context):
    query = update.callback_query
    await query.answer()
    message = query.message
    context.chat_data[message.id] = {}
    text = "Here is a list of all tags, to add another one press ➕ or select a tag to edit"
    reply_markup = insert_new_tag_keyboard(message.id)
    await query.edit_message_text(text, reply_markup=reply_markup)

async def tag_entry_points_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()
        if query.data == 'add':
            text = "Please enter tag title"
            await query.edit_message_text(text)
            return ADD
        elif query.data == 'back':
            await query.message.delete()
            return END
    else:
        message = update.message.text
        tag_id = int(message.split(':')[1])
        message_id = int(message.split(':')[2])
        tag = Tag.objects.get(id=tag_id)
        chat_id = update.effective_chat.id
        keyboard = edit_tag_keyboard()
        params = context.chat_data[message_id]
        params['tag_id'] = tag_id
        await update.message.delete()
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f"Title: {tag.title}\nEnter a new name for tag or delete",
            reply_markup=keyboard
        )
        return EDIT

async def insert_tag_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    prev_message = update.message.reply_to_message
    title = update.message.text
    await update.message.delete()
    tag = Tag.objects.create(title=title)
    reply_markup = edit_tag_keyboard()
    params = context.chat_data[prev_message.id]
    params['tag_id'] = tag.id
    await prev_message.edit_text(
        f"Title: {tag.title}\nEnter a new name for tag or delete", 
        reply_markup=reply_markup
    )
    return EDIT

async def edit_tag_query_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    message = query.message
    params = context.chat_data[message.id]
    tag = Tag.objects.get(id=params['tag_id'])
    if query.data == 'delete':
        tag.delete()
        await tags_menu(update, context)
        return RESTART
    elif query.data == 'cancel':
        await tags_menu(update, context)
        return RESTART
    elif query.data == 'confirm':
        tag.title = params['tag_title']
        tag.save()
    reply_markup = edit_tag_keyboard()
    await message.edit_text(
        f"Title: {tag.title}\nEnter a new name for tag or delete", 
        reply_markup=reply_markup
    )
    return
    
async def edit_tag_message_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    prev_message = update.message.reply_to_message
    params = context.chat_data[prev_message.message_id]
    new_title = update.message.text
    await update.message.delete()
    tag = Tag.objects.get(id=params['tag_id'])
    prev_title = tag.title
    params['tag_title'] = new_title
    text = f"Change tag title from {prev_title} to {new_title}?"
    reply_markup = cancel_or_confirm_keyboard()
    await prev_message.edit_text(text, reply_markup=reply_markup)
    return
