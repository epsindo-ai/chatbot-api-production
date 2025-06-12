from sqlalchemy import Column, Integer, String, Boolean, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy import DateTime
import enum

from app.db.base_class import Base

class UserRole(enum.Enum):
    USER = "USER"
    ADMIN = "ADMIN"
    SUPER_ADMIN = "SUPER_ADMIN"

class User(Base):
    """User model for authentication and authorization"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True, nullable=True)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    role = Column(Enum(UserRole), default=UserRole.USER)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # One-time password fields for admin-managed account creation and resets
    is_temporary_password = Column(Boolean, default=False, nullable=False)
    temp_password_expires_at = Column(DateTime(timezone=True), nullable=True)
    must_reset_password = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    conversations = relationship("Conversation", back_populates="user")
    files = relationship("FileStorage", back_populates="user")
    collections = relationship("Collection", back_populates="user") 