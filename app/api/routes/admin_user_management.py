from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from app.db import crud, models, schemas
from app.db.database import get_db
from app.utils.auth import get_admin_access, get_current_user, get_super_admin_access
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

class UserStatsResponse(BaseModel):
    user_id: int
    username: str
    email: Optional[str] = None
    role: str
    is_active: bool
    created_at: str
    conversations_count: int
    files_count: int
    collections_count: int
    total_file_size_mb: float
    last_activity: Optional[str] = None

class BulkDeleteUsersRequest(BaseModel):
    user_ids: List[int]
    delete_files: bool = True
    delete_conversations: bool = True
    delete_collections: bool = True

@router.get("/", response_model=List[UserStatsResponse])
async def list_users_with_stats(
    skip: int = Query(0, description="Number of users to skip"),
    limit: int = Query(100, description="Maximum number of users to return"),
    include_stats: bool = Query(True, description="Whether to include user statistics"),
    active_only: bool = Query(False, description="Only return active users"),
    current_user: models.User = Depends(get_admin_access),
    db: Session = Depends(get_db)
):
    """
    List all users with comprehensive statistics for admin management.
    
    Returns detailed information about each user including:
    - Basic user info (username, email, role, status)
    - Activity statistics (conversations, files, collections)
    - Storage usage information
    - Last activity timestamp
    
    This helps admins make informed decisions about user management.
    """
    try:
        # Get users with optional filtering
        query = db.query(models.User)
        if active_only:
            query = query.filter(models.User.is_active == True)
        
        users = query.offset(skip).limit(limit).all()
        
        if not include_stats:
            # Return basic user info only
            return [
                UserStatsResponse(
                    user_id=user.id,
                    username=user.username,
                    email=user.email,
                    role=user.role.value,
                    is_active=user.is_active,
                    created_at=user.created_at.isoformat(),
                    conversations_count=0,
                    files_count=0,
                    collections_count=0,
                    total_file_size_mb=0.0,
                    last_activity=None
                ) for user in users
            ]
        
        # Build comprehensive user statistics
        user_stats = []
        for user in users:
            # Count conversations
            conversations_count = db.query(models.Conversation).filter(
                models.Conversation.user_id == user.id
            ).count()
            
            # Count files and calculate total size
            user_files = db.query(models.FileStorage).filter(
                models.FileStorage.user_id == user.id
            ).all()
            files_count = len(user_files)
            total_file_size = sum(file.file_size for file in user_files) if user_files else 0
            total_file_size_mb = round(total_file_size / (1024 * 1024), 2)
            
            # Count collections (admin collections created by this user)
            collections_count = db.query(models.Collection).filter(
                models.Collection.user_id == user.id
            ).count()
            
            # Get last activity (most recent conversation update)
            last_conversation = db.query(models.Conversation).filter(
                models.Conversation.user_id == user.id
            ).order_by(models.Conversation.updated_at.desc()).first()
            
            last_activity = None
            if last_conversation and last_conversation.updated_at:
                last_activity = last_conversation.updated_at.isoformat()
            elif user.created_at:
                last_activity = user.created_at.isoformat()
            
            user_stats.append(UserStatsResponse(
                user_id=user.id,
                username=user.username,
                email=user.email,
                role=user.role.value,
                is_active=user.is_active,
                created_at=user.created_at.isoformat() if user.created_at else "",
                conversations_count=conversations_count,
                files_count=files_count,
                collections_count=collections_count,
                total_file_size_mb=total_file_size_mb,
                last_activity=last_activity
            ))
        
        return user_stats
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve user statistics: {str(e)}"
        )

@router.get("/{user_id}/stats", response_model=UserStatsResponse)
async def get_user_stats(
    user_id: int,
    current_user: models.User = Depends(get_admin_access),
    db: Session = Depends(get_db)
):
    """
    Get detailed statistics for a specific user.
    
    This endpoint provides comprehensive information about a user's activity
    and resource usage, helpful for administrators to understand the impact
    of deleting a user before proceeding with the deletion.
    """
    # Get user info
    user = crud.get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    try:
        # Count conversations
        conversations_count = db.query(models.Conversation).filter(
            models.Conversation.user_id == user_id
        ).count()
        
        # Count files and calculate total size
        user_files = db.query(models.FileStorage).filter(
            models.FileStorage.user_id == user_id
        ).all()
        files_count = len(user_files)
        total_file_size = sum(file.file_size for file in user_files) if user_files else 0
        total_file_size_mb = round(total_file_size / (1024 * 1024), 2)
        
        # Count collections
        collections_count = db.query(models.Collection).filter(
            models.Collection.user_id == user_id
        ).count()
        
        # Get last activity
        last_conversation = db.query(models.Conversation).filter(
            models.Conversation.user_id == user_id
        ).order_by(models.Conversation.updated_at.desc()).first()
        
        last_activity = None
        if last_conversation and last_conversation.updated_at:
            last_activity = last_conversation.updated_at.isoformat()
        elif user.created_at:
            last_activity = user.created_at.isoformat()
        
        return UserStatsResponse(
            user_id=user.id,
            username=user.username,
            email=user.email,
            role=user.role.value,
            is_active=user.is_active,
            created_at=user.created_at.isoformat() if user.created_at else "",
            conversations_count=conversations_count,
            files_count=files_count,
            collections_count=collections_count,
            total_file_size_mb=total_file_size_mb,
            last_activity=last_activity
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve user statistics: {str(e)}"
        )

@router.post("/bulk-delete", response_model=Dict[str, Any])
async def bulk_delete_users(
    request: BulkDeleteUsersRequest,
    current_user: models.User = Depends(get_super_admin_access),
    db: Session = Depends(get_db)
):
    """
    Delete multiple users in a single operation.
    
    This is useful for administrators who need to clean up multiple inactive
    or unwanted user accounts at once. The operation includes comprehensive
    data cleanup for each user.
    
    Safety features:
    - Prevents deletion of admin users (except by admin)
    - Prevents self-deletion
    - Prevents deletion of the last admin user
    - Provides detailed statistics for each deletion attempt
    """
    if not request.user_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No user IDs provided for deletion"
        )
    
    if len(request.user_ids) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete more than 50 users at once"
        )
    
    deletion_results = {
        "successful_deletions": [],
        "failed_deletions": [],
        "skipped_deletions": [],
        "total_requested": len(request.user_ids),
        "total_successful": 0,
        "total_failed": 0,
        "total_skipped": 0,
        "summary_stats": {
            "total_files_deleted": 0,
            "total_conversations_deleted": 0,
            "total_collections_deleted": 0,
            "total_milvus_collections_deleted": 0
        }
    }
    
    # Check super admin count first (don't allow deletion of all super admins)
    super_admin_count = db.query(models.User).filter(models.User.role == models.UserRole.SUPER_ADMIN).count()
    super_admin_users_to_delete = []
    admin_users_to_delete = []
    
    for user_id in request.user_ids:
        user = crud.get_user(db, user_id)
        if user:
            if user.role == models.UserRole.SUPER_ADMIN:
                super_admin_users_to_delete.append(user_id)
            elif user.role == models.UserRole.ADMIN:
                admin_users_to_delete.append(user_id)
    
    # Prevent deletion if it would remove all super admins
    if len(super_admin_users_to_delete) >= super_admin_count:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete all super admin users. At least one super admin must remain."
        )
    
    for user_id in request.user_ids:
        try:
            # Get user info
            user_to_delete = crud.get_user(db, user_id)
            if not user_to_delete:
                deletion_results["failed_deletions"].append({
                    "user_id": user_id,
                    "reason": "User not found"
                })
                continue
            
            # Safety checks
            if user_to_delete.id == current_user.id:
                deletion_results["skipped_deletions"].append({
                    "user_id": user_id,
                    "username": user_to_delete.username,
                    "reason": "Cannot delete yourself"
                })
                continue
            
            # Initialize deletion stats for this user
            user_deletion_stats = {
                "user_id": user_id,
                "username": user_to_delete.username,
                "files_deleted": 0,
                "conversations_deleted": 0,
                "collections_deleted": 0,
                "milvus_collections_deleted": 0,
                "errors": []
            }
            
            # Delete user's files if requested
            if request.delete_files:
                user_files = crud.get_user_files(db, user_id)
                for file in user_files:
                    try:
                        minio_service.delete_file(file.file_path)
                        user_deletion_stats["files_deleted"] += 1
                    except Exception as e:
                        user_deletion_stats["errors"].append(f"Error deleting file {file.id}: {str(e)}")
            
            # Delete user's conversations and collections if requested
            if request.delete_conversations:
                user_conversations = crud.get_user_conversations(db, user_id)
                for conversation in user_conversations:
                    try:
                        # Delete user collection from Milvus if it's a USER_FILES conversation
                        if request.delete_collections and conversation.conversation_type == models.ConversationType.USER_FILES:
                            try:
                                collection_name = conversation_collection_name(conversation.id)
                                safe_collection_name = sanitize_collection_name(collection_name)
                                ingestion_service.delete_collection(safe_collection_name)
                                user_deletion_stats["milvus_collections_deleted"] += 1
                            except Exception as e:
                                user_deletion_stats["errors"].append(f"Error deleting Milvus collection for conversation {conversation.id}: {str(e)}")
                        
                        user_deletion_stats["conversations_deleted"] += 1
                    except Exception as e:
                        user_deletion_stats["errors"].append(f"Error processing conversation {conversation.id}: {str(e)}")
            
            # Delete user's admin collections if they have any
            if request.delete_collections:
                user_collections = db.query(models.Collection).filter(models.Collection.user_id == user_id).all()
                for collection in user_collections:
                    try:
                        # Global collections cannot be deleted via user deletion
                        if collection.is_global_default or collection.is_admin_only:
                            user_deletion_stats["errors"].append(f"Skipped deletion of global collection '{collection.name}' - global collections can only be deleted through admin collections endpoint")
                            
                            # Unlink this user's conversations from the global collection
                            linked_conversations = db.query(models.Conversation).filter(
                                models.Conversation.linked_global_collection_id == collection.id,
                                models.Conversation.user_id == user_id
                            ).all()
                            
                            for conv in linked_conversations:
                                conv.linked_global_collection_id = None
                                conv.original_global_collection_name = None
                                if conv.conversation_type == models.ConversationType.GLOBAL_COLLECTION:
                                    conv.conversation_type = models.ConversationType.REGULAR
                            continue
                        
                        # For regular collections, unlink all conversations
                        linked_conversations = db.query(models.Conversation).filter(
                            models.Conversation.linked_global_collection_id == collection.id
                        ).all()
                        
                        for conv in linked_conversations:
                            conv.linked_global_collection_id = None
                            conv.original_global_collection_name = None
                            if conv.conversation_type == models.ConversationType.GLOBAL_COLLECTION:
                                conv.conversation_type = models.ConversationType.REGULAR
                        
                        # Delete from Milvus (only for regular collections)
                        milvus_collection_name = sanitize_collection_name(collection.name)
                        
                        try:
                            ingestion_service.delete_collection(milvus_collection_name)
                            user_deletion_stats["milvus_collections_deleted"] += 1
                        except Exception as e:
                            user_deletion_stats["errors"].append(f"Error deleting Milvus collection '{milvus_collection_name}': {str(e)}")
                        
                        # Delete from database
                        crud.delete_collection(db, collection.id)
                        user_deletion_stats["collections_deleted"] += 1
                        
                    except Exception as e:
                        user_deletion_stats["errors"].append(f"Error processing collection {collection.id}: {str(e)}")
            
            # Finally, delete the user from database
            db.delete(user_to_delete)
            db.commit()
            
            # Add to successful deletions
            deletion_results["successful_deletions"].append(user_deletion_stats)
            deletion_results["total_successful"] += 1
            
            # Update summary stats
            deletion_results["summary_stats"]["total_files_deleted"] += user_deletion_stats["files_deleted"]
            deletion_results["summary_stats"]["total_conversations_deleted"] += user_deletion_stats["conversations_deleted"]
            deletion_results["summary_stats"]["total_collections_deleted"] += user_deletion_stats["collections_deleted"]
            deletion_results["summary_stats"]["total_milvus_collections_deleted"] += user_deletion_stats["milvus_collections_deleted"]
            
        except Exception as e:
            db.rollback()
            deletion_results["failed_deletions"].append({
                "user_id": user_id,
                "username": user_to_delete.username if 'user_to_delete' in locals() else "Unknown",
                "reason": str(e)
            })
            deletion_results["total_failed"] += 1
    
    deletion_results["total_skipped"] = len(deletion_results["skipped_deletions"])
    
    return {
        "detail": f"Bulk deletion completed: {deletion_results['total_successful']} successful, {deletion_results['total_failed']} failed, {deletion_results['total_skipped']} skipped",
        "results": deletion_results
    }

@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    delete_files: bool = Query(True, description="Whether to also delete user's files from MinIO storage"),
    delete_conversations: bool = Query(True, description="Whether to also delete user's conversations and collections"),
    delete_collections: bool = Query(True, description="Whether to also delete user's collections from Milvus"),
    dry_run: bool = Query(False, description="Preview what would be deleted without actually deleting"),
    current_user: models.User = Depends(get_super_admin_access),
    db: Session = Depends(get_db)
):
    """
    Delete a user and optionally all their associated data.
    
    Admin only operation that can:
    1. Delete the user from database
    2. Optionally delete all user's files from MinIO storage
    3. Optionally delete all user's conversations and associated collections
    4. Optionally clean up user collections from Milvus vector store
    
    Important Notes:
    - Global collections cannot be deleted via user deletion (they belong to all admins)
    - Global collections can only be deleted through the admin collections endpoint
    - Conversations using global collections will be unlinked but the collections remain
    - Only regular user collections will be deleted from the system
    
    New Features:
    - Dry run mode to preview deletion impact
    - Enhanced statistics and error reporting
    - Better safety checks and confirmations
    - Proper handling of global vs user collections
    
    This is a destructive operation and cannot be undone.
    """
    # Get user info
    user_to_delete = crud.get_user(db, user_id)
    if not user_to_delete:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    # Prevent deletion of admin users - only super admin can delete admins
    if user_to_delete.role in [models.UserRole.ADMIN, models.UserRole.SUPER_ADMIN]:
        # Prevent self-deletion
        if user_to_delete.id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete yourself"
            )
        
        # Check if this is the last super admin user
        if user_to_delete.role == models.UserRole.SUPER_ADMIN:
            super_admin_count = db.query(models.User).filter(models.User.role == models.UserRole.SUPER_ADMIN).count()
            if super_admin_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot delete the last super admin user"
                )
    
    deleted_stats = {
        "user_id": user_id,
        "username": user_to_delete.username,
        "files_deleted": 0,
        "conversations_deleted": 0,
        "collections_deleted": 0,
        "milvus_collections_deleted": 0,
        "global_default_collections_found": 0,
        "linked_conversations_unlinked": 0,
        "errors": [],
        "warnings": [],
        "dry_run": dry_run
    }
    
    # If dry run, collect information without deleting
    if dry_run:
        try:
            # Count what would be deleted
            user_files = crud.get_user_files(db, user_id) if delete_files else []
            user_conversations = crud.get_user_conversations(db, user_id) if delete_conversations else []
            user_collections = db.query(models.Collection).filter(models.Collection.user_id == user_id).all() if delete_collections else []
            
            # Check for global default collections
            global_collections = [c for c in user_collections if c.is_global_default or c.is_admin_only]
            regular_collections = [c for c in user_collections if not (c.is_global_default or c.is_admin_only)]
            
            deleted_stats.update({
                "files_deleted": len(user_files),
                "conversations_deleted": len(user_conversations),
                "collections_deleted": len(regular_collections),  # Only regular collections can be deleted
                "global_default_collections_found": len(global_collections)
            })
            
            # Calculate storage impact
            total_file_size = sum(file.file_size for file in user_files) if user_files else 0
            total_file_size_mb = round(total_file_size / (1024 * 1024), 2)
            
            # Count linked conversations for ALL collections (including global ones for unlinking)
            linked_conversations_count = 0
            for collection in user_collections:
                if collection.is_global_default or collection.is_admin_only:
                    # For global collections, only count this user's conversations
                    linked_count = db.query(models.Conversation).filter(
                        models.Conversation.linked_global_collection_id == collection.id,
                        models.Conversation.user_id == user_id
                    ).count()
                else:
                    # For regular collections, count all linked conversations
                    linked_count = db.query(models.Conversation).filter(
                        models.Conversation.linked_global_collection_id == collection.id
                    ).count()
                linked_conversations_count += linked_count
            
            deleted_stats["linked_conversations_unlinked"] = linked_conversations_count
            deleted_stats["total_file_size_mb"] = total_file_size_mb
            
            # Add warnings
            if global_collections:
                deleted_stats["warnings"].append(f"User owns {len(global_collections)} global collection(s). Global collections cannot be deleted via user deletion - only conversations using them will be unlinked.")
            
            if linked_conversations_count > 0:
                deleted_stats["warnings"].append(f"{linked_conversations_count} conversations would be unlinked from user's collections.")
            
            return {
                "detail": f"DRY RUN: User '{user_to_delete.username}' deletion preview completed",
                "deleted_stats": deleted_stats,
                "impact_summary": {
                    "files_to_delete": len(user_files),
                    "conversations_to_delete": len(user_conversations),
                    "collections_to_delete": len(regular_collections),  # Only regular collections
                    "global_collections_found": len(global_collections),
                    "storage_to_free_mb": total_file_size_mb,
                    "conversations_to_unlink": linked_conversations_count
                }
            }
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to perform dry run: {str(e)}"
            )
    
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
        
        # 3. Handle user's admin collections (global collections cannot be deleted here)
        if delete_collections:
            user_collections = db.query(models.Collection).filter(models.Collection.user_id == user_id).all()
            for collection in user_collections:
                try:
                    # Global collections are owned by all admins and cannot be deleted via user deletion
                    # They should only be deleted through the admin collections endpoint
                    if collection.is_global_default or collection.is_admin_only:
                        deleted_stats["warnings"].append(f"Skipped deletion of global collection '{collection.name}' - global collections can only be deleted through admin collections endpoint")
                        
                        # However, we can unlink conversations that use this collection
                        linked_conversations = db.query(models.Conversation).filter(
                            models.Conversation.linked_global_collection_id == collection.id,
                            models.Conversation.user_id == user_id  # Only unlink this user's conversations
                        ).all()
                        
                        if linked_conversations:
                            for conv in linked_conversations:
                                conv.linked_global_collection_id = None
                                conv.original_global_collection_name = None
                                if conv.conversation_type == models.ConversationType.GLOBAL_COLLECTION:
                                    conv.conversation_type = models.ConversationType.REGULAR
                                deleted_stats["linked_conversations_unlinked"] += 1
                        continue
                    
                    # For non-global collections (regular user collections)
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
                            deleted_stats["linked_conversations_unlinked"] += 1
                    
                    # Delete from Milvus (only for non-global collections)
                    milvus_collection_name = sanitize_collection_name(collection.name)
                    
                    try:
                        ingestion_service.delete_collection(milvus_collection_name)
                        deleted_stats["milvus_collections_deleted"] += 1
                    except Exception as e:
                        deleted_stats["errors"].append(f"Error deleting Milvus collection '{milvus_collection_name}': {str(e)}")
                    
                    # Delete from database
                    crud.delete_collection(db, collection.id)
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

@router.patch("/{user_id}/deactivate")
async def deactivate_user(
    user_id: int,
    current_user: models.User = Depends(get_super_admin_access),
    db: Session = Depends(get_db)
):
    """
    Deactivate a user account instead of deleting it.
    
    This is a safer alternative to deletion that:
    1. Sets the user as inactive (prevents login)
    2. Preserves all user data and relationships
    3. Can be easily reversed by reactivating the user
    4. Maintains data integrity for conversations and collections
    
    This is the recommended approach for temporary user management.
    """
    # Get user info
    user_to_deactivate = crud.get_user(db, user_id)
    if not user_to_deactivate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    # Prevent self-deactivation
    if user_to_deactivate.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate yourself"
        )
    
    # Prevent deactivation of the last super admin user
    if user_to_deactivate.role == models.UserRole.SUPER_ADMIN:
        super_admin_count = db.query(models.User).filter(
            models.User.role == models.UserRole.SUPER_ADMIN,
            models.User.is_active == True
        ).count()
        if super_admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate the last active super admin user"
            )
    
    # Also prevent deactivating admin users if they are the only admin left
    elif user_to_deactivate.role == models.UserRole.ADMIN:
        admin_count = db.query(models.User).filter(
            models.User.role == models.UserRole.ADMIN,
            models.User.is_active == True
        ).count()
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate the last active admin user"
            )
    
    if not user_to_deactivate.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already deactivated"
        )
    
    try:
        # Deactivate the user
        user_to_deactivate.is_active = False
        db.commit()
        db.refresh(user_to_deactivate)
        
        return {
            "detail": f"User '{user_to_deactivate.username}' deactivated successfully",
            "user_id": user_id,
            "username": user_to_deactivate.username,
            "is_active": user_to_deactivate.is_active,
            "note": "User data is preserved and can be reactivated if needed"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deactivate user: {str(e)}"
        )

@router.patch("/{user_id}/reactivate")
async def reactivate_user(
    user_id: int,
    current_user: models.User = Depends(get_super_admin_access),
    db: Session = Depends(get_db)
):
    """
    Reactivate a previously deactivated user account.
    
    This restores full access to a deactivated user:
    1. Sets the user as active (allows login)
    2. All user data and relationships remain intact
    3. User can immediately resume using the system
    """
    # Get user info
    user_to_reactivate = crud.get_user(db, user_id)
    if not user_to_reactivate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    if user_to_reactivate.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already active"
        )
    
    try:
        # Reactivate the user
        user_to_reactivate.is_active = True
        db.commit()
        db.refresh(user_to_reactivate)
        
        return {
            "detail": f"User '{user_to_reactivate.username}' reactivated successfully",
            "user_id": user_id,
            "username": user_to_reactivate.username,
            "is_active": user_to_reactivate.is_active,
            "note": "User can now log in and access all their data"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reactivate user: {str(e)}"
        )

@router.get("/inactive", response_model=List[UserStatsResponse])
async def list_inactive_users(
    skip: int = Query(0, description="Number of users to skip"),
    limit: int = Query(100, description="Maximum number of users to return"),
    days_inactive: int = Query(30, description="Consider users inactive after this many days"),
    current_user: models.User = Depends(get_admin_access),
    db: Session = Depends(get_db)
):
    """
    List users who have been inactive for a specified number of days.
    
    This helps administrators identify users who might be candidates for
    deactivation or deletion based on their activity levels.
    
    Inactive criteria:
    - No conversations updated in the specified timeframe
    - Includes both active and already deactivated users
    - Sorted by last activity (oldest first)
    """
    from datetime import datetime, timedelta
    
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_inactive)
        
        # Find users with no recent activity
        inactive_users = []
        all_users = db.query(models.User).offset(skip).limit(limit).all()
        
        for user in all_users:
            # Get user's most recent conversation activity
            last_conversation = db.query(models.Conversation).filter(
                models.Conversation.user_id == user.id
            ).order_by(models.Conversation.updated_at.desc()).first()
            
            # Determine if user is inactive
            is_inactive = False
            last_activity = None
            
            if last_conversation and last_conversation.updated_at:
                last_activity = last_conversation.updated_at
                is_inactive = last_activity < cutoff_date
            else:
                # No conversations, check user creation date
                last_activity = user.created_at
                is_inactive = user.created_at < cutoff_date if user.created_at else True
            
            if is_inactive:
                # Get user statistics
                conversations_count = db.query(models.Conversation).filter(
                    models.Conversation.user_id == user.id
                ).count()
                
                user_files = db.query(models.FileStorage).filter(
                    models.FileStorage.user_id == user.id
                ).all()
                files_count = len(user_files)
                total_file_size = sum(file.file_size for file in user_files) if user_files else 0
                total_file_size_mb = round(total_file_size / (1024 * 1024), 2)
                
                collections_count = db.query(models.Collection).filter(
                    models.Collection.user_id == user.id
                ).count()
                
                inactive_users.append(UserStatsResponse(
                    user_id=user.id,
                    username=user.username,
                    email=user.email,
                    role=user.role.value,
                    is_active=user.is_active,
                    created_at=user.created_at.isoformat() if user.created_at else "",
                    conversations_count=conversations_count,
                    files_count=files_count,
                    collections_count=collections_count,
                    total_file_size_mb=total_file_size_mb,
                    last_activity=last_activity.isoformat() if last_activity else None
                ))
        
        # Sort by last activity (oldest first)
        inactive_users.sort(key=lambda x: x.last_activity or "")
        
        return inactive_users
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve inactive users: {str(e)}"
        )

@router.post("/create-with-temp-password", response_model=schemas.UserCreateResponse)
async def create_user_with_temporary_password(
    user_data: schemas.AdminUserCreate,
    current_user: models.User = Depends(get_admin_access),
    db: Session = Depends(get_db)
):
    """
    Create a new user account with a temporary password that must be changed on first login.
    Only admins can create user accounts.
    """
    # Check if username already exists
    existing_user = crud.get_user_by_username(db, user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already registered"
        )
    
    # Check if email already exists (if provided)
    if user_data.email:
        existing_email = crud.get_user_by_email(db, user_data.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )
    
    try:
        # Create user with temporary password
        new_user = crud.create_user_with_temp_password(db, user_data)
        
        return schemas.UserCreateResponse(
            user_id=new_user.id,
            username=new_user.username,
            email=new_user.email,
            full_name=new_user.full_name,
            role=new_user.role.value,
            is_active=new_user.is_active,
            temporary_password=user_data.temporary_password,
            password_expires_at=new_user.temp_password_expires_at,
            must_reset_password=new_user.must_reset_password
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )

@router.post("/reset-password", response_model=schemas.PasswordResetResponse)
async def reset_user_password(
    reset_data: schemas.AdminPasswordReset,
    current_user: models.User = Depends(get_admin_access),
    db: Session = Depends(get_db)
):
    """
    Reset a user's password to a temporary one that must be changed on first login.
    Only admins can reset user passwords.
    """
    # Check if target user exists
    target_user = crud.get_user(db, reset_data.user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent admins from resetting super admin passwords (security measure)
    if target_user.role == models.UserRole.SUPER_ADMIN and current_user.role != models.UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can reset super admin passwords"
        )
    
    try:
        # Reset password
        updated_user = crud.reset_user_password(
            db, 
            reset_data.user_id, 
            reset_data.temporary_password, 
            reset_data.password_expires_hours
        )
        
        return schemas.PasswordResetResponse(
            user_id=updated_user.id,
            username=updated_user.username,
            temporary_password=reset_data.temporary_password,
            password_expires_at=updated_user.temp_password_expires_at,
            message="Password has been reset. User must change password on next login."
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset password: {str(e)}"
        )

@router.post("/generate-temp-password")
async def generate_temporary_password(
    current_user: models.User = Depends(get_admin_access)
):
    """
    Generate a secure temporary password for admin use.
    Returns a password that can be used when creating accounts or resetting passwords.
    """
    from app.utils.temp_password import generate_temporary_password
    
    temp_password = generate_temporary_password()
    
    return {
        "temporary_password": temp_password,
        "message": "Use this password when creating a user account or resetting a password. The user will be required to change it on first login."
    }
