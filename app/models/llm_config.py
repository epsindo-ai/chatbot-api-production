from sqlalchemy import Column, Integer, String, Float, Boolean, Text, JSON, DateTime
from sqlalchemy.sql import func

from app.db.base_class import Base

class LLMConfig(Base):
    """Configuration for LLM models - Single configuration model"""
    __tablename__ = "llm_config"  # Changed from llm_configs to llm_config (singular)
    
    # Primary key will be fixed to 1
    id = Column(Integer, primary_key=True, default=1)
    name = Column(String, nullable=False)  # Name to identify the configuration
    model_name = Column(String, nullable=False)  # e.g., "gpt-3.5-turbo" or local model path
    temperature = Column(Float, default=0.7)
    top_p = Column(Float, default=1.0)
    max_tokens = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    extra_params = Column(JSON, nullable=True)  # For any additional parameters
    enable_thinking = Column(Boolean, default=False, nullable=False)  # New parameter for thinking capability
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    # Removed is_active field as it's not needed for a single config 