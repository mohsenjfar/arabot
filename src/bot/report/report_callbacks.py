from datetime import timedelta
from telegram import Update
from telegram.ext import ContextTypes
from database.models.models_shim import Parent, Task, Resource, ResourceLog
from django.utils import timezone
from django.db.models import Q, Sum
report.report_keyboards import report_keyboard
commons.common_keyboards import (
    calendar_keyboard,
    skip_keyboard
)
commons.commons_callbacks import (
    calendar_callback,
    time_callback,
    task_view_message
)

commons.constants import (
    REPORT, START, DUE, SUMMARY, UNTIL, END
)

async def report_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    message = query.message
    context.chat_data[message.id] = {}
    text = "Please select report type:"
    reply_markup = report_keyboard()
    await query.edit_message_text(text, reply_markup=reply_markup)
    return REPORT

async def report_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    message = query.message
    params = context.chat_data[message.id]
    if query.data in ['cancel', 'back']:
        del params
        await message.delete()
        return END
    elif query.data == 'task':
        params['time'] = timezone.now() + timedelta(hours=3.5)
        text = f"Please selected starting point: {params['time'].strftime('%x %X')}"
        reply_markup = calendar_keyboard(params['time'])
        await message.edit_text(text, reply_markup=reply_markup)
        return START
    elif query.data == 'purchase':
        params['time'] = timezone.now() + timedelta(hours=3.5)
        text = f"Please selected ending point: {params['time'].strftime('%x %X')}"
        reply_markup = calendar_keyboard(params['time'])
        await message.edit_text(text, reply_markup=reply_markup)
        return UNTIL

async def select_task_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()
        params = context.chat_data[query.message.id]
        if query.data in ['confirm', 'skip']:
            if timezone.is_naive(params['time']):
                params['time'] = timezone.make_aware(params['time'])
            params['start'] = params['time'] - timedelta(hours=3.5)
            params['time'] = timezone.now() + timedelta(hours=3.5)
            text = f"Please selected ending point: {params['time'].strftime('%x %X')}"
            reply_markup = calendar_keyboard(params['time'])
            await query.edit_message_text(text, reply_markup=reply_markup)
            return DUE
        else:
            await calendar_callback(update, context)
            return
    else:
        await time_callback(update, context)
        return

async def select_task_due(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()
        message = query.message
        params = context.chat_data[message.id]
        if query.data == 'confirm':
            if timezone.is_naive(params['time']):
                params['time'] = timezone.make_aware(params['time'])
            text = "Please enter summary or skip"
            reply_markup = skip_keyboard()
            await message.edit_text(text, reply_markup=reply_markup)
            return SUMMARY
        else:
            await calendar_callback(update, context)
            return
    else:
        await time_callback(update, context)
        return

async def task_report(update, context):
    query = update.callback_query
    if query:
        await query.answer()
        await query.message.delete()
        del params
    else:
        message = update.message.reply_to_message
        params = context.chat_data[message.id]
        chat_id = message.chat_id
        tasks = Task.objects.filter(
            start__gte=params['start'],
            start__lte=params['time'] - timedelta(hours=3.5)
        ).exclude(
            Q(start__lt=timezone.now()) &
            Q(completed=False) &
            Q(skipped=False)
        ).order_by('start')
        tasks = tasks.filter(summary__contains=update.message.text)
        await update.message.delete()
        await message.delete()
        del context.chat_data[message.id]
        for task in tasks:
            text, reply_markup = task_view_message(task)
            msg = await context.bot.send_message(chat_id, text=text, reply_markup=reply_markup)
            context.chat_data[msg.message_id] = {'task_id':task.id}
            task.message_id=msg.message_id
            task.save()
    return END

async def select_resource_balance_end(update, context):
    query = update.callback_query
    if query:
        await query.answer()
        message = query.message
        params = context.chat_data[message.id]
        if query.data == 'confirm':
            if timezone.is_naive(params['time']):
                params['time'] = timezone.make_aware(params['time'])
                await shopping_list(message, context)
            await message.delete()
            del params
            return END
        elif query.data == 'skip':
            await message.delete()
            del params
            return END
        else:
            await calendar_callback(update, context)
            return
    else:
        await time_callback(update, context)
        return

async def shopping_list(message, context):
    params = context.chat_data[message.id]
    resource_minimums = {
        resource.id: resource.min_pantry 
        for resource in Resource.objects.all()
    }
    current_inventory = (
        ResourceLog.objects
        .filter(task__start__lte=params['time'])
        .exclude(skipped=True)
        .values('resource_id')
        .annotate(current_quantity=Sum('quantity'))
    )
    entries = []
    for entry in current_inventory:
        resource_id = entry['resource_id']
        current_qty = entry['current_quantity'] or 0
        min_qty = resource_minimums.get(resource_id, 0)
        if current_qty < min_qty:
            entries.append({
                'resource_id': resource_id,
                'quantity': current_qty - min_qty
            })
    future_inventory = (
        ResourceLog.objects
        .filter(task__start__lte=params['time'], completed=False)
        .exclude(skipped=True)
        .values('resource_id')
        .annotate(future_quantity=Sum('quantity'))
    ).filter(future_quantity__gt=0)
    for entry in future_inventory:
        resource_id = entry['resource_id']
        future_qty = entry['future_quantity'] or 0
        entries.append({
            'resource_id': resource_id,
            'quantity': future_qty
        })
    parent = Parent.objects.create(title='تعدیل منابع')
    task = Task.objects.create(parent=parent, summary="تعدیل منابع", start=timezone.now())
    logs = []
    for entry in entries:
        logs.append(ResourceLog(
            task=task,
            resource_id=entry['resource_id'],
            quantity=-entry['quantity']
        ))
    ResourceLog.objects.bulk_create(logs)