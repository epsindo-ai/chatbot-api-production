from typing import Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.rag_config_service import RAGConfigService
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/rag-config", tags=["rag"])

@router.get("/", response_model=Dict[str, Any])
def get_rag_config(
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user)
):
    """Get RAG configuration for the client."""
    return RAGConfigService.get_client_config(db) 