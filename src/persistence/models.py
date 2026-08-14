from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    JSON,
    Float,
    Table,
)
import enum
from sqlalchemy.orm import relationship
from uuid import uuid4
from .db import Base

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, nullable=False)
    is_active = Column(Boolean, default=True)
    is_allowed = Column(Boolean, default=True)
    is_subscribed = Column(Boolean, default=False)
    instructions = Column(Text, nullable=True)

class RoleEnum(enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class Message(Base):
    __tablename__ = 'messages'
    id = Column(String(100), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, nullable=False)
    role = Column(String(10), nullable=True, default=RoleEnum.USER.value)
    content = Column(Text, nullable=False)

    user = relationship('User', backref='messages')

class Task(Base):
    __tablename__ = 'tasks'
    id = Column(String(100), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    summary = Column(String(100), nullable=False)
    dtstart = Column(DateTime(), nullable=False)
    dtend = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    next_date = Column(DateTime, nullable=True)
    exdate = Column(JSON, nullable=True)
    rxdate = Column(JSON, nullable=True)
    is_recurrent = Column(Boolean, default=False)
    rrule = Column(String(255), nullable=True)
    rrule_human = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    completed = Column(Boolean, default=False)
    notified = Column(Boolean, default=False)

    user = relationship('User', backref='tasks')

resource_tag = Table(
    'resource_tag', Base.metadata,
    Column('resource_id', Integer, ForeignKey('resources.id'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id'), primary_key=True),
)

class Tag(Base):
    __tablename__ = 'tags'
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)

class Resource(Base):
    __tablename__ = 'resources'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('users.id'), nullable=False)
    title = Column(String(200), nullable=False)
    unit = Column(String(100), nullable=True)
    min_pantry = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=True)

    user = relationship('User', backref='resources')
    tags = relationship('Tag', secondary=resource_tag, backref='resources')
    prices = relationship('ResourcePrice', back_populates='resource')
    parity = relationship('ResourceParity', uselist=False, back_populates='resource')
    logs = relationship('ResourceLog', back_populates='resource')

class ResourceParity(Base):
    """Optional unit conversion for a resource, e.g. bought/stored in kg but
    consumed/reported in a different unit (conversion_factor * stored_unit =
    consumption_unit)."""
    __tablename__ = 'resource_parities'
    id = Column(Integer, primary_key=True, autoincrement=True)
    resource_id = Column(Integer, ForeignKey('resources.id'), nullable=False, unique=True)
    conversion_factor = Column(Float, nullable=True)
    consumption_unit = Column(String(100), nullable=True)

    resource = relationship('Resource', back_populates='parity')

class ResourcePrice(Base):
    __tablename__ = 'resource_prices'
    id = Column(Integer, primary_key=True, autoincrement=True)
    resource_id = Column(Integer, ForeignKey('resources.id'), nullable=False)
    price = Column(Integer, nullable=True)
    date = Column(DateTime, nullable=True)

    resource = relationship('Resource', back_populates='prices')

class TaskResource(Base):
    """Template link, not history: says activity X moves `quantity` of
    resource Y every time it's confirmed. The actual dated transactions are
    ResourceLog rows, written fresh on each confirm (see
    task_service.complete_activity) - a recurring Task is a single reused
    row, so this can't just be a completed/skipped flag like the old
    per-occurrence design."""
    __tablename__ = 'task_resources'
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(100), ForeignKey('tasks.id'), nullable=False)
    resource_id = Column(Integer, ForeignKey('resources.id'), nullable=False)
    quantity = Column(Float, nullable=False)

    task = relationship('Task', backref='resource_links')
    resource = relationship('Resource')

class ResourceLog(Base):
    """One row per confirmed occurrence of a linked activity - the actual
    settled consumption/production history, dated to that occurrence."""
    __tablename__ = 'resource_logs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(100), ForeignKey('tasks.id'), nullable=False)
    resource_id = Column(Integer, ForeignKey('resources.id'), nullable=False)
    quantity = Column(Float, nullable=False)
    date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=True)

    task = relationship('Task', backref='resource_logs')
    resource = relationship('Resource', back_populates='logs')