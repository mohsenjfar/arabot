import logging

from src.persistence.models import Resource, Tag, ResourcePrice, ResourceParity, TaskResource, ResourceLog
from src.persistence.db import get_session
from src.core import timezone

logger = logging.getLogger(__name__)


def create_resource(args):
    session = get_session()
    try:
        title = (args.get("title") or "").strip()
        if not title:
            return {"status": "error", "message": "عنوان منبع نمی‌تونه خالی باشه"}

        resource = Resource(
            user_id=args.get("user_id"),
            title=title,
            unit=args.get("unit"),
            min_pantry=args.get("min_pantry"),
            created_at=timezone.now().replace(tzinfo=None),
        )

        for tag_title in args.get("tags") or []:
            tag_title = tag_title.strip()
            if not tag_title:
                continue
            tag = session.query(Tag).filter_by(title=tag_title).first()
            if not tag:
                tag = Tag(title=tag_title)
                session.add(tag)
            resource.tags.append(tag)

        session.add(resource)
        session.flush()

        if args.get("price") is not None:
            session.add(ResourcePrice(
                resource_id=resource.id,
                price=args["price"],
                date=timezone.now().replace(tzinfo=None),
            ))

        if args.get("conversion_factor") is not None or args.get("consumption_unit") is not None:
            session.add(ResourceParity(
                resource_id=resource.id,
                conversion_factor=args.get("conversion_factor"),
                consumption_unit=args.get("consumption_unit"),
            ))

        session.commit()
        return {"status": "ok", "message": f"منبع «{title}» با موفقیت ثبت شد"}

    except Exception as e:
        session.rollback()
        logger.warning(f"create_resource error: {e}")
        return {"status": "error", "message": "خطا در ثبت منبع. لطفا دوباره تلاش کن."}

    finally:
        session.close()


def manage_task_resource(args):
    session = get_session()
    try:
        task_id = args.get("activity_id")
        user_id = args.get("user_id")
        resource_title = (args.get("resource_title") or "").strip()

        if not task_id or not resource_title:
            return {"status": "error", "message": "شناسه فعالیت و عنوان منبع لازمه"}

        resource = session.query(Resource).filter(
            Resource.user_id == user_id,
            Resource.title.contains(resource_title),
        ).first()

        if not resource:
            return {
                "status": "error",
                "message": f"منبعی با عنوان «{resource_title}» پیدا نشد. اول با /resource تعریفش کن.",
            }

        link = session.query(TaskResource).filter_by(task_id=task_id, resource_id=resource.id).first()

        if args.get("remove"):
            if link:
                session.delete(link)
                session.commit()
                return {"status": "ok", "message": f"منبع «{resource.title}» از این فعالیت جدا شد"}
            return {"status": "ok", "message": f"این فعالیت به «{resource.title}» وصل نبود"}

        quantity = args.get("quantity")
        if quantity is None:
            return {"status": "error", "message": "مقدار افزایش یا کاهش لازمه"}

        if link:
            link.quantity = quantity
        else:
            session.add(TaskResource(task_id=task_id, resource_id=resource.id, quantity=quantity))

        session.commit()
        direction = "افزایش" if quantity > 0 else "کاهش"
        return {
            "status": "ok",
            "message": f"از این به بعد با تایید این فعالیت، {abs(quantity)} {resource.unit or ''} {direction} «{resource.title}» ثبت می‌شه",
        }

    except Exception as e:
        session.rollback()
        logger.warning(f"manage_task_resource error: {e}")
        return {"status": "error", "message": "خطا در مدیریت منبع فعالیت. لطفا دوباره تلاش کن."}

    finally:
        session.close()


def search_resources(user_id, query_text="", limit=20):
    """Backs the 🔍 inline-query picker in the 🧺 flow - lets the user pick
    an existing resource by title instead of typing it out for the model to
    fuzzy-match."""
    session = get_session()
    try:
        q = session.query(Resource).filter(Resource.user_id == user_id)
        if query_text:
            q = q.filter(Resource.title.contains(query_text))
        resources = q.order_by(Resource.title).limit(limit).all()
        return [{"id": r.id, "title": r.title, "unit": r.unit} for r in resources]
    finally:
        session.close()


def get_resource_title(resource_id):
    session = get_session()
    try:
        resource = session.query(Resource).filter_by(id=resource_id).first()
        return resource.title if resource else None
    finally:
        session.close()


def task_has_resource_history(task_id):
    session = get_session()
    try:
        return session.query(ResourceLog.id).filter_by(task_id=task_id).first() is not None
    finally:
        session.close()


def list_task_resource_links(task_id):
    """Backs the manual 🧺 resource menu - both its text summary and the
    per-link ✖️ remove buttons, so it needs the resource id alongside the
    display fields (unlike the old LLM-seeded summary, which only needed
    text)."""
    session = get_session()
    try:
        links = session.query(TaskResource).filter_by(task_id=task_id).all()
        return [
            {
                "resource_id": link.resource_id,
                "title": link.resource.title,
                "unit": link.resource.unit or "",
                "quantity": link.quantity,
            }
            for link in links
        ]
    finally:
        session.close()


def link_task_resource_by_id(task_id, resource_id, quantity):
    """Manual (non-LLM) counterpart to manage_task_resource: called after the
    user picks an exact resource via the 🔍 inline-query picker, so there's
    no title to fuzzy-match - just create/update the template link."""
    session = get_session()
    try:
        link = session.query(TaskResource).filter_by(task_id=task_id, resource_id=resource_id).first()
        if link:
            link.quantity = quantity
        else:
            session.add(TaskResource(task_id=task_id, resource_id=resource_id, quantity=quantity))
        session.commit()
    except Exception as e:
        session.rollback()
        logger.warning(f"link_task_resource_by_id error: {e}")
        raise
    finally:
        session.close()


def unlink_task_resource_by_id(task_id, resource_id):
    session = get_session()
    try:
        session.query(TaskResource).filter_by(task_id=task_id, resource_id=resource_id).delete(synchronize_session=False)
        session.commit()
    except Exception as e:
        session.rollback()
        logger.warning(f"unlink_task_resource_by_id error: {e}")
        raise
    finally:
        session.close()
