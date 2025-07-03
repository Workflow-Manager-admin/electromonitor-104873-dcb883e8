from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean, Text
from sqlalchemy.orm import relationship
from .database import Base

import datetime

# PUBLIC_INTERFACE
class Role(Base):
    """Database model for user roles (officer/customer)."""
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    # relationships
    users = relationship("User", back_populates="role")

# PUBLIC_INTERFACE
class User(Base):
    """Database model for users: officers or customers."""
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    full_name = Column(String(100))
    email = Column(String(100), unique=True)
    hashed_password = Column(String(200), nullable=False)
    is_active = Column(Boolean, default=True)
    role_id = Column(Integer, ForeignKey("roles.id"))
    # relationships
    role = relationship("Role", back_populates="users")
    usage = relationship("Usage", back_populates="user")
    bills = relationship("Bill", back_populates="user")
    notifications = relationship("Notification", back_populates="user")

# PUBLIC_INTERFACE
class Usage(Base):
    """Database model for storing individual usage records."""
    __tablename__ = "usage"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    reading_value = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    description = Column(Text)
    # relationships
    user = relationship("User", back_populates="usage")

# PUBLIC_INTERFACE
class Bill(Base):
    """Database model for usage bills/payments."""
    __tablename__ = "bills"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    usage_id = Column(Integer, ForeignKey("usage.id"))
    amount = Column(Float, nullable=False)
    due_date = Column(DateTime, nullable=False)
    status = Column(String(20), default="pending")  # pending/paid/overdue
    generated_at = Column(DateTime, default=datetime.datetime.utcnow)
    # relationships
    user = relationship("User", back_populates="bills")
    usage = relationship("Usage")
    notifications = relationship("Notification", back_populates="bill")

# PUBLIC_INTERFACE
class Notification(Base):
    """Database model for push/email notifications."""
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    bill_id = Column(Integer, ForeignKey("bills.id"), nullable=True)
    content = Column(Text, nullable=False)
    sent_at = Column(DateTime, default=datetime.datetime.utcnow)
    is_read = Column(Boolean, default=False)
    # relationships
    user = relationship("User", back_populates="notifications")
    bill = relationship("Bill", back_populates="notifications")
