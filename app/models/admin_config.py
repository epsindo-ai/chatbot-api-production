from sqlalchemy import Column, String, Integer, Boolean, JSON, DateTime, Text
from sqlalchemy.sql import func
from app.db.base_class import Base

class AdminConfig(Base):
    """
    Model to store all system configurations.
    This is a unified configuration store for all settings in the system.
    """
    __tablename__ = "admin_config"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False)
    value = Column(Text, nullable=True)  # Changed from String to Text to handle larger values
    value_type = Column(String, nullable=False, default="string")  # Type of value: string, int, float, boolean, json
    description = Column(String, nullable=True)
    category = Column(String, nullable=False, default="general")  # Category: llm, rag, general, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Common config keys as constants
    # LLM Config Keys
    KEY_LLM_MODEL = "llm_model"
    KEY_LLM_TEMPERATURE = "llm_temperature"
    KEY_LLM_TOP_P = "llm_top_p"
    KEY_LLM_MAX_TOKENS = "llm_max_tokens"
    
    # RAG Config Keys
    KEY_PREDEFINED_COLLECTION = "predefined_collection"
    KEY_RETRIEVER_TOP_K = "retriever_top_k"
    KEY_ALLOW_USER_UPLOADS = "allow_user_uploads"
    KEY_MAX_FILE_SIZE_MB = "max_file_size_mb"
    KEY_GLOBAL_COLLECTION_BEHAVIOR = "global_collection_behavior"  # auto_update or readonly_on_change
    KEY_GLOBAL_COLLECTION_RAG_PROMPT = "global_collection_rag_prompt"  # System prompt for global collection RAG
    KEY_USER_COLLECTION_RAG_PROMPT = "user_collection_rag_prompt"  # System prompt for user collection RAG
    KEY_REGULAR_CHAT_PROMPT = "regular_chat_prompt"  # System prompt for regular chat (non-RAG) 