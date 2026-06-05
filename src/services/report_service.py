import logging
from src.persistence.models import Task, User
from src.persistence.db import get_session
from src.core import timezone
from sqlalchemy import or_
from src.llm.mapper import to_task_response

logger = logging.getLogger(__name__)


def get_due_tasks():

    try:
        session = get_session()
        tasks = (
            session.query(Task)
            .join(User, Task.user_id == User.id)
            .filter(Task.next_date <= timezone.now().replace(tzinfo=None, microsecond=0))
            .filter(Task.completed == False)
            .filter(Task.notified == False)
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

def get_over_due_activities(user_id):
    try:
        session = get_session()

        dtstart = timezone.now().replace(tzinfo=None)

        tasks = session.query(Task).filter(
            Task.user_id == user_id,
            Task.next_date <= dtstart,
            Task.completed == False
        ).order_by(Task.next_date).all()

        results = [{
            'task_id': task.id,
            'summary': task.summary,
            'next_date': timezone.human_readable(task.next_date)
        } for task in tasks]

        return results

    except Exception as e:
        logger.warning(f"Search database error: {e}")
        return []

    finally:
        session.close()


def _get_report_by_time(user_id, dtstart, dtend):
    try:
        session = get_session()

        tasks = session.query(Task).filter(
            Task.user_id == user_id,
            Task.next_date >= dtstart,
            Task.next_date <= dtend
        ).order_by(Task.next_date).all()

        results = [{
            'task_id': task.id,
            'summary': task.summary,
            'next_date': timezone.human_readable(task.next_date)
        } for task in tasks]

        return results

    except Exception as e:
        logger.warning(f"Search database error: {e}")
        raise

    finally:
        session.close()

def report_activities_by_time(args):
    
    user_id = args.get('user_id')
    report_type = args.get('report_type')

    if report_type == "today":
        dtstart = timezone.now().replace(tzinfo=None)
        dtend = timezone.end_of_day()
        results = _get_report_by_time(user_id, dtstart, dtend)
    
    elif report_type == "tomorrow":
        dtstart = timezone.end_of_day()
        dtend = timezone.end_of_day(1)
        results = _get_report_by_time(user_id, dtstart, dtend)

    elif report_type == "the_day_after_tomorrow":
        dtstart = timezone.end_of_day(1)
        dtend = timezone.end_of_day(2)
        results = _get_report_by_time(user_id, dtstart, dtend)

    elif report_type == "this_week":
        dtstart = timezone.now().replace(tzinfo=None)
        dtend = timezone.end_of_week()
        results = _get_report_by_time(user_id, dtstart, dtend)

    elif report_type == "overdue_activities":
        results = get_over_due_activities(user_id)
    
    if results:
        return '\n\n'.join(['\n'.join(
            [
                f"عنوان فعالیت: *{result.get('summary')}*",
                f"زمان انجام: *{result.get('next_date')}*"
            ]
        ) for result in results])
    
    return "فعالیتی وجود نداره"

def _get_report_by_summary(user_id, summary):
    try:
        session = get_session()
        tasks = session.query(Task).filter(
            Task.user_id == user_id,
            Task.summary.contains(summary)
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
            return '\n\n'.join(['\n'.join(
                [
                    f"عنوان فعالیت: *{result.get('summary')}*",
                    f"زمان انجام: *{result.get('next_date')}*"
                ]
            ) for result in results])
        return "فعالیتی وجود نداره"
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
