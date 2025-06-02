from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db import crud, models, schemas
from app.db.database import get_db
from app.config import settings
from app.utils.auth import get_admin_user

router = APIRouter(
    prefix="/api/llm-config",
    tags=["llm-config"],
)

@router.get("/", response_model=List[schemas.LLMConfig])
def get_all_llm_configs(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_admin_user)
):
    """Get all LLM configurations - Admin only"""
    return crud.get_all_llm_configs(db, skip=skip, limit=limit)

@router.get("/active", response_model=schemas.LLMConfig)
def get_active_llm_config(db: Session = Depends(get_db)):
    """Get the active LLM configuration"""
    config = crud.get_active_llm_config(db)
    if not config:
        raise HTTPException(status_code=404, detail="No active LLM configuration found")
    return config

@router.get("/{config_id}", response_model=schemas.LLMConfig)
def get_llm_config(
    config_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_admin_user)
):
    """Get a specific LLM configuration by ID - Admin only"""
    config = crud.get_llm_config(db, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return config

@router.post("/", response_model=schemas.LLMConfig, status_code=status.HTTP_201_CREATED)
def create_llm_config(
    config: schemas.LLMConfigCreate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_admin_user)
):
    """Create a new LLM configuration - Admin only"""
    if config.name:
        db_config = crud.get_llm_config_by_name(db, config.name)
        if db_config:
            raise HTTPException(status_code=400, detail="Configuration with this name already exists")
    return crud.create_llm_config(db, config)

@router.post("/from-env", response_model=schemas.LLMConfig, status_code=status.HTTP_201_CREATED)
def create_llm_config_from_env(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_admin_user)
):
    """Create or update LLM configuration from environment variables - Admin only"""
    # Check if config with name from env already exists
    db_config = crud.get_llm_config_by_name(db, settings.LLM_CONFIG_NAME)
    
    # Create config object from environment variables
    config = schemas.LLMConfigCreate(
        name=settings.LLM_CONFIG_NAME,
        model_name=settings.LLM_MODEL,
        temperature=settings.LLM_TEMPERATURE,
        top_p=settings.LLM_TOP_P,
        max_tokens=settings.LLM_MAX_TOKENS,
        presence_penalty=0.0,
        frequency_penalty=0.0,
        is_active=True,
        description="Configuration created from environment variables",
        extra_params={
            "base_url": settings.OPENAI_API_BASE,
            "api_key": settings.OPENAI_API_KEY
        }
    )
    
    # If config exists, update it
    if db_config:
        update_config = schemas.LLMConfigUpdate(
            name=config.name,
            model_name=config.model_name,
            temperature=config.temperature,
            top_p=config.top_p,
            max_tokens=config.max_tokens,
            presence_penalty=config.presence_penalty,
            frequency_penalty=config.frequency_penalty,
            is_active=config.is_active,
            description=config.description,
            extra_params=config.extra_params
        )
        return crud.update_llm_config(db, db_config.id, update_config)
    
    # Otherwise create new config
    return crud.create_llm_config(db, config)

@router.put("/{config_id}", response_model=schemas.LLMConfig)
def update_llm_config(
    config_id: int, 
    config: schemas.LLMConfigUpdate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_admin_user)
):
    """Update an existing LLM configuration - Admin only"""
    db_config = crud.get_llm_config(db, config_id)
    if not db_config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return crud.update_llm_config(db, config_id, config)

@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_llm_config(
    config_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_admin_user)
):
    """Delete an LLM configuration - Admin only"""
    db_config = crud.get_llm_config(db, config_id)
    if not db_config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    
    # Don't allow deleting the only config
    config_count = len(crud.get_all_llm_configs(db))
    if config_count <= 1:
        raise HTTPException(
            status_code=400, 
            detail="Cannot delete the only configuration. Create another one first."
        )
    
    # If this is the active config, we need to set another one as active
    if db_config.is_active:
        other_configs = crud.get_all_llm_configs(db)
        for cfg in other_configs:
            if cfg.id != config_id:
                # Set this config as active
                crud.update_llm_config(
                    db, 
                    cfg.id, 
                    schemas.LLMConfigUpdate(is_active=True)
                )
                break
    
    # Now delete the config
    crud.delete_llm_config(db, config_id)
    return None 