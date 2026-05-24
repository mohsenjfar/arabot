from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Text,
    ForeignKey
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