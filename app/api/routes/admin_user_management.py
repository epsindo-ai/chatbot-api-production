from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from pydantic import BaseModel

from app.db import crud, models, schemas
from app.db.database import get_db
from app.utils.auth import get_admin_access, get_current_user
from app.services.minio_service import MinioService
from app.services.ingestion_service import DocumentIngestionService
from app.utils.string_utils import sanitize_collection_name, conversation_collection_name

router = APIRouter(
    prefix="/users",
    tags=["admin-user-management"],
)

# Initialize services
minio_service = MinioService()
ingestion_service = DocumentIngestionService()

class DeleteUserRequest(BaseModel):
    user_id: int
    delete_files: bool = True
    delete_conversations: bool = True
    delete_collections: bool = True

@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    delete_files: bool = Query(True, description="Whether to also delete user's files from MinIO storage"),
    delete_conversations: bool = Query(True, description="Whether to also delete user's conversations and collections"),
    delete_collections: bool = Query(True, description="Whether to also delete user's collections from Milvus"),
    current_user: models.User = Depends(get_admin_access),
    db: Session = Depends(get_db)
):
    """
    Delete a user and optionally all their associated data.
    
    Admin only operation that can:
    1. Delete the user from database
    2. Optionally delete all user's files from MinIO storage
    3. Optionally delete all user's conversations and associated collections
    4. Optionally clean up user collections from Milvus vector store
    
    This is a destructive operation and cannot be undone.
    """
    # Get user info
    user_to_delete = crud.get_user(db, user_id)
    if not user_to_delete:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    # Prevent deletion of admin users unless current user is also admin
    if user_to_delete.role == models.UserRole.ADMIN:
        # Prevent self-deletion
        if user_to_delete.id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete yourself"
            )
        
        # Check if this is the last admin user
        admin_count = db.query(models.User).filter(models.User.role == models.UserRole.ADMIN).count()
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete the last admin user"
            )
    
    deleted_stats = {
        "user_id": user_id,
        "username": user_to_delete.username,
        "files_deleted": 0,
        "conversations_deleted": 0,
        "collections_deleted": 0,
        "milvus_collections_deleted": 0,
        "errors": []
    }
    
    try:
        # 1. Delete user's files if requested
        if delete_files:
            user_files = crud.get_user_files(db, user_id)
            for file in user_files:
                try:
                    # Delete from MinIO
                    minio_service.delete_file(file.file_path)
                    deleted_stats["files_deleted"] += 1
                except Exception as e:
                    deleted_stats["errors"].append(f"Error deleting file {file.id}: {str(e)}")
            
        # 2. Delete user's conversations and collections if requested
        if delete_conversations:
            user_conversations = crud.get_user_conversations(db, user_id)
            for conversation in user_conversations:
                try:
                    # Delete user collection from Milvus if it's a USER_FILES conversation
                    if delete_collections and conversation.conversation_type == models.ConversationType.USER_FILES:
                        try:
                            collection_name = conversation_collection_name(conversation.id)
                            safe_collection_name = sanitize_collection_name(collection_name)
                            ingestion_service.delete_collection(safe_collection_name)
                            deleted_stats["milvus_collections_deleted"] += 1
                        except Exception as e:
                            deleted_stats["errors"].append(f"Error deleting Milvus collection for conversation {conversation.id}: {str(e)}")
                    
                    deleted_stats["conversations_deleted"] += 1
                except Exception as e:
                    deleted_stats["errors"].append(f"Error processing conversation {conversation.id}: {str(e)}")
        
        # 3. Delete user's admin collections if they have any
        if delete_collections:
            user_collections = db.query(models.Collection).filter(models.Collection.user_id == user_id).all()
            for collection in user_collections:
                try:
                    # Check if this is a global default collection
                    if collection.is_global_default:
                        deleted_stats["errors"].append(f"Skipped deletion of global default collection '{collection.name}' - please set another collection as global default first")
                        continue
                    
                    # Check if conversations are linked to this collection
                    linked_conversations = db.query(models.Conversation).filter(
                        models.Conversation.linked_global_collection_id == collection.id
                    ).all()
                    
                    if linked_conversations:
                        # Unlink conversations first
                        for conv in linked_conversations:
                            conv.linked_global_collection_id = None
                            conv.original_global_collection_name = None
                            if conv.conversation_type == models.ConversationType.GLOBAL_COLLECTION:
                                conv.conversation_type = models.ConversationType.REGULAR
                    
                    # Delete from Milvus
                    if collection.is_admin_only:
                        milvus_collection_name = sanitize_collection_name(f"admin_{collection.name}")
                    else:
                        milvus_collection_name = sanitize_collection_name(collection.name)
                    
                    try:
                        ingestion_service.delete_collection(milvus_collection_name)
                        deleted_stats["milvus_collections_deleted"] += 1
                    except Exception as e:
                        deleted_stats["errors"].append(f"Error deleting Milvus collection '{milvus_collection_name}': {str(e)}")
                    
                    deleted_stats["collections_deleted"] += 1
                except Exception as e:
                    deleted_stats["errors"].append(f"Error processing collection {collection.id}: {str(e)}")
        
        # 4. Finally, delete the user from database (this will cascade delete related records)
        db.delete(user_to_delete)
        db.commit()
        
        return {
            "detail": "User deleted successfully",
            "deleted_stats": deleted_stats
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(e)}"
        )

@router.delete("/admin/all-data")
async def delete_all_admin_data(
    confirm: str = Query(..., description="Must be 'DELETE_ALL_ADMIN_DATA' to confirm"),
    current_user: models.User = Depends(get_admin_access),
    db: Session = Depends(get_db)
):
    """
    Delete all admin files and collections.
    
    This is an extremely destructive operation that will:
    1. Delete all admin collections from database and Milvus
    2. Delete all admin files from MinIO storage
    3. Unlink any conversations linked to admin collections
    
    This operation cannot be undone.
    """
    if confirm != "DELETE_ALL_ADMIN_DATA":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide confirmation string 'DELETE_ALL_ADMIN_DATA' to proceed"
        )
    
    deleted_stats = {
        "admin_files_deleted": 0,
        "admin_collections_deleted": 0,
        "milvus_collections_deleted": 0,
        "conversations_unlinked": 0,
        "errors": []
    }
    
    try:
        # 1. Delete all admin collections
        admin_collections = db.query(models.Collection).filter(models.Collection.is_admin_only == True).all()
        
        for collection in admin_collections:
            try:
                # Check if conversations are linked to this collection
                linked_conversations = db.query(models.Conversation).filter(
                    models.Conversation.linked_global_collection_id == collection.id
                ).all()
                
                # Unlink conversations
                for conv in linked_conversations:
                    conv.linked_global_collection_id = None
                    conv.original_global_collection_name = None
                    if conv.conversation_type == models.ConversationType.GLOBAL_COLLECTION:
                        conv.conversation_type = models.ConversationType.REGULAR
                    deleted_stats["conversations_unlinked"] += 1
                
                # Delete from Milvus
                milvus_collection_name = sanitize_collection_name(f"admin_{collection.name}")
                try:
                    ingestion_service.delete_collection(milvus_collection_name)
                    deleted_stats["milvus_collections_deleted"] += 1
                except Exception as e:
                    deleted_stats["errors"].append(f"Error deleting Milvus collection '{milvus_collection_name}': {str(e)}")
                
                # Delete from database
                crud.delete_collection(db, collection.id)
                deleted_stats["admin_collections_deleted"] += 1
                
            except Exception as e:
                deleted_stats["errors"].append(f"Error deleting admin collection {collection.id}: {str(e)}")
        
        # 2. Delete all admin files (files in admin/ prefix)
        try:
            # Get all files with admin prefix in path
            all_files = db.query(models.FileStorage).all()
            admin_files = [f for f in all_files if f.file_path.startswith("admin/")]
            
            for file in admin_files:
                try:
                    # Delete from MinIO
                    minio_service.delete_file(file.file_path)
                    
                    # Delete from database
                    crud.delete_file_storage(db, file.id)
                    deleted_stats["admin_files_deleted"] += 1
                    
                except Exception as e:
                    deleted_stats["errors"].append(f"Error deleting admin file {file.id}: {str(e)}")
        
        except Exception as e:
            deleted_stats["errors"].append(f"Error processing admin files: {str(e)}")
        
        db.commit()
        
        return {
            "detail": "All admin data deleted successfully",
            "deleted_stats": deleted_stats
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete admin data: {str(e)}"
        )

@router.delete("/me/all-conversations")
async def delete_user_all_conversations(
    delete_collections: bool = Query(True, description="Whether to also delete collections and files associated with conversations"),
    current_user: models.User = Depends(get_current_user),  # Allow both users and admins
    db: Session = Depends(get_db)
):
    """
    Delete all user's own conversations and optionally associated collections and files.
    
    This will:
    1. Delete all user's conversations from database
    2. Optionally delete all files associated with those conversations from MinIO
    3. Optionally delete user collections from Milvus vector store
    
    Users can only delete their own conversations.
    This operation cannot be undone.
    """
    deleted_stats = {
        "conversations_deleted": 0,
        "files_deleted": 0,
        "collections_deleted": 0,
        "errors": []
    }
    
    try:
        # Get all user's conversations
        user_conversations = crud.get_user_conversations(db, current_user.id)
        
        for conversation in user_conversations:
            try:
                # Delete associated collections and files if requested
                if delete_collections:
                    # Delete user collection from Milvus if it's a USER_FILES conversation
                    if conversation.conversation_type == models.ConversationType.USER_FILES:
                        try:
                            collection_name = conversation_collection_name(conversation.id)
                            safe_collection_name = sanitize_collection_name(collection_name)
                            ingestion_service.delete_collection(safe_collection_name)
                            deleted_stats["collections_deleted"] += 1
                        except Exception as e:
                            deleted_stats["errors"].append(f"Error deleting Milvus collection for conversation {conversation.id}: {str(e)}")
                    
                    # Delete files associated with conversation
                    conversation_files = crud.get_conversation_files(db, conversation.id)
                    for file in conversation_files:
                        try:
                            # Delete from MinIO
                            minio_service.delete_file(file.file_path)
                            deleted_stats["files_deleted"] += 1
                        except Exception as e:
                            deleted_stats["errors"].append(f"Error deleting file {file.id}: {str(e)}")
                
                # Delete conversation (cascade deletes messages and files automatically)
                success = crud.delete_conversation(db, conversation.id)
                if success:
                    deleted_stats["conversations_deleted"] += 1
                else:
                    deleted_stats["errors"].append(f"Failed to delete conversation {conversation.id}")
                    
            except Exception as e:
                deleted_stats["errors"].append(f"Error processing conversation {conversation.id}: {str(e)}")
        
        return {
            "detail": "All conversations deleted successfully",
            "deleted_stats": deleted_stats
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete conversations: {str(e)}"
        )
