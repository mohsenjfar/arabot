from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from datetime import datetime
from ..db import Base

# association table for Resource <-> Tag
resource_tag = Table(
    'resource_tag', Base.metadata,
    Column('resource_id', Integer, ForeignKey('resources.id'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id'), primary_key=True)
)

class Project(Base):
    __tablename__ = 'projects'
    id = Column(Integer, primary_key=True)
    title = Column(String(100), nullable=True)

class Tag(Base):
    __tablename__ = 'tags'
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=True)

    def __str__(self):
        return self.title or ''

class Parent(Base):
    __tablename__ = 'parents'
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('projects.id'))
    title = Column(String(100), nullable=True)
    freq = Column(String(100), nullable=True)
    project = relationship('Project')
    tasks = relationship('Task', back_populates='parent')

class Task(Base):
    __tablename__ = 'tasks'
    id = Column(String(100), primary_key=True, default=lambda: str(uuid.uuid4()))
    parent_id = Column(Integer, ForeignKey('parents.id'), nullable=True)
    message_id = Column(Integer, nullable=True)
    summary = Column(String(100), nullable=True)
    start = Column(DateTime, nullable=True)
    description = Column(String(300), nullable=True)
    completed = Column(Boolean, default=False)
    skipped = Column(Boolean, default=False)
    archived = Column(Boolean, default=False)

    parent = relationship('Parent', back_populates='tasks')
    logs = relationship('ResourceLog', back_populates='task', lazy='dynamic')

    def __str__(self):
        return self.summary or ''

class Resource(Base):
    __tablename__ = 'resources'
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=True)
    unit = Column(String(300), nullable=True)
    min_pantry = Column(Integer, default=0)

    tag = relationship('Tag', secondary=resource_tag, backref='resources', lazy='dynamic')
    prices = relationship('ResourcePrice', back_populates='resource', lazy='dynamic')
    parity = relationship('ResourceParity', uselist=False, back_populates='resource')
    logs = relationship('ResourceLog', back_populates='resource', lazy='dynamic')

    def total_available(self, session=None):
        # sum of completed logs quantities
        q = self.logs
        if session is not None and not hasattr(q, 'filter'):
            # fallback to query via session
            from sqlalchemy import select
            stmt = select(func.coalesce(func.sum(ResourceLog.quantity), 0)).where(
                ResourceLog.resource_id == self.id,
                ResourceLog.completed == True
            )
            return session.execute(stmt).scalar() or 0
        res = self.logs.filter_by(completed=True).with_entities(func.sum(ResourceLog.quantity)).first()
        return (res[0] or 0) if res else 0

    def has_parity(self):
        return self.parity is not None

    def get_consumption_unit(self):
        return self.parity.consumption_unit if self.has_parity() else self.unit

    def get_conversion_factor(self):
        return self.parity.conversion_factor if self.has_parity() else 1

    def __str__(self):
        return self.title or ''

class ResourceParity(Base):
    __tablename__ = 'resource_parities'
    id = Column(Integer, primary_key=True, autoincrement=True)
    resource_id = Column(Integer, ForeignKey('resources.id'))
    conversion_factor = Column(Float, nullable=True)
    consumption_unit = Column(String(300), nullable=True)

    resource = relationship('Resource', back_populates='parity')

    def __str__(self):
        return self.resource.title if self.resource else ''

class ResourceLog(Base):
    __tablename__ = 'resource_logs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(100), ForeignKey('tasks.id'), nullable=True)
    resource_id = Column(Integer, ForeignKey('resources.id'))
    quantity = Column(Float, nullable=True)
    completed = Column(Boolean, default=False)
    skipped = Column(Boolean, default=False)
    created = Column(DateTime, default=datetime.utcnow)
    modified = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    task = relationship('Task', back_populates='logs')
    resource = relationship('Resource', back_populates='logs')

    def __str__(self):
        return self.resource.title if self.resource else ''

class ResourcePrice(Base):
    __tablename__ = 'resource_prices'
    id = Column(Integer, primary_key=True, autoincrement=True)
    resource_id = Column(Integer, ForeignKey('resources.id'))
    price = Column(Integer, default=0)
    date = Column(DateTime, default=func.now())

    resource = relationship('Resource', back_populates='prices')

    def __str__(self):
        return self.resource.title if self.resource else ''
