from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body, Path
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.admin_config import AdminConfig
from app.services.admin_config_service import AdminConfigService
from app.services.ingestion_service import DocumentIngestionService
from app.services.rag_config_service import RAGConfigService
from app.auth.dependencies import get_current_admin_user
from app.db import crud, schemas

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/config", response_model=List[Dict[str, Any]])
def get_all_configs(
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_admin_user)
):
    """Get all admin configurations."""
    configs = AdminConfigService.get_all_configs(db)
    return [{"id": c.id, "key": c.key, "value": c.value, "description": c.description} for c in configs]

@router.get("/config/{key}", response_model=Dict[str, Any])
def get_config(
    key: str = Path(..., description="Configuration key"),
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_admin_user)
):
    """Get a specific admin configuration by key."""
    value = AdminConfigService.get_config(db, key)
    if value is None:
        raise HTTPException(status_code=404, detail="Configuration not found")
    
    return {"key": key, "value": value}

@router.post("/config", response_model=Dict[str, Any])
def set_config(
    key: str = Body(..., description="Configuration key"),
    value: Any = Body(..., description="Configuration value"),
    description: Optional[str] = Body(None, description="Configuration description"),
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_admin_user)
):
    """Set an admin configuration value."""
    config = AdminConfigService.set_config(db, key, value, description)
    return {"id": config.id, "key": config.key, "value": config.value, "description": config.description}

@router.delete("/config/{key}", response_model=Dict[str, bool])
def delete_config(
    key: str = Path(..., description="Configuration key"),
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_admin_user)
):
    """Delete an admin configuration."""
    deleted = AdminConfigService.delete_config(db, key)
    if not deleted:
        raise HTTPException(status_code=404, detail="Configuration not found")
    
    return {"success": True}

@router.get("/unified-config", response_model=Dict[str, Any])
def get_unified_config(
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_admin_user)
):
    """
    Get unified configuration including both LLM and RAG settings.
    This combines all configuration into a single endpoint for easier admin management.
    Admin users only.
    """
    # Get LLM config
    llm_config = crud.get_active_llm_config(db)
    if not llm_config:
        llm_config = crud.create_default_llm_config(db)
    
    # Get RAG config
    rag_config = RAGConfigService.get_client_config(db)
    
    # Add global collection prompt to RAG config
    rag_config["globalCollectionRagPrompt"] = RAGConfigService.get_global_collection_rag_prompt(db)
    
    # Combine configs
    unified_config = {
        "llm": {
            "id": llm_config.id,
            "name": llm_config.name,
            "model_name": llm_config.model_name,
            "temperature": llm_config.temperature,
            "top_p": llm_config.top_p,
            "max_tokens": llm_config.max_tokens,
            "description": llm_config.description,
            "is_active": llm_config.is_active,
        },
        "rag": rag_config
    }
    
    return unified_config

@router.put("/unified-config", response_model=Dict[str, Any])
def update_unified_config(
    config: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_admin_user)
):
    """
    Update unified configuration including both LLM and RAG settings.
    Admin users only.
    """
    result = {"updated": {}}
    
    # Update LLM config if provided
    if "llm" in config:
        llm_config = config["llm"]
        active_config = crud.get_active_llm_config(db)
        
        if not active_config:
            active_config = crud.create_default_llm_config(db)
        
        # Create update schema
        update_data = {}
        for field in ["name", "model_name", "temperature", "top_p", "max_tokens", "description"]:
            if field in llm_config:
                update_data[field] = llm_config[field]
        
        config_update = schemas.LLMConfigUpdate(**update_data)
        updated_config = crud.update_llm_config(db, active_config.id, config_update)
        
        result["updated"]["llm"] = {
            "id": updated_config.id,
            "name": updated_config.name,
            "model_name": updated_config.model_name,
            "temperature": updated_config.temperature,
            "top_p": updated_config.top_p,
            "max_tokens": updated_config.max_tokens,
            "description": updated_config.description,
            "is_active": updated_config.is_active,
        }
    
    # Update RAG config if provided
    if "rag" in config:
        rag_config = config["rag"]
        
        # Update predefined collection if provided
        if "predefinedCollection" in rag_config:
            collection_name = rag_config["predefinedCollection"]
            config_obj = AdminConfigService.set_predefined_collection(db, collection_name)
            result["updated"]["rag"] = result.get("updated", {}).get("rag", {})
            result["updated"]["rag"]["predefinedCollection"] = collection_name
        
        # Update allowUserUploads if provided
        if "allowUserUploads" in rag_config:
            allow_uploads = rag_config["allowUserUploads"]
            AdminConfigService.set_config(
                db, 
                "allow_user_uploads", 
                str(allow_uploads).lower(),
                "Whether users can upload their own files for RAG"
            )
            result["updated"]["rag"] = result.get("updated", {}).get("rag", {})
            result["updated"]["rag"]["allowUserUploads"] = allow_uploads
            
        # Update maxFileSizeMb if provided
        if "maxFileSizeMb" in rag_config:
            max_size = rag_config["maxFileSizeMb"]
            AdminConfigService.set_config(
                db,
                "max_file_size_mb",
                str(max_size),
                "Maximum file size in MB for user uploads"
            )
            result["updated"]["rag"] = result.get("updated", {}).get("rag", {})
            result["updated"]["rag"]["maxFileSizeMb"] = max_size

        # Update globalCollectionRagPrompt if provided
        if "globalCollectionRagPrompt" in rag_config:
            prompt = rag_config["globalCollectionRagPrompt"]
            RAGConfigService.set_global_collection_rag_prompt(db, prompt)
            result["updated"]["rag"] = result.get("updated", {}).get("rag", {})
            result["updated"]["rag"]["globalCollectionRagPrompt"] = prompt
    
    # Return the updated unified config
    return get_unified_config(db=db, current_user=current_user)

@router.get("/collections", response_model=List[str])
def list_collections(
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_admin_user)
):
    """List all available collections."""
    ingestion_service = DocumentIngestionService()
    try:
        collections = ingestion_service.vectorstore_manager.list_collections()
        return collections
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing collections: {str(e)}")

@router.post("/collections", response_model=Dict[str, Any])
def create_collection(
    name: str = Body(..., description="Collection name"),
    description: Optional[str] = Body(None, description="Collection description"),
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_admin_user)
):
    """Create a new collection."""
    ingestion_service = DocumentIngestionService()
    try:
        created = ingestion_service.create_new_collection(name, description or "")
        if not created:
            raise HTTPException(status_code=400, detail="Collection already exists")
        
        return {"name": name, "success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating collection: {str(e)}")

@router.delete("/collections/{name}", response_model=Dict[str, bool])
def delete_collection(
    name: str = Path(..., description="Collection name"),
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_admin_user)
):
    """Delete a collection."""
    ingestion_service = DocumentIngestionService()
    try:
        deleted = ingestion_service.delete_collection(name)
        if not deleted:
            raise HTTPException(status_code=404, detail="Collection not found")
        
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting collection: {str(e)}")

@router.post("/predefined-collection", response_model=Dict[str, Any])
def set_predefined_collection(
    collection_name: str = Body(..., description="Collection name to set as predefined"),
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_admin_user)
):
    """Set the predefined collection for RAG."""
    # Verify collection exists
    ingestion_service = DocumentIngestionService()
    collections = ingestion_service.vectorstore_manager.list_collections()
    
    if collection_name not in collections:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    # Set as predefined
    config = AdminConfigService.set_predefined_collection(db, collection_name)
    
    return {"key": config.key, "value": config.value, "success": True}

@router.get("/predefined-collection", response_model=Dict[str, Any])
def get_predefined_collection(
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_admin_user)
):
    """Get the currently set predefined collection."""
    collection = AdminConfigService.get_predefined_collection(db)
    return {"collection": collection}

@router.get("/global-collection-rag-prompt", response_model=Dict[str, Any])
def get_global_collection_rag_prompt(
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_admin_user)
):
    """Get the global collection RAG prompt."""
    prompt = RAGConfigService.get_global_collection_rag_prompt(db)
    return {"prompt": prompt}

@router.post("/global-collection-rag-prompt", response_model=Dict[str, Any])
def set_global_collection_rag_prompt(
    prompt: str = Body(..., description="RAG system prompt for global collections"),
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_admin_user)
):
    """Set the global collection RAG prompt."""
    config = RAGConfigService.set_global_collection_rag_prompt(db, prompt)
    return {"key": config.key, "value": config.value, "success": True}