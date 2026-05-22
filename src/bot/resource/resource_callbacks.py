from telegram import Update
from telegram.ext import ContextTypes
from database.models.models_shim import Tag, Resource, ResourcePrice, ResourceParity
resource.resource_keyboards import (
    resources_keyboard,
    resource_keyboard,
    add_tag_to_resource_keyboard,
    add_price_to_resource_message
)
commons.common_keyboards import cancel_or_confirm_keyboard

commons.constants import (
    TAG, ADD, PRICE, EDIT,
    RESTART, UNIT, PARITY,
    END, PANTRY, REMOVE
)

async def resources_menu(message, context):
    context.chat_data[message.id] = {}
    lines = (
        "Here is a list of all resources",
        "to add another one press ➕",
        "to search resources by title use 🔍",
        "to search resources by tag use 🗂️"
    )
    text = ', '.join(lines)
    reply_markup = resources_keyboard(message.id)
    await message.edit_text(text, reply_markup=reply_markup)

def resource_details_message(resource):
    available = resource.total_available()
    details = [
        f"Title: {resource.title}",
        f"Total available amount: {(available/resource.get_conversion_factor()):.3f} {resource.unit}",
        f"Minimum pantry allowed: {resource.min_pantry}",
        f"Equal to: {available:.3f} {resource.get_consumption_unit()}" if resource.has_parity() else ""
    ]
    return '\n'.join(details)

async def resource_entry_points_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()
        if query.data == 'add':
            text = "Please enter resource title"
            await query.edit_message_text(text)
            return ADD
        elif query.data == 'back':
            await query.message.delete()
            return END
    else:
        text = update.message.text
        # inline selection encoded as: __resource_selected__:<resource_id>:<prev_msg_id>
        _, resource_id, prev_msg_id = text.split(':')
        resource = Resource.objects.get(id=int(resource_id))
        params = context.chat_data[int(prev_msg_id)]
        params['resource_id'] = resource_id
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id, 
            message_id=int(prev_msg_id), 
            text=resource_details_message(resource), 
            reply_markup=resource_keyboard()
        )
        await update.message.delete()
        return EDIT

async def insert_new_resource(update, context):
    prev_message = update.message.reply_to_message
    params = context.chat_data[prev_message.id]
    resource = Resource.objects.create(title=update.message.text)
    await update.message.delete()
    params['resource_id'] = resource.id
    await prev_message.edit_text(
        resource_details_message(resource), 
        reply_markup=resource_keyboard()
    )
    return EDIT

def related_resource_tags_message(resource):
    tags = resource.tag.all()
    text = "To search tags use 🔍, tap on tag to add or remove from resource\n"
    text += f"Related tags: {', '.join(tag.title for tag in tags)}"
    return text

async def edit_resource_callbacks(update, context):
    query = update.callback_query
    await query.answer()
    message = query.message
    params = context.chat_data[message.id]
    resource = Resource.objects.get(id=params['resource_id'])
    if query.data == 'tag':
        await query.edit_message_text(
            related_resource_tags_message(resource), 
            reply_markup=add_tag_to_resource_keyboard(message.id)
        )
        return TAG
    elif query.data == 'unit':
        text = f"Please enter resource unit"
        await query.edit_message_text(text)
        return UNIT
    elif query.data == 'pantry':
        text = f"Please enter minimum pantry allowed"
        await query.edit_message_text(text)
        return PANTRY
    elif query.data == 'back':
        await resources_menu(message, context)
        return RESTART
    elif query.data == 'remove':
        text = "Attention! this action will delete this resource and all related logs"
        reply_markup = cancel_or_confirm_keyboard()
        await query.edit_message_text(text, reply_markup=reply_markup)
        return REMOVE
    elif query.data == 'parity':
        params['consumption_unit'] = None
        params['conversion_factor'] = None
        text = f"Please enter consumption unit"
        await query.edit_message_text(text)
        return PARITY
    elif query.data == 'price':
        text, reply_markup = add_price_to_resource_message(resource)
        await query.edit_message_text(text, reply_markup=reply_markup)
        return PRICE

async def add_tag_to_resource_callbacks(update, context):
    # handle both CallbackQuery and inline-query selection messages
    query = update.callback_query
    if query:
        await query.answer()
        params = context.chat_data[query.message.id]
        resource = Resource.objects.get(id=params['resource_id'])
        await query.message.edit_text(
            resource_details_message(resource), 
            reply_markup=resource_keyboard()
        )
        return EDIT
    else:
        # message from inline-query selection encoded as: __tag_selected__:<tag_id>:<prev_msg_id>
        text = update.message.text
        if not text.startswith('__tag_selected__:'):
            await update.message.delete()
            return
        _, tag_id, prev_msg_id = text.split(':')
        prev_id = int(prev_msg_id)
        params = context.chat_data.get(prev_id)
        resource = Resource.objects.get(id=params['resource_id'])
        tag = Tag.objects.get(id=int(tag_id))
        if resource.tag.filter(id=tag.id).exists():
            resource.tag.remove(tag)
        else:
            resource.tag.add(tag)
        await update.message.delete()
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id, 
            message_id=prev_id, 
            text=related_resource_tags_message(resource), 
            reply_markup=add_tag_to_resource_keyboard(prev_id)
        )
        return

async def resource_unit(update, context):
    prev_message = update.message.reply_to_message
    params = context.chat_data[prev_message.id]
    resource = Resource.objects.get(id=params['resource_id'])
    resource.unit = update.message.text
    resource.save()
    await update.message.delete()
    await prev_message.edit_text(
        text=resource_details_message(resource), 
        reply_markup=resource_keyboard()
    )
    return EDIT

async def minimum_pantry(update, context):
    prev_message = update.message.reply_to_message
    params = context.chat_data[prev_message.id]
    resource = Resource.objects.get(id=params['resource_id'])
    resource.min_pantry = int(float(update.message.text))
    resource.save()
    await update.message.delete()
    await prev_message.edit_text(
        text=resource_details_message(resource), 
        reply_markup=resource_keyboard()
    )
    return EDIT

async def resource_delete_callbacks(update, context):
    query = update.callback_query
    await query.answer()
    message = query.message
    params = context.chat_data[message.id]
    resource = Resource.objects.get(id=params['resource_id'])
    if query.data == 'cancel':
        await message.edit_text(
            resource_details_message(resource), 
            reply_markup=resource_keyboard()
        )
        return EDIT
    elif query.data == 'confirm':
        resource.delete()
        await resources_menu(message, context)
        return RESTART

async def add_resource_parity_callbacks(update, context):
    query = update.callback_query
    if query:
        await query.answer()
        message = query.message
        params = context.chat_data[message.id]
        resource = Resource.objects.get(id=params['resource_id'])
        if query.data != 'cancel':
            if resource.has_parity():
                resource.parity.conversion_factor = params['conversion_factor']
                resource.parity.consumption_unit = params['consumption_unit']
                resource.parity.save()
            else:
                ResourceParity.objects.create(
                    resource=resource,
                    conversion_factor = params['conversion_factor'],
                    consumption_unit = params['consumption_unit']
                )
        await message.edit_text(
            text=resource_details_message(resource), 
            reply_markup=resource_keyboard()
        )
        return EDIT
    prev_message = update.message.reply_to_message
    params = context.chat_data[prev_message.id]
    if params['consumption_unit'] is None:
        params['consumption_unit'] = update.message.text
        await update.message.delete()
        text = f"Please enter conversion factor"
        await prev_message.edit_text(text)
        return
    if params['conversion_factor'] is None:
        params['conversion_factor'] = int(float(update.message.text))
        await update.message.delete()
        lines = [
            f"Conversion factor: {params['conversion_factor']}",
            f"Consumption unit: {params['consumption_unit']}"
        ]
        reply_markup = cancel_or_confirm_keyboard()
        await prev_message.edit_text('\n'.join(lines), reply_markup=reply_markup)
        return

async def add_price_callbacks(update, context):
    query = update.callback_query
    if query:
        await query.answer()
        message = query.message
        params = context.chat_data[message.id]
        resource = Resource.objects.get(id=params['resource_id'])
        if query.data == 'cancel':
            await message.edit_text(
                text=resource_details_message(resource), 
                reply_markup=resource_keyboard()
            )
            return EDIT
        elif query.data == 'price':
            text = f"Please enter new price"
            await query.edit_message_text(text)
            return
        elif query.data == 'delete':
            resource.prices.order_by('date').last().delete()
    else:
        message = update.message.reply_to_message
        params = context.chat_data[message.id]
        resource = Resource.objects.get(id=params['resource_id'])
        ResourcePrice.objects.create(
            resource = resource,
            price = int(float(update.message.text))
        )
        await update.message.delete()
    text, reply_markup = add_price_to_resource_message(resource)
    await message.edit_text(text, reply_markup=reply_markup)
    return
