from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any
from sqlalchemy.orm import Session
import os

from app.utils.auth import get_admin_access, get_current_active_user
from app.db import schemas, crud, models
from app.db.database import get_db
from app.services.rag_config_service import RAGConfigService
from app.services.admin_config_service import AdminConfigService

router = APIRouter()

@router.get("/", response_model=schemas.LLMConfig)
async def get_llm_config(
    current_user: models.User = Depends(get_admin_access),
    db: Session = Depends(get_db)
):
    """
    Get the LLM configuration. Admin users only.
    If no config exists, a default one will be created.
    """
    config = crud.get_llm_config(db)
    
    if not config:
        config = crud.create_default_llm_config(db)
    
    return config

@router.get("/public", response_model=Dict[str, Any])
async def get_llm_config_public(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """
    Get a limited view of the LLM configuration for regular users.
    """
    config = crud.get_llm_config(db)
    
    if not config:
        config = crud.create_default_llm_config(db)
    
    # Return only the necessary fields for the client
    return {
        "model_name": config.model_name,
        "temperature": config.temperature,
        "top_p": config.top_p,
        "max_tokens": config.max_tokens,
        "enable_thinking": getattr(config, 'enable_thinking', False)
    }

@router.put("/", response_model=schemas.LLMConfig)
async def update_llm_config(
    config: schemas.LLMConfigUpdate,
    current_user: models.User = Depends(get_admin_access),
    db: Session = Depends(get_db)
):
    """
    Update the LLM configuration. Admin users only.
    """
    updated_config = crud.update_llm_config(db, config)
    if not updated_config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    
    return updated_config 