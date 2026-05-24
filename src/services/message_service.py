import logging
from src.database.models import Message
from src.database.db import get_session
from src.commons import timezone

logger = logging.getLogger(__name__)

def insert_message(user_id, role, content):
    try:
        session = get_session()
        message = Message(
            user_id = user_id,
            created_at = timezone.now().replace(tzinfo=None, microsecond=0),
            role = role,
            content = content
        )
        session.add(message)
        session.commit()
        return message.id
    except Exception as e:
        session.rollback()
        logger.warning(f"Insert message error:{e}")
    finally:
        session.close()

def delete_message(message_id):
    session = None
    try:
        session = get_session()
        deleted_count = (
            session.query(Message)
            .filter_by(id=message_id)
            .delete(synchronize_session=False)
        )
        session.commit()
        return deleted_count
    except Exception as e:
        if session is not None:
            session.rollback()
        logger.warning(f"Delete message error: {e}")
        return 0
    finally:
        if session is not None:
            session.close()

def get_history(user_id, limit=5):
    try:
        session = get_session()
        records = (
            session.query(Message)
            .filter_by(user_id=user_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        return [{'role':record.role, 'content':record.content} for record in records][::-1] 
    except Exception as e:
        logger.warning(f"Fetch history error:{e}")
    finally:
        session.close()