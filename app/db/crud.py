from sqlalchemy.orm import Session
from . import models, schemas
from app.utils.password import get_password_hash
from app.config import settings
import uuid
import os
from sqlalchemy import func
from app.models.user import UserRole
from app.models.llm_config import LLMConfig
import bcrypt
from typing import Union, List
from datetime import datetime, timedelta
from sqlalchemy.sql import or_
from sqlalchemy import text

# User CRUD operations
def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()

def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = bcrypt.hashpw(user.password.encode(), bcrypt.gensalt()).decode()
    db_user = models.User(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        hashed_password=hashed_password,
        is_active=user.is_active,
        role=UserRole.USER
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def delete_user(db: Session, user_id: int):
    """Delete a user from the database."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user:
        db.delete(user)
        db.commit()
        return True
    return False

# Conversation CRUD operations
def get_conversation(db: Session, conversation_id: str):
    return db.query(models.Conversation).filter(models.Conversation.id == conversation_id).first()

def get_user_conversations(db: Session, user_id: int, skip: int = 0, limit: int = 100, include_empty: bool = True):
    query = db.query(models.Conversation)\
        .filter(models.Conversation.user_id == user_id)
    
    if not include_empty:
        query = query.filter(models.Conversation.is_empty == False)
        
    # Use coalesce to handle NULL updated_at values, falling back to created_at
    # This ensures conversations are always sorted by their most recent activity
    return query\
        .order_by(models.Conversation.updated_at.desc().nullslast(), models.Conversation.created_at.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()

def create_conversation(db: Session, user_id: int, meta_data: dict = None):
    db_conversation = models.Conversation(
        id=str(uuid.uuid4()),
        user_id=user_id,
        meta_data=meta_data
    )
    db.add(db_conversation)
    db.commit()
    db.refresh(db_conversation)
    return db_conversation

def create_empty_conversation(db: Session, user_id: int, expires_in_hours: int = 24):
    """Creates a new empty conversation with an expiration time."""
    expires_at_datetime = datetime.utcnow() + timedelta(hours=expires_in_hours)
    db_conversation = models.Conversation(
        id=str(uuid.uuid4()),
        user_id=user_id,
        is_empty=True,
        expires_at=expires_at_datetime,
        meta_data=None # Or an empty dict, depending on preference for new conversations
    )
    db.add(db_conversation)
    db.commit()
    db.refresh(db_conversation)
    return db_conversation

def update_conversation(db: Session, conversation_id: str, meta_data: dict = None, display_file_id: int = None):
    db_conversation = db.query(models.Conversation).filter(models.Conversation.id == conversation_id).first()
    if db_conversation:
        if meta_data is not None:
            db_conversation.meta_data = meta_data
        if display_file_id is not None:
            db_conversation.display_file_id = display_file_id
        db.commit()
        db.refresh(db_conversation)
    return db_conversation

def delete_conversation(db: Session, conversation_id: str):
    """
    Delete a conversation and all associated data.
    
    This will:
    1. Delete the conversation from database (cascade deletes messages and files automatically)
    2. Clean up user collection vectors from Milvus (but preserve global collections)
    
    Args:
        db: Database session
        conversation_id: ID of conversation to delete
    
    Returns:
        bool: True if deletion was successful, False if conversation not found
    """
    db_conversation = db.query(models.Conversation).filter(models.Conversation.id == conversation_id).first()
    if not db_conversation:
        return False
    
    # Store info before deletion for cleanup
    conversation_type = db_conversation.conversation_type
    
    try:
        # Break circular dependency by clearing display_file_id reference
        if db_conversation.display_file_id:
            print(f"Clearing display_file_id reference for conversation {conversation_id}")
            db_conversation.display_file_id = None
            db.commit()
        
        # Clean up user collection vectors from Milvus if this is a user files conversation
        # or if conversation has files (handles data inconsistency cases)
        if conversation_type == models.ConversationType.USER_FILES or get_conversation_files(db, conversation_id):
            try:
                from app.utils.string_utils import sanitize_collection_name, conversation_collection_name
                from app.services.ingestion_service import DocumentIngestionService
                
                collection_name = conversation_collection_name(conversation_id)
                safe_collection_name = sanitize_collection_name(collection_name)
                
                # Delete the user collection from Milvus
                ingestion_service = DocumentIngestionService()
                success = ingestion_service.delete_collection(safe_collection_name)
                if success:
                    print(f"Successfully deleted user collection from Milvus: {safe_collection_name}")
                else:
                    print(f"User collection {safe_collection_name} did not exist in Milvus (already deleted)")
            except Exception as e:
                print(f"Warning: Could not delete user collection from Milvus: {str(e)}")
                # Continue with database deletion even if Milvus cleanup fails
        
        # Delete conversation from database (cascade deletes messages and files automatically)
        db.delete(db_conversation)
        db.commit()
        return True
        
    except Exception as e:
        print(f"Error deleting conversation {conversation_id}: {str(e)}")
        db.rollback()
        return False

# Message CRUD operations
def get_conversation_messages(db: Session, conversation_id: str, skip: int = 0, limit: int = 100):
    return db.query(models.Message).filter(
        models.Message.conversation_id == conversation_id
    ).order_by(models.Message.timestamp.desc()).offset(skip).limit(limit).all()

def create_message(db: Session, message: schemas.MessageCreate):
    # Get the parent conversation
    conversation = db.query(models.Conversation).filter(models.Conversation.id == message.conversation_id).first()
    
    if not conversation:
        # This should ideally not happen if conversation_id is validated upstream
        # or if conversations are auto-created. Handle as an error or raise exception.
        # For now, let's assume conversation exists or is created before this point.
        pass # Or raise an error

    # If the conversation was empty, mark it as not empty and clear expiration
    if conversation and conversation.is_empty:
        conversation.is_empty = False
        conversation.expires_at = None
        # The commit for the message will also save these changes to the conversation

    # Get the highest sequence number in this conversation
    highest_seq = db.query(func.max(models.Message.sequence_number)).filter(
        models.Message.conversation_id == message.conversation_id
    ).scalar() or 0
    
    # Create new message with incremented sequence number
    db_message = models.Message(
        conversation_id=message.conversation_id,
        role=message.role,
        content=message.content,
        sequence_number=highest_seq + 1
    )
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message

# LLM Config CRUD operations
def get_llm_config(db: Session):
    """Get the single LLM configuration"""
    try:
        # Use a raw SQL query but with proper text() wrapper
        sql = text("SELECT name, model_name, temperature, top_p, max_tokens, description, extra_params, enable_thinking, created_at, updated_at FROM llm_config LIMIT 1")
        result = db.execute(sql).fetchone()
        
        if result:
            # Create a LLMConfig object manually
            from app.models.llm_config import LLMConfig
            config = LLMConfig()
            config.id = 1  # Default ID
            config.name = result.name
            config.model_name = result.model_name
            config.temperature = result.temperature
            config.top_p = result.top_p
            config.max_tokens = result.max_tokens
            config.description = result.description
            config.extra_params = result.extra_params
            config.enable_thinking = result.enable_thinking
            config.created_at = result.created_at
            config.updated_at = result.updated_at
            return config
        return None
    except Exception as e:
        # If there's an error (like missing table or column), return None
        print(f"Error getting LLM config: {e}")
        return None

def get_llm_config_by_name(db: Session, name: str):
    """Get LLM config by name - kept for backwards compatibility"""
    return get_llm_config(db)

def get_active_llm_config(db: Session):
    """Get the active LLM configuration (there's only one now)"""
    return get_llm_config(db)

def get_all_llm_configs(db: Session, skip: int = 0, limit: int = 100):
    """Get all LLM configs - kept for backwards compatibility"""
    config = get_llm_config(db)
    return [config] if config else []

def create_default_llm_config(db: Session):
    """Create a default LLM configuration"""
    from app.config import settings
    
    # Create a default config
    llm_config = schemas.LLMConfigCreate(
        name="Default LLM Config",
        model_name=settings.LLM_MODEL,
        temperature=settings.LLM_TEMPERATURE,
        top_p=settings.LLM_TOP_P,
        max_tokens=settings.LLM_MAX_TOKENS,
        description="Default configuration created automatically",
        enable_thinking=False,  # Default to False for thinking capability
        extra_params={
            "base_url": settings.OPENAI_API_BASE,
            "api_key": settings.OPENAI_API_KEY
        }
    )
    
    # Save to database
    return create_llm_config(db, llm_config)

def update_llm_config(db: Session, config: schemas.LLMConfigUpdate):
    """Update the LLM configuration"""
    try:
        # Check if config exists
        existing_config = get_llm_config(db)
        
        if not existing_config:
            # Create default config if it doesn't exist
            return create_default_llm_config(db)
        
        # Prepare update data
        update_data = config.dict(exclude_unset=True)
        if not update_data:
            return existing_config  # No changes to make
        
        # Build SQL update parts
        set_parts = []
        params = {}
        
        for key, value in update_data.items():
            if value is not None:  # Only update if value is not None
                set_parts.append(f"{key} = :{key}")
                params[key] = value
        
        if not set_parts:
            return existing_config  # No valid changes to make
        
        # Add updated_at timestamp
        set_parts.append("updated_at = now()")
        
        # Build and execute SQL update
        sql = text(f"UPDATE llm_config SET {', '.join(set_parts)}")
        db.execute(sql, params)
        db.commit()
        
        # Return updated config
        return get_llm_config(db)
    except Exception as e:
        print(f"Error updating LLM config: {e}")
        db.rollback()
        return existing_config

def create_llm_config(db: Session, config: schemas.LLMConfigCreate):
    """Create or update the single LLM configuration"""
    try:
        # Check if a config already exists
        existing_config = get_llm_config(db)
        
        if existing_config:
            # Update the existing config using update_llm_config
            return update_llm_config(db, schemas.LLMConfigUpdate(**config.dict()))
        else:
            # Create a new config using raw SQL with proper text() wrapper
            sql = text("""
            INSERT INTO llm_config 
            (name, model_name, temperature, top_p, max_tokens, description, extra_params, enable_thinking) 
            VALUES (:name, :model_name, :temperature, :top_p, :max_tokens, :description, :extra_params, :enable_thinking)
            """)
            
            db.execute(
                sql,
                {
                    "name": config.name,
                    "model_name": config.model_name,
                    "temperature": config.temperature,
                    "top_p": config.top_p,
                    "max_tokens": config.max_tokens,
                    "description": config.description,
                    "extra_params": config.extra_params,
                    "enable_thinking": config.enable_thinking
                }
            )
            db.commit()
            
            # Return the newly created config
            return get_llm_config(db)
    except Exception as e:
        print(f"Error creating LLM config: {e}")
        db.rollback()
        
        # Create a default config object without saving to DB
        from app.models.llm_config import LLMConfig
        config_obj = LLMConfig()
        config_obj.name = config.name
        config_obj.model_name = config.model_name
        config_obj.temperature = config.temperature
        config_obj.top_p = config.top_p
        config_obj.max_tokens = config.max_tokens
        config_obj.description = config.description
        config_obj.extra_params = config.extra_params
        config_obj.enable_thinking = config.enable_thinking
        return config_obj

def delete_llm_config(db: Session, config_id: int):
    """
    This function is kept for compatibility but does nothing.
    We always want to keep the single LLM config.
    """
    return False

# FileStorage CRUD operations
def create_file_storage(db: Session, file_data: schemas.FileStorageCreate):
    """Create a new file storage record."""
    db_file = models.FileStorage(**file_data.model_dump())
    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    return db_file

def get_file_storage(db: Session, file_id: int):
    """Get a file by ID."""
    return db.query(models.FileStorage).filter(models.FileStorage.id == file_id).first()

def get_user_files(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    """Get all files for a user."""
    return db.query(models.FileStorage).filter(
        models.FileStorage.user_id == user_id
    ).offset(skip).limit(limit).all()

def get_conversation_files(db: Session, conversation_id: str, skip: int = 0, limit: int = 100):
    """Get all files associated with a conversation."""
    return db.query(models.FileStorage).filter(
        models.FileStorage.conversation_id == conversation_id
    ).offset(skip).limit(limit).all()

def get_all_files(db: Session, skip: int = 0, limit: int = 100, search: str = None):
    """Get all files in the system, optionally filtered by filename."""
    query = db.query(models.FileStorage)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                models.FileStorage.filename.ilike(search_term),
                models.FileStorage.original_filename.ilike(search_term)
            )
        )
    
    return query.order_by(models.FileStorage.created_at.desc()).offset(skip).limit(limit).all()

def update_file_storage(db: Session, file_id: int, file_data: Union[schemas.FileStorageUpdate, dict]):
    """Update a file storage record."""
    db_file = db.query(models.FileStorage).filter(models.FileStorage.id == file_id).first()
    if db_file:
        # Handle both Pydantic model and dictionary
        if hasattr(file_data, 'model_dump'):
            # It's a Pydantic model
            update_data = file_data.model_dump(exclude_unset=True)
        else:
            # It's a dictionary
            update_data = file_data
            
        for key, value in update_data.items():
            setattr(db_file, key, value)
        db.commit()
        db.refresh(db_file)
    return db_file

def delete_file_storage(db: Session, file_id: int):
    """Delete a file."""
    db_file = db.query(models.FileStorage).filter(models.FileStorage.id == file_id).first()
    if db_file:
        db.delete(db_file)
        db.commit()
        return True
    return False

def get_file_by_path(db: Session, file_path: str):
    """Get a file by its file_path (MinIO object name)."""
    return db.query(models.FileStorage).filter(models.FileStorage.file_path == file_path).first()

def get_files_by_paths(db: Session, file_paths: List[str]):
    """Get multiple files by their file_paths (MinIO object names)."""
    return db.query(models.FileStorage).filter(models.FileStorage.file_path.in_(file_paths)).all()

# Collection CRUD operations
def create_collection(db: Session, collection_data: schemas.CollectionCreate):
    """Create a new collection."""
    # If this is marked as global default, ensure no other collection is marked as such
    if collection_data.is_global_default:
        # Reset any existing global default collection
        db.query(models.Collection).filter(models.Collection.is_global_default == True).update({"is_global_default": False})
        db.commit()
        
    db_collection = models.Collection(**collection_data.model_dump())
    db.add(db_collection)
    db.commit()
    db.refresh(db_collection)
    return db_collection

def get_collection(db: Session, collection_id: int):
    """Get a collection by ID."""
    return db.query(models.Collection).filter(models.Collection.id == collection_id).first()

def get_collection_by_name(db: Session, name: str):
    """Get a collection by name."""
    return db.query(models.Collection).filter(models.Collection.name == name).first()

def get_user_collections(db: Session, user_id: int, skip: int = 0, limit: int = 100, include_admin: bool = True):
    """Get all collections for a user, optionally including admin-only collections."""
    query = db.query(models.Collection).filter(models.Collection.user_id == user_id)
    
    if include_admin:
        # Include admin-only collections created by this user
        query = query.filter(
            (models.Collection.is_admin_only == False) | 
            ((models.Collection.is_admin_only == True) & (models.Collection.user_id == user_id))
        )
    else:
        # Only include non-admin collections
        query = query.filter(models.Collection.is_admin_only == False)
    
    return query.offset(skip).limit(limit).all()

def get_all_collections(db: Session, skip: int = 0, limit: int = 100, include_inactive: bool = False):
    """Get all collections, optionally including inactive ones."""
    query = db.query(models.Collection)
    
    if not include_inactive:
        query = query.filter(models.Collection.is_active == True)
    
    return query.offset(skip).limit(limit).all()

def get_all_collections_with_files(db: Session, skip: int = 0, limit: int = 100):
    """Get all collections with their associated files."""
    # Get all collections
    collections = get_all_collections(db, skip, limit)
    
    # Create list to hold collections with files
    collections_with_files = []
    
    for collection in collections:
        # Get collection with files
        collection_with_files = get_collection_with_files(db, collection.id)
        if collection_with_files:
            collections_with_files.append(collection_with_files)
    
    return collections_with_files

def update_collection(db: Session, collection_id: int, collection_data: schemas.CollectionUpdate):
    """Update a collection."""
    db_collection = db.query(models.Collection).filter(models.Collection.id == collection_id).first()
    if db_collection:
        # Check if setting as global default
        if collection_data.is_global_default and not db_collection.is_global_default:
            # Reset any existing global default collection
            db.query(models.Collection).filter(models.Collection.is_global_default == True).update({"is_global_default": False})
        
        update_data = collection_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_collection, key, value)
        db.commit()
        db.refresh(db_collection)
    return db_collection

def delete_collection(db: Session, collection_id: int):
    """Delete a collection."""
    db_collection = db.query(models.Collection).filter(models.Collection.id == collection_id).first()
    if db_collection:
        db.delete(db_collection)
        db.commit()
        return True
    return False

# CollectionFile CRUD operations
def add_file_to_collection(db: Session, collection_file_data: schemas.CollectionFileCreate):
    """Add a file to a collection."""
    db_collection_file = models.CollectionFile(**collection_file_data.model_dump())
    db.add(db_collection_file)
    db.commit()
    db.refresh(db_collection_file)
    return db_collection_file

def get_collection_file(db: Session, collection_file_id: int):
    """Get a collection-file association by ID."""
    return db.query(models.CollectionFile).filter(models.CollectionFile.id == collection_file_id).first()

def get_collection_files(db: Session, collection_id: int, skip: int = 0, limit: int = 100):
    """Get all files in a collection."""
    return db.query(models.CollectionFile).filter(
        models.CollectionFile.collection_id == collection_id
    ).offset(skip).limit(limit).all()

def get_file_collections(db: Session, file_id: int, skip: int = 0, limit: int = 100):
    """Get all collections containing a file."""
    return db.query(models.CollectionFile).filter(
        models.CollectionFile.file_id == file_id
    ).offset(skip).limit(limit).all()

def get_collection_files_by_file_id(db: Session, file_id: int):
    """Get all collection-file associations for a specific file."""
    return db.query(models.CollectionFile).filter(
        models.CollectionFile.file_id == file_id
    ).all()

def update_collection_file(db: Session, collection_file_id: int, collection_file_data: schemas.CollectionFileUpdate):
    """Update a collection-file association."""
    db_collection_file = db.query(models.CollectionFile).filter(models.CollectionFile.id == collection_file_id).first()
    if db_collection_file:
        update_data = collection_file_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_collection_file, key, value)
        db.commit()
        db.refresh(db_collection_file)
    return db_collection_file

def remove_file_from_collection(db: Session, collection_id: int, file_id: int):
    """Remove a file from a collection."""
    db_collection_file = db.query(models.CollectionFile).filter(
        models.CollectionFile.collection_id == collection_id,
        models.CollectionFile.file_id == file_id
    ).first()
    if db_collection_file:
        db.delete(db_collection_file)
        db.commit()
        return True
    return False

def get_collection_with_files(db: Session, collection_id: int):
    """Get a collection with all its files."""
    db_collection = db.query(models.Collection).filter(models.Collection.id == collection_id).first()
    if not db_collection:
        return None
    
    # Get all files in this collection
    collection_files = db.query(models.CollectionFile).filter(
        models.CollectionFile.collection_id == collection_id
    ).all()
    
    # Get file details
    file_ids = [cf.file_id for cf in collection_files]
    files = db.query(models.FileStorage).filter(models.FileStorage.id.in_(file_ids)).all()
    
    # Create response
    collection_dict = schemas.Collection.model_validate(db_collection).model_dump()
    collection_dict["files"] = [schemas.FileStorage.model_validate(file).model_dump() for file in files]
    
    return schemas.CollectionWithFiles(**collection_dict)

# Admin Config CRUD operations
def get_latest_admin_config(db: Session):
    """
    Get the latest admin configuration.
    Returns a dictionary of key-value pairs from the AdminConfig table.
    If the table doesn't exist, returns an empty dictionary.
    """
    try:
        configs = db.query(models.AdminConfig).all()
        if not configs:
            return {}
        
        # Convert to dictionary for easy access
        config_dict = {}
        for config in configs:
            config_dict[config.key] = config.value
        
        return config_dict
    except Exception as e:
        # Handle the case where the table doesn't exist
        print(f"Warning: Error fetching admin config: {str(e)}")
        return {}

def get_admin_config_by_key(db: Session, key: str):
    """Get an admin config by key."""
    return db.query(models.AdminConfig).filter(models.AdminConfig.key == key).first()

def create_admin_config(db: Session, key: str, value: str, description: str = None):
    """Create a new admin config."""
    db_config = models.AdminConfig(
        key=key,
        value=value,
        description=description
    )
    db.add(db_config)
    db.commit()
    db.refresh(db_config)
    return db_config

def update_admin_config(db: Session, key: str, value: str):
    """Update an admin config by key."""
    db_config = get_admin_config_by_key(db, key)
    if db_config:
        db_config.value = value
        db.commit()
        db.refresh(db_config)
        return db_config
    return None

def get_or_create_admin_config(db: Session, key: str, default_value: str, description: str = None):
    """Get an admin config by key or create it if it doesn't exist."""
    db_config = get_admin_config_by_key(db, key)
    if not db_config:
        db_config = create_admin_config(db, key, default_value, description)
    return db_config

def get_global_default_collection(db: Session):
    """Get the current global default collection."""
    return db.query(models.Collection).filter(models.Collection.is_global_default == True, models.Collection.is_active == True).first()

def create_conversation_with_global_collection(db: Session, user_id: int, meta_data: dict = None):
    """Create a new conversation linked to the current global default collection."""
    print(f"DEBUG: Starting create_conversation_with_global_collection for user_id={user_id}")
    
    try:
        # First try to find the global default collection directly
        print("DEBUG: Trying to get global default collection directly")
        collection = get_global_default_collection(db)
        
        if collection:
            print(f"DEBUG: Found global default collection: {collection.name}, id={collection.id}")
        else:
            # Import RAGConfigService here to avoid circular imports
            from app.services.rag_config_service import RAGConfigService
            
            print("DEBUG: No global default collection found, trying RAG config")
            
            # Get the RAG config which contains the predefined collection
            rag_config = RAGConfigService.get_rag_config(db)
            collection_name = rag_config.get("predefined_collection")
            print(f"DEBUG: Got predefined_collection from RAG config: {collection_name}")
            
            if not collection_name:
                print("DEBUG: No predefined collection available in RAG config")
                return None  # No predefined collection available
            
            # Find the collection by name
            collection = get_collection_by_name(db, collection_name)
            print(f"DEBUG: Collection lookup by name result: {collection}")
            
            if not collection:
                print(f"DEBUG: Collection '{collection_name}' not found in database")
                return None  # Collection not found
        
        # Create conversation with link to the collection and 24-hour expiration
        from datetime import datetime, timedelta
        expires_at_datetime = datetime.utcnow() + timedelta(hours=24)
        print(f"DEBUG: Creating conversation with linked_global_collection_id={collection.id}, expires_at={expires_at_datetime}")
        db_conversation = models.Conversation(
            id=str(uuid.uuid4()),
            user_id=user_id,
            meta_data=meta_data,
            conversation_type=models.ConversationType.GLOBAL_COLLECTION,
            linked_global_collection_id=collection.id,
            original_global_collection_name=collection.name,
            is_empty=True,  # Global collection conversations start empty
            expires_at=expires_at_datetime  # Expire in 24 hours if no messages are added
        )
        db.add(db_conversation)
        db.commit()
        db.refresh(db_conversation)
        print(f"DEBUG: Created conversation: {db_conversation.id}, type={db_conversation.conversation_type}, linked_collection_id={db_conversation.linked_global_collection_id}")
        
        return db_conversation
    except Exception as e:
        print(f"DEBUG: ERROR in create_conversation_with_global_collection: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return None

def create_conversation_for_user_files(db: Session, user_id: int, meta_data: dict = None):
    """Create a new conversation specifically for user-uploaded files with 24-hour expiration."""
    from datetime import datetime, timedelta
    expires_at_datetime = datetime.utcnow() + timedelta(hours=24)
    
    db_conversation = models.Conversation(
        id=str(uuid.uuid4()),
        user_id=user_id,
        meta_data=meta_data,
        conversation_type=models.ConversationType.USER_FILES,
        is_empty=True,  # User file conversations start empty
        expires_at=expires_at_datetime  # Expire in 24 hours if no messages are added
    )
    db.add(db_conversation)
    db.commit()
    db.refresh(db_conversation)
    return db_conversation

def is_global_collection_outdated(db: Session, conversation_id: str):
    """Check if a global collection linked to a conversation has been changed."""
    # Import services here to avoid circular imports
    from app.services.rag_config_service import RAGConfigService
    from app.services.admin_config_service import AdminConfigService
    
    conversation = get_conversation(db, conversation_id)
    if not conversation or conversation.conversation_type != models.ConversationType.GLOBAL_COLLECTION:
        return False
    
    # Get the current global collection behavior setting
    behavior = AdminConfigService.get_config(db, models.AdminConfig.KEY_GLOBAL_COLLECTION_BEHAVIOR, "auto_update")
    
    # If behavior is auto_update, we don't consider it outdated
    if behavior == "auto_update":
        return False
    
    # For readonly_on_change behavior, check if the collection has changed
    if behavior == "readonly_on_change":
        # Get the current predefined collection
        rag_config = RAGConfigService.get_rag_config(db)
        current_collection_name = rag_config.get("predefined_collection")
        
        if not current_collection_name:
            return True  # No predefined collection, so it's definitely changed
        
        # Compare with the original collection name when conversation was initiated
        return conversation.original_global_collection_name != current_collection_name
    
    # Default to not outdated for unknown behaviors
    return False

def update_conversation_to_current_global_collection(db: Session, conversation_id: str):
    """Update a conversation to use the current global default collection."""
    # Import RAGConfigService here to avoid circular imports
    from app.services.rag_config_service import RAGConfigService
    
    conversation = get_conversation(db, conversation_id)
    if not conversation or conversation.conversation_type != models.ConversationType.GLOBAL_COLLECTION:
        return None
    
    # Get the RAG config which contains the predefined collection
    rag_config = RAGConfigService.get_rag_config(db)
    collection_name = rag_config.get("predefined_collection")
    
    if not collection_name:
        return None  # No predefined collection available
    
    # Find the collection by name
    current_collection = get_collection_by_name(db, collection_name)
    if not current_collection:
        return None  # Collection not found
    
    # Update the conversation
    conversation.linked_global_collection_id = current_collection.id
    conversation.original_global_collection_name = current_collection.name
    db.commit()
    db.refresh(conversation)
    return conversation