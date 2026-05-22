from database.models.models_shim import Task
resource.task.task_resource_keyboards import (
    view_task_resources_keyboard,
    log_keyboard
)

async def task_resource_message(message, params):
    task = Task.objects.get(id=params['task_id'])
    await message.edit_text(
        task.message(), 
        reply_markup=view_task_resources_keyboard(message.id, task.id)
    )

def task_log_message(log):
    unit = log.resource.get_consumption_unit()
    task_id = log.task.id
    message_id = log.task.message_id
    balance = "کاهش" if log.quantity < 0 else "افزایش"
    lines = [
        f"عنوان: {log.resource.title}",
        f"مقدار: {balance} {abs(log.quantity)} {unit}"
    ]
    reply_markup = log_keyboard(message_id, task_id)
    return '\n'.join(lines), reply_markup
