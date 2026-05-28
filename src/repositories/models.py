from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    JSON,
    FLOAT
)
import enum
from sqlalchemy.orm import relationship
from uuid import uuid4
from .db import Base

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=True)
    phone_number = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    is_allowed = Column(Boolean, default=False)
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

class Resource:
    __tablename__ = 'resources'
    id = Column(String(100), primary_key=True, default=lambda: str(uuid4()))
    title = Column(String(100), nullable=False)

class AllocatedResource:
    __tablename__ = 'allocated_resources'
    id = Column(String(100), primary_key=True, default=lambda: str(uuid4()))
    task_id = Column(String(100), ForeignKey('tasks.id'), nullable=False)
    resource_id = Column(String(100), ForeignKey('resources.id'), nullable=False)
    amount = Column(FLOAT, nullable=False)

    task = relationship('Task', backref='allocated_resources')
    resource = relationship('Resource', backref='allocated_resources')

class UsedResource:
    __tablename__ = 'used_resources'
    id = Column(String(100), primary_key=True, default=lambda: str(uuid4()))
    task_id = Column(String(100), ForeignKey('tasks.id'), nullable=False)
    resource_id = Column(String(100), ForeignKey('resources.id'), nullable=False)
    created_at = Column(DateTime, nullable=False)
    amount = Column(FLOAT, nullable=False)

    task = relationship('Task', backref='used_resources')
    resource = relationship('Resource', backref='used_resources')

class ResourcePrice:
    __tablename__ = 'prices'
    id = Column(String(100), primary_key=True, default=lambda: str(uuid4()))
    resource_id = Column(String(100), ForeignKey('resources.id'), nullable=False)
    created_at = Column(DateTime, nullable=False)
    price = Column(Integer, nullable=False)

    resource = relationship('Resource', backref='prices')