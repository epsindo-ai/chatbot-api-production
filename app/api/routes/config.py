from fastapi import APIRouter, Depends, HTTPException, status, Body
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import os
import logging

from app.utils.auth import get_admin_access, get_current_active_user
from app.db import schemas, crud, models
from app.db.database import get_db
from app.services.admin_config_service import AdminConfigService
from app.models.admin_config import AdminConfig
from app.config import settings

router = APIRouter()

@router.get("/", response_model=Dict[str, Any])
async def get_unified_config(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """
    Get unified configuration including both LLM and RAG settings.
    This combines data from both the LLM config table and admin config table.
    """
    # Get LLM config
    try:
        llm_config = crud.get_llm_config(db)
        if not llm_config:
            llm_config = crud.create_default_llm_config(db)
        
        # LLM config fields
        llm_data = {
            "name": llm_config.name,
            "model_name": llm_config.model_name,
            "temperature": llm_config.temperature,
            "top_p": llm_config.top_p,
            "max_tokens": llm_config.max_tokens,
            "description": llm_config.description,
            "extra_params": llm_config.extra_params,
            "enable_thinking": getattr(llm_config, 'enable_thinking', False),
            "created_at": llm_config.created_at,
            "updated_at": llm_config.updated_at
        }
    except Exception as e:
        # Log the error
        logging.error(f"Error getting LLM config: {str(e)}")
        
        # If the table doesn't exist or there's another error, use default values
        llm_data = {
            "name": settings.LLM_CONFIG_NAME,
            "model_name": settings.LLM_MODEL,
            "temperature": settings.LLM_TEMPERATURE,
            "top_p": settings.LLM_TOP_P,
            "max_tokens": settings.LLM_MAX_TOKENS,
            "description": "Default LLM configuration",
            "enable_thinking": False,
            "extra_params": {
                "base_url": settings.OPENAI_API_BASE,
                "api_key": settings.OPENAI_API_KEY
            },
            "created_at": None,
            "updated_at": None
        }
    
    # Get RAG config
    try:
        rag_configs_db = AdminConfigService.get_configs_by_category(db, "rag")
        general_configs_db = AdminConfigService.get_configs_by_category(db, "general")
        
        # Convert to dictionaries with proper typing
        rag_config = {}
        for config_item in rag_configs_db:
            value = AdminConfigService.get_config(db, config_item.key)
            rag_config[config_item.key] = value
            
        general_config = {}
        for config_item in general_configs_db:
            value = AdminConfigService.get_config(db, config_item.key)
            general_config[config_item.key] = value
    except Exception as e:
        # Log the error
        logging.error(f"Error getting admin configs: {str(e)}")
        
        # Use empty dicts if there's an error
        rag_config = {}
        general_config = {}
    
    # Add default values if missing for RAG
    if AdminConfig.KEY_PREDEFINED_COLLECTION not in rag_config:
        rag_config[AdminConfig.KEY_PREDEFINED_COLLECTION] = settings.DEFAULT_COLLECTION
    if AdminConfig.KEY_RETRIEVER_TOP_K not in rag_config:
        rag_config[AdminConfig.KEY_RETRIEVER_TOP_K] = settings.RETRIEVER_TOP_K
    if AdminConfig.KEY_ALLOW_USER_UPLOADS not in rag_config:
        rag_config[AdminConfig.KEY_ALLOW_USER_UPLOADS] = True
    if AdminConfig.KEY_MAX_FILE_SIZE_MB not in rag_config:
        rag_config[AdminConfig.KEY_MAX_FILE_SIZE_MB] = 10
    if AdminConfig.KEY_GLOBAL_COLLECTION_BEHAVIOR not in rag_config:
        rag_config[AdminConfig.KEY_GLOBAL_COLLECTION_BEHAVIOR] = "auto_update"
    
    # Combine configs
    unified_config = {
        "llm": llm_data,
        "rag": rag_config,
        "general": general_config
    }
    
    return unified_config

@router.put("/", response_model=Dict[str, Any])
async def update_unified_config(
    config: Dict[str, Any],
    current_user: models.User = Depends(get_admin_access),
    db: Session = Depends(get_db)
):
    """
    Update unified configuration for all settings.
    This handles both LLM config (llm_config table) and admin configs (admin_config table).
    Admin users only.
    """
    result = {"updated": {}}
    
    # Update LLM config if provided
    if "llm" in config:
        try:
            llm_config = config["llm"]
            # Create LLMConfigUpdate object from dict
            update_config = schemas.LLMConfigUpdate(**llm_config)
            active_config = crud.update_llm_config(db, update_config)
            result["updated"]["llm"] = llm_config
        except Exception as e:
            # Log the error
            logging.error(f"Error updating LLM config in unified update: {str(e)}")
            # Don't add to result["updated"] if it failed
    
    # Update RAG config if provided
    if "rag" in config:
        try:
            rag_config = config["rag"]
            for key, value in rag_config.items():
                AdminConfigService.set_config(
                    db, 
                    key, 
                    value, 
                    f"RAG configuration: {key}", 
                    "rag"
                )
            result["updated"]["rag"] = rag_config
        except Exception as e:
            # Log the error
            logging.error(f"Error updating RAG config in unified update: {str(e)}")
            # Don't add to result["updated"] if it failed
    
    # Update general config if provided
    if "general" in config:
        try:
            general_config = config["general"]
            for key, value in general_config.items():
                AdminConfigService.set_config(
                    db, 
                    key, 
                    value, 
                    f"General configuration: {key}", 
                    "general"
                )
            result["updated"]["general"] = general_config
        except Exception as e:
            # Log the error
            logging.error(f"Error updating general config in unified update: {str(e)}")
            # Don't add to result["updated"] if it failed
    
    # Get the updated unified config
    return await get_unified_config(db, current_user)

@router.get("/global-collection-behavior", response_model=Dict[str, str])
async def get_global_collection_behavior(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """
    Get the current global collection behavior setting.
    Returns either 'auto_update' or 'readonly_on_change'.
    """
    behavior = AdminConfigService.get_config(
        db, 
        AdminConfig.KEY_GLOBAL_COLLECTION_BEHAVIOR, 
        "auto_update"
    )
    
    return {
        "behavior": behavior,
        "description": {
            "auto_update": "Conversations automatically use the latest global collection",
            "readonly_on_change": "Conversations become read-only when global collection changes"
        }.get(behavior, "Unknown behavior")
    }

@router.put("/global-collection-behavior", response_model=Dict[str, str])
async def set_global_collection_behavior(
    behavior: Optional[str] = None,  # Query parameter
    request_body: Optional[Dict[str, str]] = Body(None),  # Request body
    current_user: models.User = Depends(get_admin_access),
    db: Session = Depends(get_db)
):
    """
    Set the global collection behavior.
    Admin users only.
    
    Args:
        behavior: Either 'auto_update' or 'readonly_on_change' (query parameter)
        request_body: JSON body with {"behavior": "auto_update|readonly_on_change"}
    """
    # Get behavior from query parameter or request body
    if behavior is None and request_body and "behavior" in request_body:
        behavior = request_body["behavior"]
    elif behavior is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Behavior must be provided either as query parameter or in request body"
        )
    
    if behavior not in ["auto_update", "readonly_on_change"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Behavior must be either 'auto_update' or 'readonly_on_change'"
        )
    
    AdminConfigService.set_config(
        db,
        AdminConfig.KEY_GLOBAL_COLLECTION_BEHAVIOR,
        behavior,
        f"Global collection behavior: {behavior}",
        "rag"
    )
    
    return {
        "behavior": behavior,
        "message": f"Global collection behavior set to '{behavior}'"
    }

@router.get("/{category}", response_model=Dict[str, Any])
async def get_category_config(
    category: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """
    Get configuration for a specific category (llm, rag, general).
    For 'llm' category, retrieves from llm_config table.
    For other categories, retrieves from admin_config table.
    """
    if category.lower() == "llm":
        try:
            llm_config = crud.get_llm_config(db)
            if not llm_config:
                llm_config = crud.create_default_llm_config(db)
                
            # Return LLM config with all fields except ID
            return {"llm": {
                "name": llm_config.name,
                "model_name": llm_config.model_name,
                "temperature": llm_config.temperature,
                "top_p": llm_config.top_p,
                "max_tokens": llm_config.max_tokens,
                "description": llm_config.description,
                "extra_params": llm_config.extra_params,
                "enable_thinking": getattr(llm_config, 'enable_thinking', False),
                "created_at": llm_config.created_at,
                "updated_at": llm_config.updated_at
            }}
        except Exception as e:
            # Log the error
            logging.error(f"Error getting LLM config for category endpoint: {str(e)}")
            
            # If the table doesn't exist or there's another error, return default values
            return {"llm": {
                "name": settings.LLM_CONFIG_NAME,
                "model_name": settings.LLM_MODEL,
                "temperature": settings.LLM_TEMPERATURE,
                "top_p": settings.LLM_TOP_P,
                "max_tokens": settings.LLM_MAX_TOKENS,
                "description": "Default LLM configuration",
                "enable_thinking": False,
                "extra_params": {
                    "base_url": settings.OPENAI_API_BASE,
                    "api_key": settings.OPENAI_API_KEY
                },
                "created_at": None,
                "updated_at": None
            }}

    try:
        configs = AdminConfigService.get_configs_by_category(db, category)
        
        result = {}
        for config_item in configs:
            value = AdminConfigService.get_config(db, config_item.key)
            result[config_item.key] = value
    except Exception as e:
        # Log the error
        logging.error(f"Error getting {category} config: {str(e)}")
        result = {}

    # Add default values if missing for RAG
    if category == "rag":
        if AdminConfig.KEY_PREDEFINED_COLLECTION not in result:
            result[AdminConfig.KEY_PREDEFINED_COLLECTION] = settings.DEFAULT_COLLECTION
        if AdminConfig.KEY_RETRIEVER_TOP_K not in result:
            result[AdminConfig.KEY_RETRIEVER_TOP_K] = settings.RETRIEVER_TOP_K
        if AdminConfig.KEY_ALLOW_USER_UPLOADS not in result:
            result[AdminConfig.KEY_ALLOW_USER_UPLOADS] = True
        if AdminConfig.KEY_MAX_FILE_SIZE_MB not in result:
            result[AdminConfig.KEY_MAX_FILE_SIZE_MB] = 10
            
    return {category: result}

@router.put("/{category}", response_model=Dict[str, Any])
async def update_category_config(
    category: str,
    config: Dict[str, Any],
    current_user: models.User = Depends(get_admin_access),
    db: Session = Depends(get_db)
):
    """
    Update configuration for a specific category.
    For 'llm' category, updates the llm_config table.
    For other categories, updates the admin_config table.
    Admin users only.
    """
    if category.lower() == "llm":
        try:
            # Create LLMConfigUpdate object from dict
            update_config = schemas.LLMConfigUpdate(**config)
            active_config = crud.update_llm_config(db, update_config)
            
            # Return updated LLM config with all fields except ID
            return {"llm": {
                "name": active_config.name,
                "model_name": active_config.model_name,
                "temperature": active_config.temperature,
                "top_p": active_config.top_p,
                "max_tokens": active_config.max_tokens,
                "description": active_config.description,
                "extra_params": active_config.extra_params,
                "enable_thinking": getattr(active_config, 'enable_thinking', False),
                "created_at": active_config.created_at,
                "updated_at": active_config.updated_at
            }}
        except Exception as e:
            # Log the error
            logging.error(f"Error updating LLM config: {str(e)}")
            
            # Return the default config
            return await get_category_config(category, db, current_user)
    
    # For non-LLM categories, update admin_config table
    try:
        for key, value in config.items():
            AdminConfigService.set_config(
                db, 
                key, 
                value, 
                f"{category.capitalize()} configuration: {key}", 
                category
            )
        
        # Return updated config
        configs = AdminConfigService.get_configs_by_category(db, category)
        
        result = {}
        for config_item in configs:
            value = AdminConfigService.get_config(db, config_item.key)
            result[config_item.key] = value
        
        return {category: result}
    except Exception as e:
        # Log the error
        logging.error(f"Error updating {category} config: {str(e)}")
        
        # Return the current config
        return await get_category_config(category, db, current_user) 