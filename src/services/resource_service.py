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
        return {"status": "ok", "message": f"منبع «{title}» با موفقیت ثبت شد", "id": resource.id}

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


def get_resource_details(resource_id):
    """Backs the manual /resource details view (title/unit/min_pantry/tags/parity),
    the resource-side counterpart of report_service.get_activity_details_by_id."""
    session = get_session()
    try:
        resource = session.query(Resource).filter_by(id=resource_id).first()
        if not resource:
            return None
        return {
            "id": resource.id,
            "title": resource.title,
            "unit": resource.unit,
            "min_pantry": resource.min_pantry,
            "tags": [tag.title for tag in resource.tags],
            "consumption_unit": resource.parity.consumption_unit if resource.parity else None,
            "conversion_factor": resource.parity.conversion_factor if resource.parity else None,
        }
    finally:
        session.close()


def update_resource_unit(resource_id, unit):
    session = get_session()
    try:
        session.query(Resource).filter_by(id=resource_id).update({"unit": unit})
        session.commit()
    except Exception as e:
        session.rollback()
        logger.warning(f"update_resource_unit error: {e}")
        raise
    finally:
        session.close()


def update_resource_min_pantry(resource_id, min_pantry):
    session = get_session()
    try:
        session.query(Resource).filter_by(id=resource_id).update({"min_pantry": min_pantry})
        session.commit()
    except Exception as e:
        session.rollback()
        logger.warning(f"update_resource_min_pantry error: {e}")
        raise
    finally:
        session.close()


def list_resource_prices(resource_id, limit=5):
    session = get_session()
    try:
        prices = (
            session.query(ResourcePrice)
            .filter_by(resource_id=resource_id)
            .order_by(ResourcePrice.date.desc())
            .limit(limit)
            .all()
        )
        return [
            {"price": p.price, "date": timezone.human_readable(p.date) if p.date else ""}
            for p in prices
        ]
    finally:
        session.close()


def add_resource_price(resource_id, price):
    session = get_session()
    try:
        session.add(ResourcePrice(resource_id=resource_id, price=price, date=timezone.now().replace(tzinfo=None)))
        session.commit()
    except Exception as e:
        session.rollback()
        logger.warning(f"add_resource_price error: {e}")
        raise
    finally:
        session.close()


def delete_latest_resource_price(resource_id):
    session = get_session()
    try:
        latest = (
            session.query(ResourcePrice)
            .filter_by(resource_id=resource_id)
            .order_by(ResourcePrice.date.desc())
            .first()
        )
        if latest:
            session.delete(latest)
            session.commit()
    except Exception as e:
        session.rollback()
        logger.warning(f"delete_latest_resource_price error: {e}")
        raise
    finally:
        session.close()


def set_resource_parity(resource_id, consumption_unit, conversion_factor):
    session = get_session()
    try:
        parity = session.query(ResourceParity).filter_by(resource_id=resource_id).first()
        if parity:
            parity.consumption_unit = consumption_unit
            parity.conversion_factor = conversion_factor
        else:
            session.add(ResourceParity(
                resource_id=resource_id,
                consumption_unit=consumption_unit,
                conversion_factor=conversion_factor,
            ))
        session.commit()
    except Exception as e:
        session.rollback()
        logger.warning(f"set_resource_parity error: {e}")
        raise
    finally:
        session.close()


def search_tags(query_text="", limit=20):
    """Backs the 🔍 inline-query tag picker in both the 🗂️ resource-tag view
    (toggle on a resource) and /tags (pick one to rename/delete). Tags are
    global (no user_id), same as the legacy bot."""
    session = get_session()
    try:
        q = session.query(Tag)
        if query_text:
            q = q.filter(Tag.title.contains(query_text))
        tags = q.order_by(Tag.title).limit(limit).all()
        return [{"id": t.id, "title": t.title} for t in tags]
    finally:
        session.close()


def get_tag_title(tag_id):
    session = get_session()
    try:
        tag = session.query(Tag).filter_by(id=tag_id).first()
        return tag.title if tag else None
    finally:
        session.close()


def create_tag(title):
    """Backs the ➕ step of /tags - get-or-create by title (not linked to any
    resource), unlike add_new_resource_tag which also links it to one."""
    session = get_session()
    try:
        title = title.strip()
        tag = session.query(Tag).filter_by(title=title).first()
        if not tag:
            tag = Tag(title=title)
            session.add(tag)
        session.commit()
        session.refresh(tag)
        return tag.id
    except Exception as e:
        session.rollback()
        logger.warning(f"create_tag error: {e}")
        raise
    finally:
        session.close()


def rename_tag(tag_id, new_title):
    session = get_session()
    try:
        session.query(Tag).filter_by(id=tag_id).update({"title": new_title})
        session.commit()
    except Exception as e:
        session.rollback()
        logger.warning(f"rename_tag error: {e}")
        raise
    finally:
        session.close()


def delete_tag(tag_id):
    """Immediate delete, no confirm step - matches the legacy bot's
    edit_tag_query_callbacks exactly. Clears the resource_tag association
    rows first (via the Tag.resources backref) so the delete doesn't
    violate the secondary table's FKs."""
    session = get_session()
    try:
        tag = session.query(Tag).filter_by(id=tag_id).first()
        if tag:
            tag.resources = []
            session.flush()
            session.delete(tag)
        session.commit()
    except Exception as e:
        session.rollback()
        logger.warning(f"delete_tag error: {e}")
        raise
    finally:
        session.close()


def toggle_resource_tag(resource_id, tag_id):
    """Adds the tag if the resource doesn't have it yet, removes it if it
    does - matching the legacy bot's tap-to-toggle tag picker."""
    session = get_session()
    try:
        resource = session.query(Resource).filter_by(id=resource_id).one()
        tag = session.query(Tag).filter_by(id=tag_id).one()
        added = tag not in resource.tags
        if added:
            resource.tags.append(tag)
        else:
            resource.tags.remove(tag)
        session.commit()
        return added
    except Exception as e:
        session.rollback()
        logger.warning(f"toggle_resource_tag error: {e}")
        raise
    finally:
        session.close()


def add_new_resource_tag(resource_id, title):
    """Typing a tag title (instead of picking one via 🔍) creates it - get-or-create
    by title, same as create_resource's inline tag handling - and links it."""
    session = get_session()
    try:
        resource = session.query(Resource).filter_by(id=resource_id).one()
        title = title.strip()
        tag = session.query(Tag).filter_by(title=title).first()
        if not tag:
            tag = Tag(title=title)
            session.add(tag)
        if tag not in resource.tags:
            resource.tags.append(tag)
        session.commit()
    except Exception as e:
        session.rollback()
        logger.warning(f"add_new_resource_tag error: {e}")
        raise
    finally:
        session.close()


def delete_resource(resource_id):
    """Hard delete - matches the legacy bot exactly (confirmed with mohsen):
    unlike activities, a resource with ResourceLog history is NOT frozen,
    it's fully removed along with that history. Cascades child rows first
    since none of the FKs are ON DELETE CASCADE."""
    session = get_session()
    try:
        session.query(ResourceLog).filter_by(resource_id=resource_id).delete(synchronize_session=False)
        session.query(TaskResource).filter_by(resource_id=resource_id).delete(synchronize_session=False)
        session.query(ResourcePrice).filter_by(resource_id=resource_id).delete(synchronize_session=False)
        session.query(ResourceParity).filter_by(resource_id=resource_id).delete(synchronize_session=False)
        resource = session.query(Resource).filter_by(id=resource_id).first()
        if resource:
            resource.tags = []
            session.flush()
            session.delete(resource)
        session.commit()
    except Exception as e:
        session.rollback()
        logger.warning(f"delete_resource error: {e}")
        raise
    finally:
        session.close()
