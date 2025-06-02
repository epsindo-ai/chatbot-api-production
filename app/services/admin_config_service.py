from typing import Any, Dict, List, Optional, Union
from sqlalchemy.orm import Session
import json

from app.models.admin_config import AdminConfig
from app.config import settings

class AdminConfigService:
    """Service for managing unified system configurations."""
    
    @staticmethod
    def initialize_default_configs(db: Session):
        """
        Ensures that default configurations from settings are present in the database.
        If a default configuration is not found, it's added.
        This will primarily handle RAG and General settings. Core LLM settings are
        managed by the llm_configs table and its dedicated service/API.
        """
        # LLM Defaults section removed as core LLM settings are in llm_configs table

        # RAG Defaults
        rag_defaults = {
            AdminConfig.KEY_PREDEFINED_COLLECTION: settings.DEFAULT_COLLECTION,
            AdminConfig.KEY_RETRIEVER_TOP_K: settings.RETRIEVER_TOP_K,
            AdminConfig.KEY_ALLOW_USER_UPLOADS: True,  # Default from get_unified_config logic
            AdminConfig.KEY_MAX_FILE_SIZE_MB: 10,     # Default from get_unified_config logic
            AdminConfig.KEY_GLOBAL_COLLECTION_BEHAVIOR: "auto_update",  # Default behavior
        }
        for key, default_value in rag_defaults.items():
            existing_config = db.query(AdminConfig).filter(
                AdminConfig.key == key,
                AdminConfig.category == "rag"
            ).first()
            if not existing_config:
                AdminConfigService.set_config(
                    db,
                    key,
                    default_value,
                    f"Default RAG setting: {key}",
                    "rag"
                )
        
        # Note: No explicit commit here as set_config handles its own commit.
        # However, if this function were to do multiple set_config calls that should
        # be atomic as a group, a session commit at the end (managed by the caller)
        # would be needed, and set_config might need to be adjusted not to commit individually.
        # For now, individual commits by set_config are acceptable.

    @staticmethod
    def get_config(db: Session, key: str, default_value: Optional[Any] = None) -> Any:
        """
        Get a configuration value by key.
        
        Args:
            db: Database session
            key: Configuration key
            default_value: Default value if key is not found
            
        Returns:
            Configuration value
        """
        config = db.query(AdminConfig).filter(AdminConfig.key == key).first()
        
        if not config:
            # Return default from parameters or from settings
            if default_value is not None:
                return default_value
                
            # Fallback to settings based on key
            if key == AdminConfig.KEY_PREDEFINED_COLLECTION:
                return settings.DEFAULT_COLLECTION
            elif key == AdminConfig.KEY_RETRIEVER_TOP_K:
                return settings.RETRIEVER_TOP_K
            elif key == AdminConfig.KEY_ALLOW_USER_UPLOADS:
                return True
            elif key == AdminConfig.KEY_MAX_FILE_SIZE_MB:
                return 10  # Default 10MB
            elif key == AdminConfig.KEY_GLOBAL_COLLECTION_BEHAVIOR:
                return "auto_update"  # Default behavior
            
            return None
            
        # Convert value based on value_type
        if config.value_type == "int":
            return int(config.value)
        elif config.value_type == "float":
            return float(config.value)
        elif config.value_type == "boolean":
            return config.value.lower() == "true"
        elif config.value_type == "json":
            return json.loads(config.value)
        
        # Return as string for other types
        return config.value
        
    @staticmethod
    def set_config(db: Session, key: str, value: Any, description: Optional[str] = None, 
                  category: str = "general", value_type: Optional[str] = None) -> AdminConfig:
        """
        Set a configuration value.
        
        Args:
            db: Database session
            key: Configuration key
            value: Configuration value
            description: Optional description
            category: Configuration category (llm, rag, general, etc.)
            value_type: Value type (string, int, float, boolean, json)
            
        Returns:
            Updated AdminConfig object
        """
        # Determine value type if not provided
        if value_type is None:
            if isinstance(value, bool):
                value_type = "boolean"
            elif isinstance(value, int):
                value_type = "int"
            elif isinstance(value, float):
                value_type = "float"
            elif isinstance(value, (dict, list)):
                value_type = "json"
                value = json.dumps(value)
            else:
                value_type = "string"
                
        # Convert value to string
        if not isinstance(value, str):
            value = str(value)
            
        # Check if config exists
        config = db.query(AdminConfig).filter(AdminConfig.key == key).first()
        
        if config:
            # Update existing config
            config.value = value
            config.value_type = value_type
            config.category = category
            if description:
                config.description = description
        else:
            # Create new config
            config = AdminConfig(
                key=key,
                value=value,
                value_type=value_type,
                category=category,
                description=description
            )
            db.add(config)
            
        db.commit()
        db.refresh(config)
        
        return config
        
    @staticmethod
    def get_all_configs(db: Session) -> List[AdminConfig]:
        """
        Get all configurations.
        
        Args:
            db: Database session
            
        Returns:
            List of all AdminConfig objects
        """
        return db.query(AdminConfig).all()
        
    @staticmethod
    def get_configs_by_category(db: Session, category: str) -> List[AdminConfig]:
        """
        Get configurations by category.
        
        Args:
            db: Database session
            category: Configuration category
            
        Returns:
            List of AdminConfig objects in the specified category
        """
        return db.query(AdminConfig).filter(AdminConfig.category == category).all()
        
    @staticmethod
    def delete_config(db: Session, key: str) -> bool:
        """
        Delete a configuration.
        
        Args:
            db: Database session
            key: Configuration key
            
        Returns:
            True if deleted, False if not found
        """
        config = db.query(AdminConfig).filter(AdminConfig.key == key).first()
        if not config:
            return False
            
        db.delete(config)
        db.commit()
        
        return True
        
    @staticmethod
    def get_llm_config(db: Session) -> Dict[str, Any]:
        """
        Get LLM configuration as a dictionary.
        
        Args:
            db: Database session
            
        Returns:
            Dictionary of LLM configuration values
        """
        configs = AdminConfigService.get_configs_by_category(db, "llm")
        
        # Start with defaults
        llm_config = {
            "model_name": settings.LLM_MODEL,
            "temperature": settings.LLM_TEMPERATURE,
            "top_p": settings.LLM_TOP_P,
            "max_tokens": settings.LLM_MAX_TOKENS,
        }
        
        # Override with database values
        for config in configs:
            if config.key == AdminConfig.KEY_LLM_MODEL:
                llm_config["model_name"] = config.value
            elif config.key == AdminConfig.KEY_LLM_TEMPERATURE:
                llm_config["temperature"] = float(config.value)
            elif config.key == AdminConfig.KEY_LLM_TOP_P:
                llm_config["top_p"] = float(config.value)
            elif config.key == AdminConfig.KEY_LLM_MAX_TOKENS:
                llm_config["max_tokens"] = int(config.value)
                
        return llm_config
        
    @staticmethod
    def set_llm_config(db: Session, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Set LLM configuration from a dictionary.
        
        Args:
            db: Database session
            config: Dictionary of LLM configuration values
            
        Returns:
            Updated LLM configuration
        """
        if "model_name" in config:
            AdminConfigService.set_config(
                db, 
                AdminConfig.KEY_LLM_MODEL, 
                config["model_name"], 
                "LLM model name", 
                "llm", 
                "string"
            )
            
        if "temperature" in config:
            AdminConfigService.set_config(
                db, 
                AdminConfig.KEY_LLM_TEMPERATURE, 
                config["temperature"], 
                "LLM temperature", 
                "llm", 
                "float"
            )
            
        if "top_p" in config:
            AdminConfigService.set_config(
                db, 
                AdminConfig.KEY_LLM_TOP_P, 
                config["top_p"], 
                "LLM top_p", 
                "llm", 
                "float"
            )
            
        if "max_tokens" in config:
            AdminConfigService.set_config(
                db, 
                AdminConfig.KEY_LLM_MAX_TOKENS, 
                config["max_tokens"], 
                "LLM max tokens", 
                "llm", 
                "int"
            )
            
        return AdminConfigService.get_llm_config(db)
        
    @staticmethod
    def set_predefined_collection(db: Session, collection_name: str) -> AdminConfig:
        """Set the predefined collection for RAG."""
        return AdminConfigService.set_config(
            db, 
            AdminConfig.KEY_PREDEFINED_COLLECTION, 
            collection_name, 
            "Default collection for RAG",
            "rag",
            "string"
        )
        
    @staticmethod
    def get_predefined_collection(db: Session) -> str:
        """
        Get the predefined collection for RAG from admin configuration.
        
        Args:
            db: Database session
            
        Returns:
            Predefined collection name as string
        """
        return AdminConfigService.get_config(
            db,
            AdminConfig.KEY_PREDEFINED_COLLECTION,
            settings.DEFAULT_COLLECTION
        )
        
    @staticmethod
    def get_retriever_top_k(db: Session) -> int:
        """
        Get the retriever top_k parameter.
        
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