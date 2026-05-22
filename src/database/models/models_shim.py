from django.db import models
import uuid
from django.utils import timezone
from django.db.models import Sum, Prefetch
from collections import defaultdict

class Project(models.Model):
    id = models.IntegerField(primary_key=True)
    title = models.CharField(max_length=100,null=True, blank=True)

    # def __str__(self):
    """Compatibility shim: expose SQLAlchemy models with a Django-like `.objects` manager

    This file exports the model names used elsewhere in the project (Project, Tag, Parent,
    Task, Resource, ResourceParity, ResourceLog, ResourcePrice) but implements them using
    SQLAlchemy models defined in `sqlalchemy_models.py` and provides a small Manager wrapper
    and some monkeypatches on SQLAlchemy Query to support a few commonly-used convenience
    methods (e.g. `order_by('-date')`, `.exists()`, `.last()`).
    """

    from sqlalchemy.orm import Query
    from sqlalchemy import desc, asc
    from .sqlalchemy_models import (
        Project as _Project,
        Tag as _Tag,
        Parent as _Parent,
        Task as _Task,
        Resource as _Resource,
        ResourceParity as _ResourceParity,
        ResourceLog as _ResourceLog,
        ResourcePrice as _ResourcePrice,
    )
    from ..db import get_session


    # --- Monkeypatch Query to accept simple string order_by and provide last/exists ---
    _orig_order_by = Query.order_by

    def _order_by(self, *criteria):
        new_criteria = []
        for c in criteria:
            if isinstance(c, str):
                if c.startswith('-'):
                    field = c[1:]
                    model = self._entity_zero().entity_zero.class_
                    col = getattr(model, field)
                    new_criteria.append(desc(col))
                else:
                    field = c
                    model = self._entity_zero().entity_zero.class_
                    col = getattr(model, field)
                    new_criteria.append(asc(col))
            else:
                new_criteria.append(c)
        return _orig_order_by(self, *new_criteria)

    def _last(self):
        try:
            return self.all()[-1]
        except Exception:
            return None

    def _exists(self):
        try:
            return self.count() > 0
        except Exception:
            return len(self.all()) > 0

    Query.order_by = _order_by
    Query.last = _last
    Query.exists = _exists


    # --- Manager wrapper ---
    class Manager:
        def __init__(self, model):
            self.model = model

        def _session(self):
            return get_session()

        def get(self, **kwargs):
            s = self._session()
            try:
                return s.query(self.model).filter_by(**kwargs).one()
            finally:
                s.close()

        def create(self, **kwargs):
            s = self._session()
            try:
                obj = self.model(**kwargs)
                s.add(obj)
                s.commit()
                s.refresh(obj)
                return obj
            finally:
                s.close()

        def filter(self, *args, **kwargs):
            s = self._session()
            q = s.query(self.model).filter(*args).filter_by(**kwargs)
            return q

        def all(self):
            s = self._session()
            try:
                return s.query(self.model).all()
            finally:
                s.close()


    # --- attach helper instance methods ---
    def _attach_helpers(cls):
        def save(self, session=None):
            s = session or get_session()
            try:
                s.add(self)
                s.commit()
                s.refresh(self)
            finally:
                if session is None:
                    s.close()

        def delete(self, session=None):
            s = session or get_session()
            try:
                s.delete(self)
                s.commit()
            finally:
                if session is None:
                    s.close()

        cls.save = save
        cls.delete = delete
        cls.objects = Manager(cls)


    # export names and attach helpers
    Project = _Project
    Tag = _Tag
    Parent = _Parent
    Task = _Task
    Resource = _Resource
    ResourceParity = _ResourceParity
    ResourceLog = _ResourceLog
    ResourcePrice = _ResourcePrice

    for _cls in (Project, Tag, Parent, Task, Resource, ResourceParity, ResourceLog, ResourcePrice):
        _attach_helpers(_cls)


    # --- add Task helper methods ported from the original Django model ---
    from sqlalchemy import func

    def _task_filter_related_logs(self, by='title', filter=''):
        logs = self.logs.filter(ResourceLog.quantity != None)
        # join resource to allow filtering by resource fields
        logs = logs.join(Resource)
        if by == 'title':
            logs = logs.filter(Resource.title.contains(filter))
        else:
            # filter by tag title
            logs = logs.join(Resource.tag).filter(Tag.title.contains(filter)).distinct()

        values = {
            "total_consumed_value": 0,
            "total_produced_value": 0,
            "items": []
        }

        for log in logs.all():
            item_id = log.id
            sign = "➖" if (log.quantity or 0) < 0 else "➕"
            sign += '✅' if log.completed else ''
            sign += '⛔' if log.skipped else ''
            title = log.resource.title
            parity_unit = log.resource.get_consumption_unit()
            conversion_factor = log.resource.get_conversion_factor()
            quantity = log.quantity or 0
            total = log.resource.total_available()
            latest_price_obj = log.resource.prices.order_by('-date').first()
            price = latest_price_obj.price if latest_price_obj else 0
            tags = ', '.join(tag.title for tag in log.resource.tag.all())

            if quantity <= 0:
                value = abs(int(float(quantity) / float(conversion_factor) * price)) if conversion_factor else 0
                if not log.skipped:
                    values["total_consumed_value"] += abs(value)
            elif quantity > 0:
                quantity /= conversion_factor if conversion_factor else 1
                value = int(float(quantity) * price)
                if not log.skipped:
                    values["total_produced_value"] += abs(value)

            values['items'].append({
                'item_id': item_id,
                'title': f"{sign} {abs(quantity):.2f} {parity_unit} {title}",
                'total': f"{total:.2f} {parity_unit}",
                'price': f"{int(value):,} تومان",
                'tags': tags
            })

        return values

    def _task_message(self):
        values = _task_filter_related_logs(self)
        total_consumed_value = int(values.get('total_consumed_value'))
        total_produced_value = int(values.get('total_produced_value'))
        description = f"\n💰 جمع ارزش منابع مصرف‌ شده: {total_consumed_value:,} تومان"
        description += f"\n💰 جمع ارزش منابع افزوده شده: {total_produced_value:,} تومان"
        return description

    Task.filter_related_logs = _task_filter_related_logs
    Task.message = _task_message
