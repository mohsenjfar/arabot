import enum
from uuid import uuid4
from sqlalchemy import (
    Column, Integer, BigInteger, String, Boolean, 
    DateTime, Text, ForeignKey, Enum, func
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, backref
from .db import Base

# ۱. تعریف Enumها
class PlanType(enum.Enum):
    free = "free"
    monthly = "monthly"
    yearly = "yearly"
    pro = "pro"

class RoleEnum(enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class TransactionStatus(enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"

# ۲. مدل کاربر
class User(Base):
    __tablename__ = 'users'
    
    # استفاده از BigInteger برای تلگرام (بسیار مهم)
    id = Column(BigInteger, primary_key=True, autoincrement=False) 
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=True)
    phone_number = Column(String(20), nullable=True) # شماره تلفن باید String باشد
    
    plan = Column(Enum(PlanType), default=PlanType.free, nullable=False)
    is_active = Column(Boolean, default=True)
    is_allowed = Column(Boolean, default=True) # معمولا پیش‌فرض را True میگیرند مگر لیست سیاه داشته باشید
    is_subscribed = Column(Boolean, default=False)
    
    trial_messages_left = Column(Integer, default=20, nullable=False)
    subscription_expires_at = Column(DateTime(timezone=True), nullable=True)
    
    instructions = Column(Text, nullable=True) # System Prompt مختص کاربر
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # روابط (Relationships)
    usage_logs = relationship("UsageLog", back_populates="user", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("SubscriptionTransaction", back_populates="user")

# ۳. مدل لاگ مصرف (برای تحلیل هزینه)
class UsageLog(Base):
    __tablename__ = "usage_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    prompt_text = Column(Text, nullable=False)
    response_text = Column(Text, nullable=True)

    prompt_tokens = Column(Integer, default=0, nullable=False)
    completion_tokens = Column(Integer, default=0, nullable=False)
    total_tokens = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    user = relationship("User", back_populates="usage_logs")

# ۴. مدل تراکنش‌های مالی
class SubscriptionTransaction(Base):
    __tablename__ = "subscription_transactions"

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)

    plan = Column(Enum(PlanType), nullable=False)
    amount = Column(BigInteger, nullable=False) # مبالغ ریالی ممکن است از سقف Integer خارج شوند
    status = Column(Enum(TransactionStatus), default=TransactionStatus.PENDING, nullable=False)

    payment_ref = Column(String(128), nullable=True, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    paid_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="transactions")

# ۵. مدل پیام‌ها (تاریخچه چت)
class Message(Base):
    __tablename__ = 'messages'
    
    # استفاده از UUID واقعی برای پرفورمنس بهتر در ایندکس
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(BigInteger, ForeignKey('users.id', ondelete="CASCADE"), nullable=False, index=True)
    
    role = Column(Enum(RoleEnum), nullable=False, default=RoleEnum.USER)
    content = Column(Text, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship('User', back_populates='messages')
