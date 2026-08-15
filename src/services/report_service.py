import logging
from src.persistence.models import Task, User
from src.persistence.db import get_session
from src.core import timezone
from sqlalchemy import or_
from src.llm.mapper import to_task_response
from src.services.task_service import create_activity, complete_activity

logger = logging.getLogger(__name__)

def _create_report_activity(user_id, title, description):
    """Reports are shown as a regular activity card (title + description)
    instead of plain text, per product requirement. Immediately marked
    completed so it doesn't show up as an open task, and completed tasks are
    excluded from report queries so a report never lists itself."""
    created = create_activity({
        "user_id": user_id,
        "summary": title,
        "description": description,
    })
    complete_activity(created["id"])
    return created


def get_due_tasks():

    try:
        session = get_session()
        tasks = (
            session.query(Task)
            .join(User, Task.user_id == User.id)
            .filter(Task.next_date <= timezone.now().replace(tzinfo=None, microsecond=0))
            .filter(Task.completed == False)
            .filter(Task.notified == False)
            .filter(Task.archived == False)
            .filter(User.is_active == True)
            .order_by(Task.next_date)
            .all()
        )
        return tasks
    except Exception as e:
        session.rollback()
        logger.warning(f"Fetch due tasks error:{e}")
    finally:
        session.close()

def _get_activities_by_time(user_id, dtstart, dtend):
    """Unlike get_due_tasks (the reminder job), this deliberately does not
    filter on next_date <= now: a report should show everything in the
    requested window, including activities not due yet, so the user can get
    ahead of them. `notified == False` excludes activities already shown
    (via the job or a previous report) so nothing is repeated."""
    try:
        session = get_session()

        tasks = session.query(Task).filter(
            Task.user_id == user_id,
            Task.next_date >= dtstart,
            Task.next_date <= dtend,
            Task.completed == False,
            Task.notified == False,
        ).order_by(Task.next_date).all()

        return [to_task_response(task).model_dump() for task in tasks]

    except Exception as e:
        logger.warning(f"Search database error: {e}")
        raise

    finally:
        session.close()

def report_activities_by_time(args):
    """Returns a list of task dicts (each rendered as its own full card with
    buttons by the caller - see message_handlers._show_task_results), or an
    {"status": "error", ...} dict for an invalid report_type."""
    user_id = args.get('user_id')
    report_type = args.get('report_type')

    if report_type == "today":
        dtstart = timezone.now().replace(tzinfo=None)
        dtend = timezone.end_of_day()

    elif report_type == "tomorrow":
        dtstart = timezone.end_of_day()
        dtend = timezone.end_of_day(1)

    elif report_type == "this_week":
        dtstart = timezone.now().replace(tzinfo=None)
        dtend = timezone.end_of_week()

    else:
        return {"status": "error", "message": "نوع گزارش نامعتبره"}

    return _get_activities_by_time(user_id, dtstart, dtend)

def _get_report_by_summary(user_id, summary):
    try:
        session = get_session()
        tasks = session.query(Task).filter(
            Task.user_id == user_id,
            Task.summary.contains(summary),
            Task.completed == False
        ).order_by(Task.next_date).all()
        results = [{
            'task_id':task.id, 
            'summary':task.summary, 
            'next_date':timezone.human_readable(task.next_date)
            } for task in tasks]
        return results
    except Exception as e:
        logger.warning(f"Search database error:{e}")
        raise
    finally:
        session.close()

def report_activities_by_summary(args):
    user_id = args.get('user_id')
    summary_keyword = args.get('summary_keyword')
    try:
        results = _get_report_by_summary(user_id, summary_keyword)
        if results:
            description = '\n\n'.join(['\n'.join(
                [
                    f"عنوان فعالیت: *{result.get('summary')}*",
                    f"زمان انجام: *{result.get('next_date')}*"
                ]
            ) for result in results])
        else:
            description = "فعالیتی وجود نداره"

        title = f"گزارش فعالیت‌های مرتبط با «{summary_keyword}»"
        return _create_report_activity(user_id, title, description)
    except Exception as e:
        logger.warning(f"report_activities_by_summary error:{e}")
        raise

def get_activity_details_by_id(task_id):
    session = None
    try:
        session = get_session()
        task = session.query(Task).filter_by(id=task_id).one()
        return to_task_response(task).model_dump()
    except:
        raise
    finally:
        if session:
            session.close()

def get_activity_details_by_summary(args):
    session = get_session()
    try:
        user_id = args.get("user_id")
        activity_title = args.get("activity_title")
        task = session.query(Task).filter_by(
            user_id=user_id, 
            summary=activity_title
        ).first()
        return to_task_response(task).model_dump()
    finally:
        session.close()

def show_activities_details_by_titles(args): # user_id
    session = get_session()
    try:
        summaries = list({
            s.strip() for s in args.get("activity_titles", [])
            if s and s.strip()
        })

        if not summaries:
            return []

        filters = [
            Task.summary.ilike(f"%{summary}%")
            for summary in summaries
        ]

        tasks = (
            session.query(Task)
            .filter(or_(*filters))
            .all()
        )

        return [
            to_task_response(task).model_dump()
            for task in tasks
        ]

    finally:
        session.close()
