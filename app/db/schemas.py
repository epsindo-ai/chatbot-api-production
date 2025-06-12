from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from enum import Enum

class UserRole(str, Enum):
    USER = "USER"
    ADMIN = "ADMIN"
    SUPER_ADMIN = "SUPER_ADMIN"

class ConversationType(str, Enum):
    REGULAR = "regular"
    USER_FILES = "user_files" 
    GLOBAL_COLLECTION = "global_collection"

# LLM Config schemas
class LLMConfigBase(BaseModel):
    name: str
    model_name: str
    temperature: float = 0.7
    top_p: float = 1.0
    max_tokens: Optional[int] = None
    description: Optional[str] = None
    extra_params: Optional[Dict[str, Any]] = None
    enable_thinking: bool = False  # New parameter for thinking capability

class LLMConfigCreate(LLMConfigBase):
    pass

class LLMConfigUpdate(BaseModel):
    name: Optional[str] = None
    model_name: Optional[str] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None
    description: Optional[str] = None
    extra_params: Optional[Dict[str, Any]] = None
    enable_thinking: Optional[bool] = None  # New parameter for thinking capability

class LLMConfig(LLMConfigBase):
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# User schemas
class UserBase(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    is_active: bool = True

class UserCreate(UserBase):
    password: str
    role: Optional[UserRole] = UserRole.USER  # Default to USER role

class UserLogin(BaseModel):
    username: str
    password: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None

class User(UserBase):
    id: int
    role: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class UserInDB(UserBase):
    id: int
    hashed_password: str
    
    class Config:
        from_attributes = True

class UserInfo(BaseModel):
    """Schema for user information returned by the /me endpoint"""
    user_id: int
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: str
    is_active: bool = True

# Admin user management schemas
class AdminUserCreate(BaseModel):
    """Schema for admin creating a new user account with temporary password"""
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[UserRole] = UserRole.USER
    temporary_password: str
    password_expires_hours: Optional[int] = 24  # Default 24 hours for temp password

class AdminPasswordReset(BaseModel):
    """Schema for admin resetting a user's password"""
    user_id: int
    temporary_password: str
    password_expires_hours: Optional[int] = 24

class PasswordChangeRequest(BaseModel):
    """Schema for user changing their password from temporary to permanent"""
    current_password: str
    new_password: str
    confirm_password: str

class UserCreateResponse(BaseModel):
    """Response schema for admin user creation"""
    user_id: int
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: str
    is_active: bool
    temporary_password: str
    password_expires_at: datetime
    must_reset_password: bool

class PasswordResetResponse(BaseModel):
    """Response schema for password reset"""
    user_id: int
    username: str
    temporary_password: str
    password_expires_at: datetime
    message: str

# Token schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class UserLoginResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: UserRole
    expires_in: int  # in seconds
    is_active: Optional[bool] = True
    must_reset_password: Optional[bool] = False
    is_temporary_password: Optional[bool] = False
    temp_password_expires_at: Optional[str] = None

# Message schemas
class MessageBase(BaseModel):
    role: str
    content: str

class MessageCreate(MessageBase):
    conversation_id: str
    rag_context: Optional[str] = None

class Message(MessageBase):
    id: int
    conversation_id: str
    sequence_number: int
    timestamp: datetime
    rag_context: Optional[str] = None
    
    class Config:
        from_attributes = True

# Conversation schemas
class ConversationBase(BaseModel):
    meta_data: Optional[dict] = None
    headline: Optional[str] = None
    conversation_type: Optional[ConversationType] = ConversationType.REGULAR
    display_file_id: Optional[int] = None

class ConversationCreate(ConversationBase):
    user_id: int
    linked_global_collection_id: Optional[int] = None
    original_global_collection_name: Optional[str] = None

class Conversation(ConversationBase):
    id: str
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None  # Added for empty conversation expiry
    is_empty: bool = True  # Added to track if conversation has messages
    linked_global_collection_id: Optional[int] = None
    original_global_collection_name: Optional[str] = None
    
    class Config:
        from_attributes = True

class ConversationWithMessages(Conversation):
    messages: List["Message"] = []
    
    class Config:
        from_attributes = True

# Move ConversationWithFiles after FileStorage is defined
# It will be added later in the file

# Chat request/response schemas
class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    meta_data: Optional[dict] = None

class UnifiedChatRequest(BaseModel):
    """Simplified unified schema for chat - collections and files are auto-bound."""
    message: str
    conversation_id: Optional[str] = None
    meta_data: Optional[dict] = None

class ChatResponse(BaseModel):
    status_code: int = 200
    error: Optional[str] = None
    response: str
    conversation_id: str
    meta_data: Optional[dict] = None
    
class UnifiedChatResponse(ChatResponse):
    """Unified response schema for both regular chat and RAG chat."""
    used_rag: bool = False

class StreamingChatResponse(BaseModel):
    """Response model for a single chunk in a streaming response"""
    content: str
    conversation_id: str
    error: Optional[str] = None
    finished: bool = False

# New schema for initiate conversation response
class ConversationInitiateResponse(BaseModel):
    conversation_id: str
    expires_at: Optional[datetime] = None

# RAG-specific schemas
class RagChatRequest(BaseModel):
    """Request schema for RAG chat"""
    message: str
    collection_name: str
    conversation_id: Optional[str] = None
    meta_data: Optional[Dict[str, Any]] = None

class ConversationRagChatRequest(BaseModel):
    """Request schema for conversation-based RAG chat"""
    message: str
    conversation_id: str
    meta_data: Optional[Dict[str, Any]] = None

class RagChatResponse(BaseModel):
    """Response schema for RAG chat"""
    response: str
    conversation_id: str
    collection_name: str
    meta_data: Optional[Dict[str, Any]] = None

class StreamingRagChatResponse(BaseModel):
    """Response model for a single chunk in a streaming RAG response"""
    content: str
    conversation_id: str
    collection_name: str
    error: Optional[str] = None
    finished: bool = False
    
class CollectionInfo(BaseModel):
    """Information about a vector store collection"""
    name: str
    description: Optional[str] = None
    document_count: Optional[int] = None
    is_admin_only: bool = False
    
class CollectionsResponse(BaseModel):
    """Response model for listing available collections"""
    collections: List[CollectionInfo]

# Document ingestion schemas
class TextIngestionRequest(BaseModel):
    text: str
    collection_name: str
    metadata: Optional[Dict[str, Any]] = None

class CollectionCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None

# File Storage schemas
class FileStorageBase(BaseModel):
    """Base schema for file storage"""
    filename: str
    original_filename: str
    file_path: str
    file_size: int
    mime_type: str
    file_metadata: Optional[Dict[str, Any]] = None
    conversation_id: Optional[str] = None

class FileStorageCreate(FileStorageBase):
    """Schema for creating a file storage record"""
    user_id: int

class FileStorageUpdate(BaseModel):
    """Schema for updating a file storage record"""
    filename: Optional[str] = None
    file_metadata: Optional[Dict[str, Any]] = None

class FileStorage(FileStorageBase):
    """Schema for a file storage record"""
    id: int
    user_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class FileStorageResponse(FileStorage):
    """Response schema for file storage with additional fields"""
    download_url: Optional[str] = None

# Add ConversationWithFiles here after FileStorage is defined
class ConversationWithFiles(Conversation):
    """Schema for a conversation with its files"""
    files: List[FileStorage] = []
    
    class Config:
        from_attributes = True

# Collection schemas
class CollectionBase(BaseModel):
    """Base schema for collection"""
    name: str
    description: Optional[str] = None
    is_active: bool = True
    is_admin_only: bool = False
    is_global_default: bool = False

class CollectionCreate(CollectionBase):
    """Schema for creating a collection"""
    user_id: int

class CollectionUpdate(BaseModel):
    """Schema for updating a collection"""
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    is_admin_only: Optional[bool] = None
    is_global_default: Optional[bool] = None

class Collection(CollectionBase):
    """Schema for a collection"""
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# CollectionFile schemas
class CollectionFileBase(BaseModel):
    """Base schema for collection file association"""
    collection_id: int
    file_id: int

class CollectionFileCreate(CollectionFileBase):
    """Schema for creating a collection file association"""
    pass

class CollectionFileUpdate(BaseModel):
    """Schema for updating a collection file association"""
    is_processed: Optional[bool] = None

class CollectionFile(CollectionFileBase):
    """Schema for a collection file association"""
    id: int
    added_at: datetime
    is_processed: bool
    
    class Config:
        from_attributes = True

class CollectionWithFiles(Collection):
    """Schema for a collection with its files"""
    files: List[FileStorage] = []
    
    class Config:
        from_attributes = True

# Collection management schemas
class AddFileToCollectionRequest(BaseModel):
    collection_id: str
    file_ids: List[str]

class RemoveFileFromCollectionRequest(BaseModel):
    collection_id: str
    file_id: str

# Text content schema
class TextContent(BaseModel):
    """Schema for text content to be added to a collection"""
    text: str
    metadata: Optional[Dict[str, Any]] = None
