from database.models.models_shim import Task, Resource, ResourceLog
from django.utils import timezone
resource.task.task_resource_keyboards import freq_selection_message
resource.task.task_resource_messages import (
    task_resource_message,
    task_log_message
)
commons.commons_callbacks import task_view_message
commons.constants import (
    RESTART, RESOURCE, EDIT, AMOUNT, REMOVE, EDIT_AMOUNT,
    END, RESTART
)

async def task_resource_menu(update, context):
    query = update.callback_query
    await query.answer()
    message = query.message
    params = context.chat_data[message.id]
    await task_resource_message(message, params)
    return RESOURCE

async def task_resource_entry_points(update,context):
    query = update.callback_query
    if query:
        await query.answer()
        message_id = query.message.id
        task = Task.objects.get(message_id=message_id)
        text, reply_markup = task_view_message(task)
        await query.edit_message_text(text, reply_markup=reply_markup)
        return END
    else:
        message = update.message
        # __log_selected__:<message_id>:<log_id>
        if "__log_selected__" in message.text:
            parts = message.text.split(':')
            message_id = int(parts[1])
            log_id = int(parts[2])
            params = context.chat_data[message_id]
            params['log_id'] = log_id
            log = ResourceLog.objects.get(id=log_id)
            text, reply_markup= task_log_message(log)
            await message.delete()
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id, 
                message_id=message_id, 
                text=text,
                reply_markup=reply_markup
            )
            return EDIT
        # __resource_selected_to_reduce__:<message_id>:<task_id>:<resource_id>
        elif "__resource_selected_to_reduce__" in message.text:
            parts = message.text.split(':')
            message_id = int(parts[1])
            task_id = parts[2]
            resource_id = int(parts[3])
            params = context.chat_data[message_id]
            params['task_id'] = task_id
            params['resource_id'] = resource_id
            params['increase'] = -1
            await update.message.delete()
            resource = Resource.objects.get(id=params['resource_id'])
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id, 
                message_id=message_id, 
                text=f"Please enter the amount for {resource.title}"
            )
            return AMOUNT
        # __resource_selected_to_increase__:<message_id>:<task_id>:<resource_id>
        elif "__resource_selected_to_increase__" in message.text:
            parts = message.text.split(':')
            message_id = int(parts[1])
            task_id = parts[2]
            resource_id = int(parts[3])
            params = context.chat_data[message_id]
            params['task_id'] = task_id
            params['resource_id'] = resource_id
            params['increase'] = 1
            await update.message.delete()
            resource = Resource.objects.get(id=params['resource_id'])
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id, 
                message_id=message_id, 
                text=f"Please enter the amount for {resource.title}"
            )
            return AMOUNT

async def edit_task_resource_callbacks(update,context):
    query = update.callback_query
    if query:
        await query.answer()
        message_id = query.message.id
        params = context.chat_data[message_id]
        task = Task.objects.get(message_id=message_id)
        if query.data == 'back':
            text, reply_markup = task_view_message(task)
            await query.edit_message_text(text, reply_markup=reply_markup)
            return END
        elif query.data == 'remove':
            if task.parent.freq:
                text, reply_markup = freq_selection_message()
                await query.edit_message_text(text, reply_markup=reply_markup)
                return REMOVE
            ResourceLog.objects.get(id=params['log_id']).delete()
            await task_resource_message(query.message, params)
            return RESTART
        elif query.data == 'edit':
            log = ResourceLog.objects.get(id=params['log_id'])
            lines = [
                f"Please enter new amount for {log.resource.title}:",
                f"current amount is {log.quantity}"
            ]
            await query.edit_message_text('\n'.join(lines))
            return EDIT_AMOUNT
        elif query.data == 'used':
            params['resources'] = Resource.objects.all()
            log = ResourceLog.objects.get(id=params['log_id'])
            log.completed = not log.completed
            log.modified = timezone.now()
            log.save()
            await task_resource_message(query.message, params)
            return RESTART
        elif query.data == 'skip':
            params['resources'] = Resource.objects.all()
            log = ResourceLog.objects.get(id=params['log_id'])
            log.skipped = not log.skipped
            log.modified = timezone.now()
            log.save()
            await task_resource_message(query.message, params)
            return
    else:
        # __resource_selected__:<resource_id>:<prev_id>
        message = update.message
        parts = message.text.split(":")
        resource_id = int(parts[1])
        message_id = int(parts[2])
        params = context.chat_data[message_id]
        log = ResourceLog.objects.get(id=params['log_id'])
        new_resource = Resource.objects.get(id=resource_id)
        ResourceLog.objects.order_by('task__start').filter(
            resource=log.resource,
            completed=False,
            skipped=False
        ).update(resource=new_resource)
        log.resource = new_resource
        log.save()
        await update.message.delete()
        text, reply_markup = task_log_message(log)
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id, 
            message_id=message_id, 
            text=text, 
            reply_markup=reply_markup
        )
        return

async def remove_resource_from_task(update,context):
    query = update.callback_query
    await query.answer()
    message_id = query.message.id
    params = context.chat_data[message_id]
    task = Task.objects.get(message_id=message_id)
    log = ResourceLog.objects.get(id=params['log_id'])
    if query.data == 'this':
        log.delete()
    elif query.data == 'future':
        ResourceLog.objects.filter(
            task__parent=task.parent, 
            resource=log.resource,
            task__start__gte=task.start
        ).delete()
    params['resources'] = task.logs.filter(completed=False)
    await task_resource_message(query.message, params)
    return RESTART

async def edit_task_resource_amount(update,context):
    query = update.callback_query
    if query:
        await query.answer()
        message = query.message
        params = context.chat_data[message.id]
        task = Task.objects.get(id=params['task_id'])
        log = ResourceLog.objects.get(id=params['log_id'])
        if query.data == 'future':
            ResourceLog.objects.filter(
                task__parent = task.parent,
                task__start__gte=task.start,
                resource=log.resource
            ).update(quantity=params['amount'])
    else:
        message = update.message.reply_to_message
        params = context.chat_data[message.id]
        log = ResourceLog.objects.get(id=params['log_id'])
        params['amount'] = float(update.message.text)
        params['amount'] = abs(params['amount']) if log.quantity >= 0 else abs(params['amount']) * -1
        await update.message.delete()
        task = Task.objects.get(id=params['task_id'])
        factor = log.resource.get_conversion_factor()
        log.quantity = params['amount'] * factor if params['amount'] > 0 else params['amount']
        log.save()
        if task.parent.freq:
            text, reply_markup = freq_selection_message()
            await message.edit_text(text, reply_markup=reply_markup)
            return
    params['resources'] = task.logs.filter(completed=False)
    await task_resource_message(message, params)
    return RESTART

async def add_task_resource_amount(update, context):
    query = update.callback_query
    if query:
        await query.answer()
        message_id = query.message.id
        params = context.chat_data[message_id]
        task = Task.objects.get(message_id=message_id)
        if query.data == 'future':
            tasks = task.parent.tasks.filter(start__gt=task.start)
            res = Resource.objects.get(id=params['resource_id'])
            qty = params['amount'] * res.get_conversion_factor() if params['amount'] > 0 else params['amount']
            logs = [ResourceLog(
                task=t,
                resource=res,
                quantity=qty
            ) for t in tasks]
            ResourceLog.objects.bulk_create(logs)
        params['resources'] = Resource.objects.all()
        await task_resource_message(query.message, params)
        return RESTART
    message = update.message.reply_to_message
    params = context.chat_data[message.message_id]
    task = Task.objects.get(message_id=message.id)
    resource = Resource.objects.get(id=params['resource_id'])
    factor = resource.get_conversion_factor()
    increase = params['increase'] if params['increase'] < 0 else params['increase'] * factor
    params['amount'] = abs(float(update.message.text)) * increase
    await update.message.delete()
    ResourceLog.objects.create(
        task = task,
        resource = resource,
        quantity = params['amount']
    )
    if task.parent.freq:
        text, reply_markup = freq_selection_message()
        await message.edit_text(text, reply_markup=reply_markup)
        return
    params['resources'] = Resource.objects.all()
    await task_resource_message(message, params)
    return RESTART