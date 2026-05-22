from datetime import time, timedelta
from database.models.models_shim import Parent, Task, ResourceLog, Resource
from django.utils import timezone
from django.db.models import Sum
commons.commons_callbacks import task_view_message
from freqtrade_client import FtRestClient
from telegram.ext import ContextTypes

server_url = 'http://127.0.0.1:8080'
username = 'mohsen'
password = "40I3kDGz9_FJUHsnh2VlvlKn2pRUfzpCJQ"
client = FtRestClient(server_url, username, password)

async def run_repeated_jobs(context, func, interval, chat_id, first=1):
    context.job_queue.run_repeating(
        func, interval=interval, first=first, chat_id=chat_id, name=f"{func.__name__}_{chat_id}"
    )

async def scheduled_tasks(context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = context.job.chat_id
    tasks = Task.objects.filter(
        parent__project__id = abs(chat_id),
        message_id = None,
        start__lte = timezone.now(),
        archived = False,
        completed=False,
        skipped=False,
    ).order_by('start')
    for task in tasks:
        text, reply_markup = task_view_message(task)
        msg = await context.bot.send_message(chat_id, text=text, reply_markup=reply_markup)
        context.chat_data[msg.message_id] = {'task_id':task.id}
        task.message_id=msg.message_id
        task.save()

async def setup_scheduled_tasks(context, chat_id):
    context.job_queue.run_repeating(
        scheduled_tasks,
        interval=1,
        first=1,
        chat_id=chat_id,
        name=f"{scheduled_tasks.__name__}_{chat_id}"
    )

async def usdt_balance(context):
    currencies = client.balance().get('currencies')
    balance = [ticker.get("balance") for ticker in currencies if ticker.get('currency') == 'USDT'][0]
    ResourceLog.objects.filter(resource__title="تتر").update(quantity=balance)

async def update_usdt_balance(context, chat_id):
    context.job_queue.run_repeating(
        usdt_balance,
        interval=60,
        first=1,
        chat_id=chat_id,
        name=f"{usdt_balance.__name__}_{chat_id}"
    )

async def auto_shopping_list(context):
    ttime = timezone.now() + timedelta(days=7)
    now = timezone.now()
    resource_minimums = {
        resource.id: resource.min_pantry 
        for resource in Resource.objects.all()
    }
    current_inventory = (
        ResourceLog.objects
        .filter(task__start__lte=ttime)
        .values('resource_id')
        .annotate(current_quantity=Sum('quantity'))
    )
    consumed = []
    for entry in current_inventory:
        resource_id = entry['resource_id']
        current_qty = entry['current_quantity'] or 0
        min_qty = resource_minimums.get(resource_id, 0)
        
        if current_qty < min_qty:
            consumed.append({
                'resource_id': resource_id,
                'deficit': min_qty - current_qty
            })
    future_inventory = (
        ResourceLog.objects
        .filter(task__start__lte=ttime, task__completed=False)
        .values('resource_id')
        .annotate(future_quantity=Sum('quantity'))
    )
    produced = []
    for entry in future_inventory:
        resource_id = entry['resource_id']
        future_qty = entry['future_quantity'] or 0
        min_qty = resource_minimums.get(resource_id, 0)
        if future_qty > min_qty:
            produced.append({
                'resource_id': resource_id,
                'surplus': future_qty - min_qty
            })
    parent = Parent.objects.create(title='تعدیل منابع')
    task = Task.objects.create(parent=parent, summary="تعدیل منابع", start=now)
    logs = []
    for entry in consumed:
        resource = Resource.objects.get(id=entry['resource_id'])
        conversion_factor = resource.get_conversion_factor()
        deficit = entry['deficit']
        quantity = ((deficit + conversion_factor - 1) // conversion_factor) * conversion_factor
        logs.append(ResourceLog(
            task=task,
            resource_id=entry['resource_id'],
            quantity=quantity
        ))
    for entry in produced:
        logs.append(ResourceLog(
            task=task,
            resource_id=entry['resource_id'],
            quantity=-entry['surplus']
        ))
    ResourceLog.objects.bulk_create(logs)

async def auto_shopping_list(context):
    ttime = timezone.now() + timedelta(days=7)
    resource_minimums = {
        resource.id: resource.min_pantry 
        for resource in Resource.objects.all()
    }
    current_inventory = (
        ResourceLog.objects
        .filter(task__start__lte=ttime)
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
        .filter(task__start__lte=ttime, completed=False)
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

async def setup_weekly_shopping(context, chat_id):
    context.job_queue.run_daily(
        auto_shopping_list,
        time=time(hour=18, minute=30, second=0),
        days=(3,),
        name=f"weekly_backup_for_{chat_id}"
    )

async def setup_jobs(context, chat_id):
    await setup_scheduled_tasks(context, chat_id)
    # await update_usdt_balance(context, chat_id)
    await setup_weekly_shopping(context, chat_id)
