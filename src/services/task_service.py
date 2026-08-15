import logging
from src.persistence.models import Task, TaskResource, ResourceLog
from src.persistence.db import get_session
from src.core import timezone
from dateutil.rrule import rrulestr, rruleset
from datetime import datetime, timedelta
from src.llm.mapper import to_task_response, to_task_orm_create, to_task_orm_update

logger = logging.getLogger(__name__)

# /timer has no dedicated column/flag on the row itself: a task is "a timer
# phase" purely by virtue of its rrule being one of these two. A row always
# describes the block that's *coming up next*, never the block in progress
# (see _next_timer_block) - delivery only ever happens through the
# background job once next_date is reached, there is no synchronous display.
TIMER_WORK = {
    "rrule": "FREQ=MINUTELY;INTERVAL=25",
    "summary": "💻 وقت شروع مجدد کاره",
    "rrule_human": "این فاز ۲۵ دقیقه‌ست",
}
TIMER_BREAK = {
    "rrule": "FREQ=MINUTELY;INTERVAL=5",
    "summary": "🍹 وقت استراحته",
    "rrule_human": "این فاز ۵ دقیقه‌ست",
}
TIMER_PHASE_MINUTES = {
    TIMER_WORK["rrule"]: 25,
    TIMER_BREAK["rrule"]: 5,
}

def _is_timer_rrule(rrule):
    return rrule in (TIMER_WORK["rrule"], TIMER_BREAK["rrule"])

def _current_timer_session(now):
    """Which phase is live *right now* on the fixed :00/:30 grid (each
    30-minute block is 25 minutes of work then 5 minutes of break), and the
    grid-aligned instant that block started."""
    block_start = now.replace(minute=0 if now.minute < 30 else 30, second=0, microsecond=0)
    minute_in_block = (now - block_start).total_seconds() / 60
    if minute_in_block >= 25:
        return TIMER_BREAK, block_start + timedelta(minutes=25)
    return TIMER_WORK, block_start

def _next_timer_block(now):
    """The block that immediately follows whichever one `now` falls into:
    the opposite phase, starting the instant the current block ends. Always
    recomputed fresh from the real clock (never from whatever was stored
    before), so a late ✔️/✖️ still lands on the correct upcoming block
    instead of drifting."""
    phase, block_start = _current_timer_session(now)
    next_start = block_start + timedelta(minutes=TIMER_PHASE_MINUTES[phase["rrule"]])
    next_phase = TIMER_BREAK if phase is TIMER_WORK else TIMER_WORK
    return next_phase, next_start

def _advance_timer_to_next_block(task, now):
    next_phase, next_start = _next_timer_block(now)
    task.rrule = next_phase["rrule"]
    task.summary = next_phase["summary"]
    task.rrule_human = next_phase["rrule_human"]
    task.next_date = next_start
    task.notified = False

def _apply_recurrence_advance(task):
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
        if args.get("activity_type") == "timer":
            now = timezone.now().replace(microsecond=0, tzinfo=None)
            next_phase, next_start = _next_timer_block(now)
            args = {**args, "dtstart": now, "is_recurrent": True, "next_date": next_start, **next_phase}
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
        completed_summary = task.summary
        # Captured before any of the branches below advance/clear next_date -
        # this is the occurrence actually being confirmed, and it's what
        # ResourceLog rows below get dated to.
        occurrence_date = task.next_date or task.dtstart

        if _is_timer_rrule(task.rrule):
            _advance_timer_to_next_block(task, timezone.now().replace(microsecond=0, tzinfo=None))
        elif task.rrule:
            _apply_recurrence_advance(task)
        else:
            task.completed = True
            task.next_date = None

        # A recurring Task is a single reused row, so linked resources can't
        # just flip a completed flag like the old per-occurrence design -
        # each confirm writes a fresh dated log instead (see TaskResource).
        links = session.query(TaskResource).filter_by(task_id=task.id).all()
        for link in links:
            session.add(ResourceLog(
                task_id=task.id,
                resource_id=link.resource_id,
                quantity=link.quantity,
                date=occurrence_date,
                created_at=timezone.now().replace(tzinfo=None),
            ))

        session.commit()
        session.refresh(task)

        return f"{completed_summary} با موفقیت انجام شد"

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
        skipped_summary = task.summary

        if _is_timer_rrule(task.rrule):
            _advance_timer_to_next_block(task, timezone.now().replace(microsecond=0, tzinfo=None))
            session.commit()
            session.refresh(task)
            return f"این نوبت از «{skipped_summary}» با موفقیت رد شد."

        if not task.rrule:
            raise ValueError("Cannot skip a non-recurrent task")

        if not task.next_date:
            raise ValueError("Task has no upcoming occurrence to skip")

        exdates = task.exdate or []
        exdates.append(task.next_date.isoformat())
        task.exdate = exdates

        _apply_recurrence_advance(task)

        session.commit()
        session.refresh(task)

        return f"این نوبت از «{skipped_summary}» با موفقیت رد شد."

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
        # Only reached when the task has no ResourceLog history (the caller
        # checks first), but it may still have unconfirmed TaskResource
        # template links - drop those too or the FK blocks the delete.
        session.query(TaskResource).filter_by(task_id=task_id).delete(synchronize_session=False)
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
    """Stops a task's recurrence without deleting the row - used instead of
    delete_activity whenever the task has ResourceLog history, since hard
    deleting it would orphan that history (and violate the FK). Recurring:
    excludes the pending occurrence and caps the rrule with UNTIL. Non
    recurrent: just freezes it as completed, same end state as a normal
    one-off confirm."""
    session = None
    try:
        session = get_session()
        task = session.query(Task).filter_by(id=task_id).one()
        if task.is_recurrent and task.next_date:
            exdates = task.exdate or []
            exdates.append(task.next_date.isoformat())
            task.exdate = exdates
            task.rrule += f";UNTIL={timezone.datetime_to_ical(task.next_date)}"

        task.completed = True
        task.next_date = None
        session.add(task)
        session.commit()
        return f"{task.summary} به‌خاطر سابقه‌ی مصرف منبع پاک نشد، فقط تکرارهای بعدیش متوقف شد"
    except Exception as e:
        if session is not None:
            session.rollback()
        logger.warning(f"Delete task error: {e}")
        raise
    finally:
        if session is not None:
            session.close()

def get_activity_datetime(task_id):
    """Raw (non-humanized) upcoming datetime for a task - seeds the manual
    📆 date-edit calendar picker, which needs an actual datetime object to
    convert to Jalali, not the human-readable string get_activity_details_by_id
    returns."""
    session = get_session()
    try:
        task = session.query(Task).filter_by(id=task_id).one()
        return task.next_date or task.dtstart
    finally:
        session.close()

_RRULE_FREQ_FA = {
    "MINUTELY": "دقیقه", "HOURLY": "ساعت", "DAILY": "روز",
    "WEEKLY": "هفته", "MONTHLY": "ماه", "YEARLY": "سال",
}

def describe_rrule(rrule: str) -> str:
    """Small non-LLM fallback for rrule_human when the manual 🔄 frequency
    editor is used - just describes plain FREQ/INTERVAL, falling back to the
    raw rrule text for anything fancier (BYDAY, COUNT, ...) that a bare
    "every N days" phrasing would misrepresent."""
    parts = dict(p.split("=", 1) for p in rrule.split(";") if "=" in p)
    unit = _RRULE_FREQ_FA.get(parts.get("FREQ"))
    extra_fields = set(parts) - {"FREQ", "INTERVAL"}
    if not unit or extra_fields:
        return rrule
    interval = parts.get("INTERVAL", "1")
    return f"هر {interval} {unit}"

def update_activity_frequency(task_id, rrule, rrule_human=None):
    """Called by both the 🔄 LLM-driven edit_activity path and (for disabling
    recurrence) update_activity: unlike update_activity/to_task_orm_update
    (which only ever touches dtstart when a caller explicitly moves it), a
    rrule change must also recompute next_date - otherwise the currently
    displayed occurrence stays whatever the OLD rule produced until the next
    confirm/skip. `rrule` empty/None disables recurrence entirely.
    `rrule_human` lets a caller (the LLM) supply its own phrasing; falls back
    to describe_rrule's crude FREQ/INTERVAL-only description otherwise."""
    session = get_session()
    try:
        task = session.query(Task).filter_by(id=task_id).one()

        if not rrule:
            task.rrule = None
            task.rrule_human = None
            task.is_recurrent = False
            task.completed = False
            task.next_date = task.dtstart
        else:
            task.rrule = rrule
            task.rrule_human = rrule_human or describe_rrule(rrule)
            _apply_recurrence_advance(task)

        session.commit()
        session.refresh(task)
        return to_task_response(task).model_dump()

    except Exception as e:
        session.rollback()
        logger.warning(f"update_activity_frequency error: {e}")
        return {"status": "error", "message": "خطا در ویرایش تکرار. لطفا دوباره تلاش کن."}

    finally:
        session.close()

def copy_activity(task_id):
    """🟠🔵 manual copy: a fresh Task row starting now, with the same
    summary/description/rrule and the same TaskResource template links (but
    obviously no ResourceLog history, since none has happened yet)."""
    session = get_session()
    try:
        task = session.query(Task).filter_by(id=task_id).one()
        args = {
            "user_id": task.user_id,
            "summary": task.summary,
            "description": task.description,
            "is_recurrent": task.is_recurrent,
            "rrule": task.rrule,
            "rrule_human": task.rrule_human,
        }
        links = [(l.resource_id, l.quantity) for l in session.query(TaskResource).filter_by(task_id=task_id).all()]
    finally:
        session.close()

    new_task = create_activity(args)

    if links:
        session = get_session()
        try:
            for resource_id, quantity in links:
                session.add(TaskResource(task_id=new_task["id"], resource_id=resource_id, quantity=quantity))
            session.commit()
        except Exception as e:
            session.rollback()
            logger.warning(f"copy_activity resource link error: {e}")
        finally:
            session.close()

    return new_task

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