from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query, Form, UploadFile, File
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime
import os
import io
import time

from app.db import crud, models, schemas
from app.db.database import get_db
from app.utils.auth import get_admin_access
from app.services.rag_service import RemoteVectorStoreManager
from app.services.ingestion_service import DocumentIngestionService
from app.config import settings

router = APIRouter(
    prefix="/collections",
    tags=["admin-collections"],
)

# Initialize services
vector_store_manager = RemoteVectorStoreManager(
    embedding_url=settings.REMOTE_EMBEDDER_URL,
    milvus_uri=settings.MILVUS_URI
)
ingestion_service = DocumentIngestionService()

@router.get("/", response_model=List[schemas.CollectionWithFiles])
async def list_all_collections(
    skip: int = 0,
    limit: int = 100,
    include_files: bool = True,
    current_user: models.User = Depends(get_admin_access),
    db: Session = Depends(get_db)
):
    """
    List all collections with their files (admin only).
    """
    if include_files:
        collections = crud.get_all_collections_with_files(db, skip, limit)
    else:
        collections = crud.get_all_collections(db, skip, limit)
    
    return collections

@router.post("/", response_model=schemas.Collection)
async def create_admin_collection(
    collection: schemas.CollectionBase,
    current_user: models.User = Depends(get_admin_access),
    db: Session = Depends(get_db)
):
    """
    Create a new admin collection.
    """
    # Check if collection with this name already exists
    existing_collection = crud.get_collection_by_name(db, collection.name)
    if existing_collection:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Collection with name '{collection.name}' already exists"
        )
    
    # Force collection to be admin-only
    collection_data = collection.model_dump()
    collection_data["is_admin_only"] = True
    
    # Create collection
    collection_create = schemas.CollectionCreate(
        **collection_data,
        user_id=current_user.id
    )
    db_collection = crud.create_collection(db, collection_create)
    
    # Create the collection in Milvus if it doesn't exist (with admin prefix)
    from app.utils.string_utils import sanitize_collection_name
    safe_collection_name = sanitize_collection_name(f"admin_{db_collection.name}")
    if not vector_store_manager.collection_exists(safe_collection_name):
        ingestion_service.create_new_collection(safe_collection_name)
    
    return db_collection

@router.post("/with-files", response_model=Dict[str, Any])
async def create_admin_collection_with_files(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    file_ids: List[int] = Form(...),
    is_global_default: bool = Form(False),
    current_user: models.User = Depends(get_admin_access),
    db: Session = Depends(get_db)
):
    """
    Create a new admin collection and process selected files in one operation.
    This is the recommended way to create collections as it's more efficient.
    
    Args:
        name: Collection name (must be unique)
        description: Optional collection description
        file_ids: List of file IDs from MinIO to include in the collection
        is_global_default: Whether to set this as the global default collection
    
    Returns:
        Collection details with processing status
    """
    try:
        # Check if collection with this name already exists
        existing_collection = crud.get_collection_by_name(db, name)
        if existing_collection:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Collection with name '{name}' already exists"
            )
        
        # Validate that all files exist and are accessible
        files_to_process = []
        for file_id in file_ids:
            file = crud.get_file_storage(db, file_id)
            if not file:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"File with ID {file_id} not found"
                )
            files_to_process.append(file)
        
        if not files_to_process:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one valid file must be provided"
            )
        
        # Create collection in database
        collection_create = schemas.CollectionCreate(
            name=name,
            description=description,
            user_id=current_user.id,
            is_admin_only=True,
            is_global_default=is_global_default
        )
        db_collection = crud.create_collection(db, collection_create)
        
        # Create sanitized collection name for Milvus with admin prefix
        from app.utils.string_utils import sanitize_collection_name
        safe_collection_name = sanitize_collection_name(f"admin_{name}")
        
        # Create the collection in Milvus first
        try:
            collection_created = ingestion_service.create_new_collection(safe_collection_name, description or "")
            if not collection_created:
                # Collection might already exist, check if it's empty
                if vector_store_manager.collection_exists(safe_collection_name):
                    print(f"Collection {safe_collection_name} already exists in Milvus, proceeding...")
                else:
                    raise Exception(f"Failed to create collection {safe_collection_name} in Milvus")
        except Exception as e:
            # Rollback database collection creation
            crud.delete_collection(db, db_collection.id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create collection in vector store: {str(e)}"
            )
        
        # Process files and add them to the collection
        processed_files = []
        failed_files = []
        total_chunks = 0
        
        from app.services.minio_service import MinioService
        minio_service = MinioService()
        
        for file in files_to_process:
            try:
                # Add file to collection in database first
                collection_file_create = schemas.CollectionFileCreate(
                    collection_id=db_collection.id,
                    file_id=file.id
                )
                collection_file = crud.add_file_to_collection(db, collection_file_create)
                
                # Download file from MinIO
                download_success, file_data = minio_service.download_file(file.file_path)
                if not download_success:
                    failed_files.append({
                        "file_id": file.id,
                        "filename": file.original_filename,
                        "error": "Failed to download from storage"
                    })
                    continue
                
                # Process file for vector storage
                num_docs = ingestion_service.ingest_file_object(
                    file_obj=file_data,
                    filename=file.filename,
                    collection_name=safe_collection_name,
                    metadata={
                        "source_file_id": file.id, 
                        "file_name": file.original_filename,
                        "collection_id": db_collection.id,
                        "collection_name": name
                    }
                )
                
                # Update file metadata
                crud.update_file_storage(db, file.id, {
                    "file_metadata": {
                        **(file.file_metadata or {}),
                        "is_processed_for_rag": True,
                        "chunk_count": num_docs,
                        "processed_at": datetime.utcnow().isoformat()
                    }
                })
                
                # Update collection file record
                crud.update_collection_file(db, collection_file.id, schemas.CollectionFileUpdate(
                    is_processed=True
                ))
                
                processed_files.append({
                    "file_id": file.id,
                    "filename": file.original_filename,
                    "chunks_processed": num_docs
                })
                total_chunks += num_docs
                
            except Exception as e:
                print(f"Error processing file {file.id} for collection {name}: {e}")
                failed_files.append({
                    "file_id": file.id,
                    "filename": file.original_filename,
                    "error": str(e)
                })
                
                # Update file metadata to indicate error
                try:
                    crud.update_file_storage(db, file.id, {
                        "file_metadata": {
                            **(file.file_metadata or {}),
                            "processing_error": str(e),
                            "processed_at": datetime.utcnow().isoformat()
                        }
                    })
                except:
                    pass
        
        # If no files were processed successfully, delete the collection
        if not processed_files:
            try:
                ingestion_service.delete_collection(safe_collection_name)
            except:
                pass
            crud.delete_collection(db, db_collection.id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process any files for the collection"
            )
        
        # Update global default collection setting if requested
        if is_global_default:
            from app.services.admin_config_service import AdminConfigService
            AdminConfigService.set_predefined_collection(db, name)
        
        return {
            "collection": {
                "id": db_collection.id,
                "name": db_collection.name,
                "description": db_collection.description,
                "is_global_default": db_collection.is_global_default,
                "created_at": db_collection.created_at.isoformat()
            },
            "processing_summary": {
                "total_files": len(files_to_process),
                "processed_successfully": len(processed_files),
                "failed": len(failed_files),
                "total_chunks_created": total_chunks
            },
            "processed_files": processed_files,
            "failed_files": failed_files,
            "milvus_collection_name": safe_collection_name,
            "message": f"Collection '{name}' created successfully with {len(processed_files)} files processed"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in create_admin_collection_with_files: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create collection: {str(e)}"
        )

@router.get("/{collection_id}", response_model=schemas.CollectionWithFiles)
async def get_admin_collection(
    collection_id: int,
    current_user: models.User = Depends(get_admin_access),
    db: Session = Depends(get_db)
):
    """
    Get a specific admin collection with its files.
    """
    collection = crud.get_collection_with_files(db, collection_id)
    
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection with ID {collection_id} not found"
        )
    
    # Check if it's an admin collection
    if not collection.is_admin_only:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This is not an admin collection"
        )
    
    return collection

@router.put("/{collection_id}", response_model=schemas.Collection)
async def update_admin_collection(
    collection_id: int,
    collection_update: schemas.CollectionUpdate,
    current_user: models.User = Depends(get_admin_access),
    db: Session = Depends(get_db)
):
    """
    Update an admin collection metadata.
    
    Request Body Fields:
    - name: Collection display name (must be unique)
    - description: Collection description for admin reference
    - is_active: Whether collection is active (for soft delete/disable)
    - is_admin_only: Always forced to True for admin collections
    - is_global_default: Set this collection as the global default for RAG
    
    Note: This only updates metadata. To add/remove files, use the unified creation endpoints.
    """
    db_collection = crud.get_collection(db, collection_id)
    
    if not db_collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection with ID {collection_id} not found"
        )
    
    # Check if it's an admin collection
    if not db_collection.is_admin_only:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This is not an admin collection"
        )
    
    # If name is being updated, check it doesn't conflict
    if collection_update.name and collection_update.name != db_collection.name:
        existing = crud.get_collection_by_name(db, collection_update.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Collection with name '{collection_update.name}' already exists"
            )
    
    # Ensure it remains admin-only
    collection_update_dict = collection_update.model_dump(exclude_unset=True)
    collection_update_dict["is_admin_only"] = True
    
    # Update collection
    updated_collection = crud.update_collection(db, collection_id, schemas.CollectionUpdate(**collection_update_dict))
    
    # If setting as global default, update admin config
    if collection_update.is_global_default and updated_collection.is_global_default:
        from app.services.admin_config_service import AdminConfigService
        AdminConfigService.set_predefined_collection(db, updated_collection.name)
        print(f"Updated admin config: set '{updated_collection.name}' as global default collection")
    
    return updated_collection

@router.delete("/{collection_id}")
async def delete_admin_collection(
    collection_id: int,
    force: bool = Query(False, description="Force delete even if conversations are linked to this collection"),
    current_user: models.User = Depends(get_admin_access),
    db: Session = Depends(get_db)
):
    """
    Delete an admin collection.
    
    Args:
        collection_id: ID of the collection to delete
        force: If True, will unlink conversations before deleting the collection
    
    Security Note: 
        - Cannot delete the current global default collection for system safety
        - To delete a global default collection, first set another collection as global default
    
    Note: This always deletes the collection from Milvus as well.
    """
    db_collection = crud.get_collection(db, collection_id)
    
    if not db_collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection with ID {collection_id} not found"
        )
    
    # Check if it's an admin collection
    if not db_collection.is_admin_only:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This is not an admin collection"
        )
    
    # Check if this is the current global default collection - prevent deletion
    if db_collection.is_global_default:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the current global default collection. Please set another collection as global default first."
        )
    
    # Check if there are conversations linked to this collection
    linked_conversations = db.query(models.Conversation).filter(
        models.Conversation.linked_global_collection_id == collection_id
    ).all()
    
    if linked_conversations and not force:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete collection: {len(linked_conversations)} conversations are linked to this collection. Use force=true to unlink them first."
        )
    
    # If force is True, unlink all conversations from this collection
    if linked_conversations and force:
        for conversation in linked_conversations:
            conversation.linked_global_collection_id = None
            conversation.original_global_collection_name = None
            # Optionally change conversation type back to regular
            if conversation.conversation_type == models.ConversationType.GLOBAL_COLLECTION:
                conversation.conversation_type = models.ConversationType.REGULAR
        db.commit()
        print(f"Unlinked {len(linked_conversations)} conversations from collection {db_collection.name}")
    
    # Always delete from Milvus first
    from app.utils.string_utils import sanitize_collection_name
    milvus_collection_name = sanitize_collection_name(f"admin_{db_collection.name}")
    try:
        ingestion_service.delete_collection(milvus_collection_name)
        print(f"Successfully deleted Milvus collection: {milvus_collection_name}")
    except Exception as e:
        # Log error but continue with database deletion
        print(f"Error deleting Milvus collection {milvus_collection_name}: {e}")
        # Don't raise exception here, continue with database deletion
    
    # Delete from database
    try:
        crud.delete_collection(db, collection_id)
        print(f"Successfully deleted database collection: {db_collection.name}")
    except Exception as e:
        print(f"Error deleting database collection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete collection from database: {str(e)}"
        )
    
    return {
        "detail": "Collection deleted successfully",
        "collection_name": db_collection.name,
        "milvus_collection_name": milvus_collection_name,
        "unlinked_conversations": len(linked_conversations) if linked_conversations else 0
    }

# REMOVED: process_collection_for_rag endpoint
# This endpoint has been replaced by the unified collection creation approach.
# Files are now processed immediately during collection creation via:
# - POST /api/admin/collections/with-files
# - POST /api/admin/collections/upload-and-create

@router.get("/milvus/collections", response_model=List[str])
async def list_milvus_collections(
    current_user: models.User = Depends(get_admin_access)
):
    """
    List all collections directly from Milvus vector store (admin only).
    
    This returns the actual collections that exist in Milvus, which may differ
    from the database collections if there are sync issues.
    
    Usage:
    - Health monitoring dashboard
    - Debugging Milvus vs database sync issues
    - Admin interface showing Milvus status
    """
    collections = vector_store_manager.list_collections()
    return collections

@router.get("/milvus/stats", response_model=List[Dict[str, Any]])
async def get_milvus_collection_stats(
    current_user: models.User = Depends(get_admin_access)
):
    """
    Get statistics for all Milvus collections.
    """
    from pymilvus import connections, utility
    
    try:
        # Connect to Milvus
        connections.connect(uri=settings.MILVUS_URI)
        
        # Get list of collections
        collections = utility.list_collections()
        
        # Get stats for each collection
        result = []
        for collection_name in collections:
            try:
                # Create collection object to get stats
                from pymilvus import Collection
                collection = Collection(collection_name)
                
                # Get collection info and convert schema to dict
                schema_dict = {}
                if collection.schema:
                    schema_dict = {
                        "fields": [
                            {
                                "name": field.name,
                                "dtype": str(field.dtype),
                                "description": field.description
                            } for field in collection.schema.fields
                        ],
                        "description": collection.schema.description
                    }
                
                stats = {
                    "row_count": collection.num_entities,
                    "schema": schema_dict,
                    "description": collection.description
                }
                
                # Add to result
                result.append({
                    "name": collection_name,
                    "stats": stats
                })
            except Exception as e:
                # Add error info
                result.append({
                    "name": collection_name,
                    "error": str(e)
                })
        
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting Milvus stats: {str(e)}"
        )

# Helper function for processing files
async def process_file_for_collection(db: Session, file_id: int, collection_name: str):
    """Process a file for a collection in the background."""
    from app.services.minio_service import MinioService
    
    try:
        # Get services
        minio_service = MinioService()
        ingestion_service = DocumentIngestionService()
        
        # Get file info
        file = crud.get_file_storage(db, file_id)
        if not file:
            return
        
        # Download file from MinIO
        download_success, file_data = minio_service.download_file(file.file_path)
        if not download_success:
            return
        
        # Process file for vector storage
        num_docs = ingestion_service.ingest_file_object(
            file_obj=file_data,
            filename=file.filename,
            collection_name=collection_name,
            metadata={"source_file_id": file.id, "file_name": file.original_filename}
        )
        
        # Update file metadata
        crud.update_file_storage(db, file_id, {
            "file_metadata": {
                **(file.file_metadata or {}),
                "is_processed_for_rag": True,
                "is_processing_for_rag": False,
                "chunk_count": num_docs,
                "processed_at": datetime.utcnow().isoformat()
            }
        })
        
        # Update collection file record
        collection_files = crud.get_collection_files_by_file_id(db, file_id)
        for cf in collection_files:
            crud.update_collection_file(db, cf.id, schemas.CollectionFileUpdate(
                is_processed=True
            ))
        
    except Exception as e:
        print(f"Error processing file {file_id} for collection {collection_name}: {e}")
        
        # Update file metadata to indicate error
        try:
            crud.update_file_storage(db, file_id, {
                "file_metadata": {
                    **(file.file_metadata or {}),
                    "processing_error": str(e),
                    "is_processing_for_rag": False
                }
            })
        except:
            pass

# REMOVED: add_file_to_collection endpoint
# This endpoint has been replaced by the unified collection creation approach.
# Files should be added during collection creation via:
# - POST /api/admin/collections/with-files (for existing files)
# - POST /api/admin/collections/upload-and-create (for new file uploads)
# This eliminates the inefficient multi-step workflow.

@router.post("/upload-and-create", response_model=Dict[str, Any])
async def upload_files_and_create_collection(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    files: List[UploadFile] = File(...),
    is_global_default: bool = Form(False),
    current_user: models.User = Depends(get_admin_access),
    db: Session = Depends(get_db)
):
    """
    Upload files and create a new admin collection in one operation.
    This is the most convenient way for admins to create collections.
    
    Args:
        name: Collection name (must be unique)
        description: Optional collection description
        files: Files to upload and include in the collection
        is_global_default: Whether to set this as the global default collection
    
    Returns:
        Collection details with processing status
    """
    try:
        # Check if collection with this name already exists
        existing_collection = crud.get_collection_by_name(db, name)
        if existing_collection:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Collection with name '{name}' already exists"
            )
        
        if not files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one file must be provided"
            )
        
        # Validate file types and sizes
        supported_extensions = ['.pdf', '.txt', '.doc', '.docx', '.csv', '.md']
        max_file_size = 50 * 1024 * 1024  # 50MB for admin uploads
        
        for file in files:
            file_ext = os.path.splitext(file.filename)[1].lower()
            if not any(file_ext.endswith(ext) for ext in supported_extensions):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported file type: {file_ext}. Supported types: {', '.join(supported_extensions)}"
                )
        
        # Create collection in database first
        collection_create = schemas.CollectionCreate(
            name=name,
            description=description,
            user_id=current_user.id,
            is_admin_only=True,
            is_global_default=is_global_default
        )
        db_collection = crud.create_collection(db, collection_create)
        
        # Create sanitized collection name for Milvus with admin prefix
        from app.utils.string_utils import sanitize_collection_name
        safe_collection_name = sanitize_collection_name(f"admin_{name}")
        
        # Create the collection in Milvus
        try:
            collection_created = ingestion_service.create_new_collection(safe_collection_name, description or "")
            if not collection_created:
                if vector_store_manager.collection_exists(safe_collection_name):
                    print(f"Collection {safe_collection_name} already exists in Milvus, proceeding...")
                else:
                    raise Exception(f"Failed to create collection {safe_collection_name} in Milvus")
        except Exception as e:
            # Rollback database collection creation
            crud.delete_collection(db, db_collection.id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create collection in vector store: {str(e)}"
            )
        
        # Upload and process files
        from app.services.minio_service import MinioService
        
        minio_service = MinioService()
        processed_files = []
        failed_files = []
        total_chunks = 0
        
        for file in files:
            try:
                # Read file content
                file_content = await file.read()
                file_size = len(file_content)
                
                # Check file size
                if file_size > max_file_size:
                    failed_files.append({
                        "filename": file.filename,
                        "error": f"File too large. Maximum size: {max_file_size/1024/1024}MB"
                    })
                    continue
                
                # Generate safe filename
                timestamp = int(time.time())
                safe_filename = f"{timestamp}_{sanitize_collection_name(file.filename)}"
                file_path = f"admin/{current_user.id}/{safe_filename}"
                
                # Upload to MinIO
                await file.seek(0)  # Reset file position
                minio_service.upload_file(
                    file_data=file_content,
                    file_path=file_path,
                    content_type=file.content_type
                )
                
                # Create file record in database
                file_create = schemas.FileStorageCreate(
                    user_id=current_user.id,
                    filename=safe_filename,
                    original_filename=file.filename,
                    file_path=file_path,
                    file_size=file_size,
                    mime_type=file.content_type,
                    file_metadata={"is_admin_upload": True}
                )
                db_file = crud.create_file_storage(db, file_create)
                
                # Add file to collection
                collection_file_create = schemas.CollectionFileCreate(
                    collection_id=db_collection.id,
                    file_id=db_file.id
                )
                collection_file = crud.add_file_to_collection(db, collection_file_create)
                
                # Process file for vector storage
                await file.seek(0)  # Reset file position again
                file_obj = io.BytesIO(file_content)
                
                num_docs = ingestion_service.ingest_file_object(
                    file_obj=file_obj,
                    filename=file.filename,
                    collection_name=safe_collection_name,
                    metadata={
                        "source_file_id": db_file.id,
                        "file_name": file.filename,
                        "collection_id": db_collection.id,
                        "collection_name": name
                    }
                )
                
                # Update file metadata
                crud.update_file_storage(db, db_file.id, {
                    "file_metadata": {
                        **(db_file.file_metadata or {}),
                        "is_processed_for_rag": True,
                        "chunk_count": num_docs,
                        "processed_at": datetime.utcnow().isoformat()
                    }
                })
                
                # Update collection file record
                crud.update_collection_file(db, collection_file.id, schemas.CollectionFileUpdate(
                    is_processed=True
                ))
                
                processed_files.append({
                    "file_id": db_file.id,
                    "filename": file.filename,
                    "chunks_processed": num_docs
                })
                total_chunks += num_docs
                
            except Exception as e:
                print(f"Error processing file {file.filename} for collection {name}: {e}")
                failed_files.append({
                    "filename": file.filename,
                    "error": str(e)
                })
        
        # If no files were processed successfully, delete the collection
        if not processed_files:
            try:
                ingestion_service.delete_collection(safe_collection_name)
            except:
                pass
            crud.delete_collection(db, db_collection.id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process any files for the collection"
            )
        
        # Update global default collection setting if requested
        if is_global_default:
            from app.services.admin_config_service import AdminConfigService
            AdminConfigService.set_predefined_collection(db, name)
        
        return {
            "collection": {
                "id": db_collection.id,
                "name": db_collection.name,
                "description": db_collection.description,
                "is_global_default": db_collection.is_global_default,
                "created_at": db_collection.created_at.isoformat()
            },
            "processing_summary": {
                "total_files": len(files),
                "processed_successfully": len(processed_files),
                "failed": len(failed_files),
                "total_chunks_created": total_chunks
            },
            "processed_files": processed_files,
            "failed_files": failed_files,
            "milvus_collection_name": safe_collection_name,
            "message": f"Collection '{name}' created successfully with {len(processed_files)} files uploaded and processed"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in upload_files_and_create_collection: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create collection: {str(e)}"
        ) 