from telegram import InlineQueryResultArticle, InputTextMessageContent
from database.models.models_shim import Task, Tag, Resource

async def inline_query(update, context):
    query_obj = update.inline_query
    q = query_obj.query
    offset = int(query_obj.offset or 0)

    if not q:
        return

    page_size = 30
    results = []

    def make_resource_result(resource, prev_id):
        resource_id = resource.id
        title = resource.title
        text_payload = f"__resource_selected__:{resource_id}:{prev_id}"
        input_message_content = InputTextMessageContent(text_payload)
        description = f"موجودی: {resource.total_available()} {resource.get_consumption_unit()}\n"
        description += f"تگ های مرتبط: {', '.join(t.title for t in resource.tag.all())}"
        return InlineQueryResultArticle(
            id=str(resource_id),
            title=title,
            input_message_content=input_message_content,
            description=description
        )

    items = []

    if q.startswith('resources_by_title:'):
        # inline-query encoded as: resources_by_title:<prev_msg_id>:<optinal:resource_title>
        parts = q.split(':', 2)
        prev_id = parts[1] if len(parts) > 1 else ''
        title = parts[2] if len(parts) > 2 else ''
        items = list(Resource.objects.filter(title__contains=title))

        for r in items[offset: offset + page_size]:
            results.append(make_resource_result(r, prev_id))

    elif q.startswith('resources_by_tag:'):
        parts = q.split(':', 2)
        prev_id = parts[1] if len(parts) > 1 else ''
        title = parts[2] if len(parts) > 2 else ''
        items = list(Resource.objects.filter(tag__title__contains=title).distinct())

        for r in items[offset: offset + page_size]:
            results.append(make_resource_result(r, prev_id))

    elif q.startswith('tags:'):
        parts = q.split(':', 2)
        prev_id = parts[1] if len(parts) > 1 else ''
        title = parts[2] if len(parts) > 2 else ''

        tags = Tag.objects.all()
        if title:
            tags = tags.filter(title__contains=title.strip())

        items = list(tags)

        for tag in items[offset: offset + page_size]:
            text_payload = f"__tag_selected__:{tag.id}:{prev_id}"
            results.append(
                InlineQueryResultArticle(
                    id=str(tag.id),
                    title=tag.title,
                    input_message_content=InputTextMessageContent(text_payload)
                )
            )

    elif q.startswith('archive:'):
        title = q.split(':', 1)[1]
        items = list(Task.objects.filter(summary__contains=title, archived=True))

        for task in items[offset: offset + page_size]:
            results.append(
                InlineQueryResultArticle(
                    id=str(task.id),
                    title=task.summary,
                    input_message_content=InputTextMessageContent(f"__task_selected__:{task.id}"),
                    description=task.description
                )
            )

    elif q.startswith('tasks_by_summary:'):
        parts = q.split(':', 2)
        prev_id = parts[1] if len(parts) > 1 else ''
        title = parts[2] if len(parts) > 2 else ''

        items = list(Task.objects.filter(summary__contains=title))

        for task in items[offset: offset + page_size]:
            text_payload = f"__task_selected__:{task.id}:{prev_id}"
            results.append(
                InlineQueryResultArticle(
                    id=f"t-{task.id}",
                    title=task.summary,
                    input_message_content=InputTextMessageContent(text_payload),
                    description=task.description
                )
            )
    
    elif q.startswith('task_resources_by_resource_title:'):
        # inline-query encoded as: task_resources_by_summary:<prev_msg_id>:<task_id>:<optinal:resource_title>
        parts = q.split(':')
        prev_id = parts[1]
        task_id = parts[2]
        resource_title = parts[3] if len(parts) > 3 else ''

        task = Task.objects.get(id=task_id)
        items = task.filter_related_logs(by='title', filter=resource_title).get('items')

        for item in items[offset: offset + page_size]:
            text_payload = f"__log_selected__:{prev_id}:{item.get('item_id')}"
            description = f"موجود: {item.get('total')}\n"
            description += f"ارزش: {item.get('price')}\n"
            description += f"تگ های مرتبط: {item.get('tags')}"
            results.append(
                InlineQueryResultArticle(
                    id=item.get('item_id'),
                    title=item.get('title'),
                    input_message_content=InputTextMessageContent(text_payload),
                    description=description
                )
            )

    elif q.startswith('task_resources_by_resource_tag:'):
        # inline-query encoded as: task_resources_by_tag:<prev_msg_id>:<task_id>:<optinal:resource_tag_title>
        parts = q.split(':')
        prev_id = parts[1]
        task_id = parts[2]
        tag_title = parts[3] if len(parts) > 3 else ''

        task = Task.objects.get(id=task_id)
        items = task.filter_related_logs(by='tag', filter=tag_title).get('items')

        for item in items[offset: offset + page_size]:
            text_payload = f"__log_selected__:{prev_id}:{item.get('item_id')}"
            description = f"موجود: {item.get('total')}\n"
            description += f"ارزش: {item.get('price')}\n"
            description += f"تگ های مرتبط: {item.get('tags')}"
            results.append(
                InlineQueryResultArticle(
                    id=item.get('item_id'),
                    title=item.get('title'),
                    input_message_content=InputTextMessageContent(text_payload),
                    description=description
                )
            )

    elif q.startswith('reduce:'):
        # inline-query encoded as: reduce:<prev_msg_id>:<task_id>:<optinal:resource_title>
        parts = q.split(':')
        prev_id = parts[1]
        task_id = parts[2]
        resource_title = parts[3] if len(parts) > 3 else ''

        items = Resource.objects.filter(title__contains=resource_title)

        for item in items[offset: offset + page_size]:
            text_payload = f"__resource_selected_to_reduce__:{prev_id}:{task_id}:{item.id}"
            description = f"موجود: {item.total_available()}\n"
            description += f"تگ های مرتبط: {', '.join(tag.title for tag in item.tag.all())}"
            results.append(
                InlineQueryResultArticle(
                    id=item.id,
                    title=item.title,
                    input_message_content=InputTextMessageContent(text_payload),
                    description=description
                )
            )

    elif q.startswith('increase:'):
        # inline-query encoded as: increase:<prev_msg_id>:<task_id>:<optinal:resource_title>
        parts = q.split(':')
        prev_id = parts[1]
        task_id = parts[2]
        resource_title = parts[3] if len(parts) > 3 else ''

        items = Resource.objects.filter(title__contains=resource_title)

        for item in items[offset: offset + page_size]:
            text_payload = f"__resource_selected_to_increase__:{prev_id}:{task_id}:{item.id}"
            description = f"موجود: {item.total_available()}\n"
            description += f"تگ های مرتبط: {', '.join(tag.title for tag in item.tag.all())}"
            results.append(
                InlineQueryResultArticle(
                    id=item.id,
                    title=item.title,
                    input_message_content=InputTextMessageContent(text_payload),
                    description=description
                )
            )

    has_more = len(items) > offset + page_size
    next_offset = str(offset + page_size) if has_more else ""

    await update.inline_query.answer(
        results,
        next_offset=next_offset,
        cache_time=1
    )
