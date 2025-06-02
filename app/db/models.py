from app.db.base_class import Base

# Import and register all models here
from app.models.user import User, UserRole
from app.models.chat_history import ChatHistory
from app.models.llm_config import LLMConfig
from app.models.admin_config import AdminConfig

# Define additional models that are not in separate files
from sqlalchemy import Boolean, Column, Integer, String, ForeignKey, DateTime, JSON, Text, Float, Enum, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

class ConversationType(enum.Enum):
    REGULAR = "regular"
    USER_FILES = "user_files"
    GLOBAL_COLLECTION = "global_collection"

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)  # For empty conversation expiry
    is_empty = Column(Boolean, default=True, nullable=False)  # Tracks if conversation has messages
    meta_data = Column(JSON, nullable=True)
    headline = Column(String(255), nullable=True, comment="Auto-generated headline for the conversation")
    conversation_type = Column(Enum(ConversationType), default=ConversationType.REGULAR, nullable=False)
    linked_global_collection_id = Column(Integer, ForeignKey("collections.id"), nullable=True)
    original_global_collection_name = Column(String, nullable=True, comment="Name of the global collection when conversation was initiated")
    display_file_id = Column(Integer, ForeignKey("file_storage.id"), nullable=True, comment="File to display in the chat panel")
    
    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete")
    files = relationship("FileStorage", back_populates="conversation", foreign_keys="[FileStorage.conversation_id]", cascade="all, delete")
    linked_global_collection = relationship("Collection", foreign_keys=[linked_global_collection_id])
    display_file = relationship("FileStorage", foreign_keys=[display_file_id])

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(String, ForeignKey("conversations.id", ondelete="CASCADE"))
    sequence_number = Column(Integer, nullable=False, comment="Per-conversation sequential counter starting from 1")
    role = Column(String, nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    rag_context = Column(Text, nullable=True, comment="Stores the retrieved context used for RAG responses")
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    
    __table_args__ = (
        UniqueConstraint('conversation_id', 'sequence_number', name='uq_message_conversation_sequence'),
    )

class FileStorage(Base):
    """Tracks uploaded files in the MinIO storage."""
    __tablename__ = "file_storage"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)  # Path in MinIO
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    file_metadata = Column(JSON, nullable=True)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="files")
    collection_files = relationship("CollectionFile", back_populates="file", cascade="all, delete")
    conversation = relationship("Conversation", back_populates="files", foreign_keys=[conversation_id])

class Collection(Base):
    """Collection of files used for RAG."""
    __tablename__ = "collections"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    is_admin_only = Column(Boolean, default=False)
    is_global_default = Column(Boolean, default=False)
    
    # Relationships
    user = relationship("User", back_populates="collections")
    collection_files = relationship("CollectionFile", back_populates="collection", cascade="all, delete")

class CollectionFile(Base):
    """Association table between Collection and FileStorage."""
    __tablename__ = "collection_files"
    
    id = Column(Integer, primary_key=True, index=True)
    collection_id = Column(Integer, ForeignKey("collections.id", ondelete="CASCADE"))
    file_id = Column(Integer, ForeignKey("file_storage.id", ondelete="CASCADE"))
    added_at = Column(DateTime(timezone=True), server_default=func.now())
    is_processed = Column(Boolean, default=False)
    
    # Relationships
    collection = relationship("Collection", back_populates="collection_files")
    file = relationship("FileStorage", back_populates="collection_files")
    
    # Unique constraint to prevent duplicate files in a collection
    __table_args__ = (
        UniqueConstraint('collection_id', 'file_id', name='uq_collection_file'),
    ) 