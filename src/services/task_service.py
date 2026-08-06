import logging
from src.persistence.models import Task
from src.persistence.db import get_session
from src.core import timezone
from dateutil.rrule import rrulestr, rruleset
from datetime import datetime
from src.llm.mapper import to_task_response, to_task_orm_create, to_task_orm_update

logger = logging.getLogger(__name__)

def calculate_next_date(
    dtstart: datetime,
    rrule: str | None,
    exdate=None,
    rxdate=None,
):
    if not rrule:
        return dtstart, False

    try:
        rule = rrulestr(rrule, dtstart=dtstart)
        rs = rruleset()
        rs.rrule(rule)

        for dt in exdate or []:
            rs.exdate(timezone.str_to_datetime(dt))

        for dt in rxdate or []:
            rs.rdate(timezone.str_to_datetime(dt))

        next_date = rs.after(timezone.now().replace(tzinfo=None))

        if next_date is None:
            return None, False

        return next_date, True

    except Exception as e:
        logger.error(f"Invalid recurrence rule: {e}")
        raise ValueError(f"Invalid recurrence rule: {e}")

def create_activity(args):
    try:
        session = get_session()
        logger.info(args)
        data_validated = to_task_orm_create(args).model_dump()
        task = Task(**data_validated)
        session.add(task)
        session.commit()
        return to_task_response(task).model_dump()
    except Exception as e:
        logger.warning(f"Create activity error:{e}")
        session.rollback()
        raise
    finally:
        session.close()

def complete_activity(task_id):
    session = None

    try:
        session = get_session()
        task = session.query(Task).filter_by(id=task_id).one()

        if task.rrule:
            next_date, is_recurrent = calculate_next_date(
                task.dtstart,
                task.rrule,
                task.exdate,
                task.rxdate,
            )

            task.is_recurrent = is_recurrent

            if next_date:
                task.next_date = next_date
                task.notified = False
            else:
                task.next_date = None
                task.completed = True

        else:
            task.completed = True
            task.next_date = None

        session.commit()
        session.refresh(task)

        return f"{task.summary} با موفقیت انجام شد"

    except Exception as e:
        if session:
            session.rollback()

        logger.warning(f"Complete activity error: {e}")
        return f"خطا در انجام فعالیت: {e}"

    finally:
        if session:
            session.close()

def notification(task_id):
    try:
        session = get_session()
        task = session.query(Task).filter_by(id=task_id).one()
        task.notified = True
        session.add(task)
        session.commit()
    except Exception as e:
        session.rollback()
        logger.warning(f"Notification sent error:{e}")
    finally:
        session.close()

def clear_activity(task_id):
    try:
        session = get_session()
        task = session.query(Task).filter_by(id=task_id).one()
        task.notified = False
        session.add(task)
        session.commit()
        return f"{task.summary} با موفقیت پاک شد"
    except Exception as e:
        session.rollback()
        logger.warning(f"clear_activity error:{e}")
    finally:
        session.close()

def is_task_recurrent(task_id):
    session = None
    try:
        session = get_session()
        task = session.query(Task).filter_by(id=task_id).one()
        return task.is_recurrent
    except Exception as e:
        if session is not None:
            session.rollback()
        logger.warning(f"is_task_recurrent error: {e}")
        raise
    finally:
        if session is not None:
            session.close()

def skip_activity(task_id):
    session = None

    try:
        session = get_session()
        task = session.query(Task).filter_by(id=task_id).one()

        if not task.rrule:
            raise ValueError("Cannot skip a non-recurrent task")

        if not task.next_date:
            raise ValueError("Task has no upcoming occurrence to skip")

        exdates = task.exdate or []
        exdates.append(task.next_date.isoformat())
        task.exdate = exdates

        next_date, is_recurrent = calculate_next_date(
            task.dtstart,
            task.rrule,
            task.exdate,
            task.rxdate,
        )

        task.is_recurrent = is_recurrent

        if next_date:
            task.next_date = next_date
            task.notified = False
        else:
            task.next_date = None
            task.completed = True

        session.commit()
        session.refresh(task)

        return f"این نوبت از «{task.summary}» با موفقیت رد شد."

    except Exception as e:
        if session:
            session.rollback()
        logger.warning(f"skip_activity error: {e}")
        raise

    finally:
        if session:
            session.close()

def delete_activity(task_id):
    session = None
    try:
        session = get_session()
        session.query(Task).filter_by(id=task_id).delete(synchronize_session=False)
        session.commit()
    except Exception as e:
        if session is not None:
            session.rollback()
        logger.warning(f"delete_activity error: {e}")
        raise
    finally:
        if session is not None:
            session.close()

def skip_future_activities(task_id):
    session = None
    try:
        session = get_session()
        task = session.query(Task).filter_by(id=task_id).one()
        if task.is_recurrent:
            exdates = task.exdate or []
            exdates.append(task.next_date.isoformat())
            task.exdate = exdates
            task.rrule += f";UNTIL={timezone.datetime_to_ical(task.next_date)}"
            task.completed = True
            session.add(task)
            session.commit()
            return f"{task.summary} با موفقیت حذف شد"
        else:
            session.query(Task).filter_by(id=task_id).delete(synchronize_session=False)
        session.commit()
    except Exception as e:
        if session is not None:
            session.rollback()
        logger.warning(f"Delete task error: {e}")
        raise
    finally:
        if session is not None:
            session.close()

def update_activity(kwargs: dict):
    try:

        if len(kwargs) == 1:
            return {
                "status": "error",
                "message": "No fields provided for update"
            }

        session = get_session()

        task_id = kwargs.get("activity_id")
        task = session.query(Task).filter_by(id=task_id).first()

        if not task:
            raise ValueError("Task not found")

        data_validated = to_task_orm_update(kwargs).model_dump(exclude_unset=True)

        for key, value in data_validated.items():
            setattr(task, key, value)

        session.commit()
        session.refresh(task)

        return to_task_response(task).model_dump()

    except Exception as e:
        session.rollback()
        logger.error(f"update_activity error: {e}")
        return {"status": "error", "message": "خطا در ویرایش فعالیت. لطفا دوباره تلاش کن."}

    finally:
        session.close()