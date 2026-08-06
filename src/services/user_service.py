import logging
from src.persistence.models import User, Message
from src.persistence.db import get_session

logger = logging.getLogger(__name__)


def user_exists(user_id):
    try:
        session = get_session()
        user = session.query(User).filter_by(id=user_id).one_or_none()
        return True if user else False
    
    except Exception as e:
        session.rollback()
        logger.warning(f"Error handeling user existence method:{e}")
    
    finally:
        session.close()

def insert_user(user_id, first_name, is_active=True, is_allowed=True):
    try:
        session = get_session()
        user = User(
            id=user_id,
            is_active=is_active,
            is_allowed=is_allowed,
            instructions=f"user first name:{first_name}\n"
        )
        session.add(user)
        session.commit()
        return user
    
    except Exception as e:
        session.rollback()
        logger.warning(f"Insert new user error:{e}")

    finally:
        session.close()

def user_allowed(user_id):
    try:
        session = get_session()
        user = session.query(User).filter_by(id=user_id).one_or_none()
        return user.is_allowed

    except Exception as e:
        session.rollback()
        logger.warning(f"Error handeling user allowed method:{e}")
    
    finally:
        session.close()

def is_first_time_user(user_id):
    session = None
    try:
        session = get_session()
        exists = (
            session.query(Message.id)
            .filter_by(user_id=user_id)
            .limit(1)
            .scalar()
        )
        return exists is None
    except Exception as e:
        if session:
            session.rollback()
        logger.warning(f"is_first_time_user error: {e}")
        return False
    finally:
        if session:
            session.close()

def deactivate_user(user_id):
    try:
        session = get_session()
        user = session.query(User).filter_by(id=user_id).one()
        user.is_active = False
        session.add(user)
        session.commit()
    except Exception as e:
        session.rollback()
        logger.warning(f"Deactivate user error:{e}")
    finally:
        session.close()

def activate_user(user_id):
    try:
        session = get_session()
        user = session.query(User).filter_by(id=user_id).one()
        user.is_active = True
        session.add(user)
        session.commit()
    except Exception as e:
        session.rollback()
        logger.warning(f"Activate user error:{e}")
    finally:
        session.close()

def update_user_instruction(user_id, instruction):
    try:
        session = get_session()
        user = session.query(User).filter_by(id=user_id).one()
        user.instructions += f"\n{instruction}"
        session.add(user)
        session.commit()
    except Exception as e:
        session.rollback()
        logger.warning(f"Update user instruction error:{e}")
        raise
    finally:
        session.close()

def get_user_instructions(user_id):
    try:
        session = get_session()
        user = session.query(User).filter_by(id=user_id).one()
        instructions = user.instructions
        session.close()
        return instructions
    except Exception as e:
        session.rollback()
        logger.warning(f"Fetch user instructions error:{e}")
    finally:
        session.close()

def keep_in_mind(args):
    try:
        what = args.get("what")
        user_id = args.get("user_id")
        update_user_instruction(user_id, what)
        return "اطلاعات با موفقیت به حافظه سپرده شد"
    except Exception as e:
        logger.warning(f"keep_in_mind error: {e}")
        raise
