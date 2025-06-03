from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.services.admin_config_service import AdminConfigService
from app.models.admin_config import AdminConfig
from app.config import settings

class RAGConfigService:
    """Service for handling RAG configuration that integrates with admin settings."""
    
    @staticmethod
    def get_predefined_collection(db: Session) -> str:
        """
        Get the predefined collection name from admin configuration.
        
        Args:
            db: Database session
            
        Returns:
            Predefined collection name
        """
        return AdminConfigService.get_predefined_collection(db)
    
    @staticmethod
    def get_retriever_top_k(db: Session) -> int:
        """
        Get the retriever top_k parameter from admin configuration.
        
        Args:
            db: Database session
            
        Returns:
            Retriever top_k value
        """
        return AdminConfigService.get_config(
            db,
            AdminConfig.KEY_RETRIEVER_TOP_K,
            settings.RETRIEVER_TOP_K
        )
    
    @staticmethod
    def get_global_collection_rag_prompt(db: Session) -> str:
        """
        Get the RAG system prompt for global collections.
        
        Args:
            db: Database session
            
        Returns:
            Global collection RAG system prompt
        """
        return AdminConfigService.get_global_collection_rag_prompt(db)
    
    @staticmethod
    def set_global_collection_rag_prompt(db: Session, prompt: str) -> AdminConfig:
        """
        Set the RAG system prompt for global collections.
        
        Args:
            db: Database session
            prompt: The system prompt to set
            
        Returns:
            AdminConfig object
        """
        return AdminConfigService.set_global_collection_rag_prompt(db, prompt)
    
    @staticmethod
    def get_rag_config(db: Session) -> Dict[str, Any]:
        """
        Get all RAG-related configuration parameters.
        
        Args:
            db: Database session
            
        Returns:
            Dictionary with RAG configuration
        """
        return {
            "predefined_collection": RAGConfigService.get_predefined_collection(db),
            "retriever_top_k": RAGConfigService.get_retriever_top_k(db),
            "global_collection_rag_prompt": RAGConfigService.get_global_collection_rag_prompt(db),
            "allow_user_uploads": AdminConfigService.get_config(
                db,
                AdminConfig.KEY_ALLOW_USER_UPLOADS,
                True
            )
        }
    
    @staticmethod
    def get_client_config(db: Session) -> Dict[str, Any]:
        """
        Get configuration values to be sent to the client.
        
        Args:
            db: Database session
            
        Returns:
            Dictionary with client-facing configuration
        """
        return {
            "predefinedCollection": RAGConfigService.get_predefined_collection(db),
            "globalCollectionRagPrompt": RAGConfigService.get_global_collection_rag_prompt(db),
            "allowUserUploads": AdminConfigService.get_config(
                db,
                AdminConfig.KEY_ALLOW_USER_UPLOADS,
                True
            ),
            "maxFileSizeMb": AdminConfigService.get_config(
                db,
                AdminConfig.KEY_MAX_FILE_SIZE_MB,
                10
            )
        }