# src/tasks/mapper.py

from .schemas import TaskResponse, TaskCreate, TaskUpdate
from src.core import timezone


def to_task_response(task) -> TaskResponse:
    return TaskResponse(
        id=str(task.id),
        user_id=task.user_id,
        summary=task.summary,
        dtstart=timezone.human_readable(task.dtstart) if task.dtstart else "",
        dtend=timezone.human_readable(task.dtend) if task.dtend else "",
        next_date=timezone.human_readable(task.next_date) if task.next_date else "",
        description=task.description,
        completed=task.completed,
        is_recurrent=task.is_recurrent,
        rrule_human=task.rrule_human if task.rrule_human else "",
        related_task_id=task.related_task_id
    )

def to_task_orm_create(args) -> TaskCreate:
    dtstart = args.get('dtstart') or timezone.now().replace(microsecond=0, tzinfo=None)
    return TaskCreate(
        user_id=args.get('user_id'),
        summary=args.get('summary'),
        dtstart=dtstart,
        next_date=dtstart,
        description=args.get('description'),
        is_recurrent=args.get('is_recurrent'),
        rrule=args.get('rrule'),
        rrule_human=args.get('rrule_human'),
        related_task_id=args.get('related_task_id'),
    )

def to_task_orm_update(kwargs) -> TaskUpdate:

    task_id = kwargs.get("activity_id")
    
    if not task_id:
        return {"status": "error", "message": "activity_id is required"}

    values_to_update = {"task_id": task_id}

    # Use `.get(key) is not None` rather than `key in kwargs`: the model
    # frequently emits the full function schema with null for fields it
    # doesn't intend to change, and a bare `in` check would wrongly treat
    # that as "clear this field" and overwrite it (e.g. wiping summary/dtstart).
    if kwargs.get("user_id") is not None:
        values_to_update["user_id"] = kwargs["user_id"]

    if kwargs.get("new_summary") is not None:
        values_to_update["summary"] = kwargs["new_summary"]

    if kwargs.get("new_dtstart") is not None:
        values_to_update["dtstart"] = kwargs["new_dtstart"]
        values_to_update["next_date"] = kwargs["new_dtstart"]

    if kwargs.get("new_description") is not None:
        values_to_update["description"] = kwargs["new_description"]

    if kwargs.get("make_recurrent") is not None:
        values_to_update["is_recurrent"] = kwargs["make_recurrent"]

    if kwargs.get("new_rrule") is not None:
        values_to_update["rrule"] = kwargs["new_rrule"]

    if kwargs.get("new_rrule_human") is not None:
        values_to_update["rrule_human"] = kwargs["new_rrule_human"]

    return TaskUpdate(**values_to_update)