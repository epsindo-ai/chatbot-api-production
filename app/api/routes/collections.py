from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db import crud, models, schemas
from app.db.database import get_db
from app.utils.auth import get_current_user, get_admin_access
from app.services.rag_service import RemoteVectorStoreManager
from app.services.minio_service import MinioService
from app.services.ingestion_service import DocumentIngestionService
from app.config import settings
from app.utils.string_utils import conversation_collection_name

router = APIRouter(
    tags=["collections"],
    responses={404: {"description": "Not found"}},
)

# Initialize services
vector_store_manager = RemoteVectorStoreManager(
    embedding_url=settings.REMOTE_EMBEDDER_URL, 
    milvus_uri=settings.MILVUS_URI
)
minio_service = MinioService()
ingestion_service = DocumentIngestionService()

@router.get("/global-default", response_model=schemas.Collection, operation_id="api_collections_get_global_default")
def get_global_default_collection(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the current global default collection.
    This collection is used for knowledge base conversations.
    """
    collection = crud.get_global_default_collection(db)
    
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No global default collection has been defined"
        )
    
    return collection

@router.get("/", response_model=List[dict], operation_id="api_collections_get_user_collections")
def get_user_collections(
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's own conversation-based collections.
    
    Returns collections created from the user's file uploads to conversations.
    Each collection represents a conversation where the user has uploaded files.
    """
    # Get user's conversations that have files (which means they have collections)
    conversations_with_files = db.query(models.Conversation).filter(
        models.Conversation.user_id == current_user.id,
        models.Conversation.conversation_type == models.ConversationType.USER_FILES
    ).offset(skip).limit(limit).all()
    
    result = []
    for conversation in conversations_with_files:
        # Get files for this conversation
        files = crud.get_conversation_files(db, conversation.id)
        
        if files:  # Only include conversations that actually have files
            # Check if files are processed
            processed_files = [f for f in files if f.file_metadata and f.file_metadata.get("is_processed_for_rag", False)]
            
            collection_info = {
                "conversation_id": conversation.id,
                "collection_name": conversation_collection_name(conversation.id),
                "headline": conversation.headline or "Untitled Conversation",
                "created_at": conversation.created_at,
                "updated_at": conversation.updated_at,
                "file_count": len(files),
                "processed_file_count": len(processed_files),
                "is_ready": len(processed_files) == len(files),
                "files": [
                    {
                        "id": f.id,
                        "filename": f.original_filename,
                        "file_size": f.file_size,
                        "mime_type": f.mime_type,
                        "is_processed": f.file_metadata.get("is_processed_for_rag", False) if f.file_metadata else False,
                        "created_at": f.created_at
                    }
                    for f in files
                ]
            }
            result.append(collection_info)
    
    return result

@router.get("/{conversation_id}", response_model=dict, operation_id="api_collections_get_user_collection_details")
def get_user_collection_details(
    conversation_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a user's conversation-based collection.
    
    Shows all files in the conversation/collection and their processing status.
    Users can only access their own conversation collections.
    """
    # Check if conversation exists and belongs to user
    conversation = crud.get_conversation(db, conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found"
        )
    
    if conversation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this conversation"
        )
    
    # Get files for this conversation
    files = crud.get_conversation_files(db, conversation_id)
    
    if not files:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No files found in this conversation"
        )
    
    # Check processing status
    processed_files = [f for f in files if f.file_metadata and f.file_metadata.get("is_processed_for_rag", False)]
    
    # Get collection info from Milvus if available
    collection_name = conversation_collection_name(conversation_id)
    milvus_info = None
    try:
        if vector_store_manager.collection_exists(collection_name):
            # Get basic collection info
            milvus_info = {
                "exists": True,
                "name": collection_name
            }
        else:
            milvus_info = {"exists": False}
    except Exception as e:
        milvus_info = {"exists": False, "error": str(e)}
    
    return {
        "conversation_id": conversation.id,
        "collection_name": collection_name,
        "headline": conversation.headline or "Untitled Conversation",
        "created_at": conversation.created_at,
        "updated_at": conversation.updated_at,
        "conversation_type": conversation.conversation_type,
        "file_count": len(files),
        "processed_file_count": len(processed_files),
        "is_ready": len(processed_files) == len(files),
        "milvus_collection": milvus_info,
        "files": [
            {
                "id": f.id,
                "filename": f.original_filename,
                "file_path": f.file_path,
                "file_size": f.file_size,
                "mime_type": f.mime_type,
                "created_at": f.created_at,
                "is_processed": f.file_metadata.get("is_processed_for_rag", False) if f.file_metadata else False,
                "chunk_count": f.file_metadata.get("chunk_count", 0) if f.file_metadata else 0,
                "processed_at": f.file_metadata.get("processed_at") if f.file_metadata else None,
                "download_url": f"/api/collections/{conversation_id}/files/{f.id}/download"
            }
            for f in files
        ]
    }

@router.delete("/{conversation_id}/files/{file_id}", operation_id="api_collections_remove_file_from_conversation")
def remove_file_from_conversation(
    conversation_id: str,
    file_id: int,
    delete_from_minio: bool = Query(True, description="Whether to also delete the file from MinIO storage"),
    delete_from_vectorstore: bool = Query(True, description="Whether to also delete the file vectors from Milvus"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Remove a file from user's conversation collection.
    
    This will:
    1. Remove the file from the database
    2. Optionally delete the file from MinIO storage
    3. Optionally remove the file's vectors from the Milvus collection
    
    Users can only remove files from their own conversations.
    """
    # Check if conversation exists and belongs to user
    conversation = crud.get_conversation(db, conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found"
        )
    
    if conversation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this conversation"
        )
    
    # Check if file exists and belongs to this conversation
    file = crud.get_file_storage(db, file_id)
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File with ID {file_id} not found"
        )
    
    if file.conversation_id != conversation_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File does not belong to this conversation"
        )
    
    if file.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this file"
        )
    
    # Store file info for cleanup
    file_path = file.file_path
    collection_name = conversation_collection_name(conversation_id)
    
    # Delete from vector store if requested and file was processed
    if delete_from_vectorstore and file.file_metadata and file.file_metadata.get("is_processed_for_rag", False):
        try:
            success = remove_file_vectors_from_collection(collection_name, file_id)
            if not success:
                print(f"Warning: Could not remove vectors for file {file_id} from collection {collection_name}")
        except Exception as e:
            print(f"Error removing vectors for file {file_id}: {str(e)}")
            # Continue with deletion even if vector removal fails
    
    # Delete from MinIO if requested
    if delete_from_minio:
        try:
            minio_service.delete_file(file_path)
        except Exception as e:
            print(f"Error deleting file from MinIO: {str(e)}")
            # Continue with database deletion even if MinIO deletion fails
    
    # Delete from database
    success = crud.delete_file_storage(db, file_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete file from database"
        )
    
    return {
        "detail": "File removed successfully",
        "file_id": file_id,
        "conversation_id": conversation_id,
        "deleted_from_minio": delete_from_minio,
        "deleted_from_vectorstore": delete_from_vectorstore
    }

def remove_file_vectors_from_collection(collection_name: str, file_id: int) -> bool:
    """
    Remove vectors for a specific file from a Milvus collection.
    
    Args:
        collection_name: Name of the collection
        file_id: ID of the file whose vectors should be removed
        
    Returns:
        True if vectors were removed successfully, False otherwise
    """
    try:
        from pymilvus import connections, Collection, utility
        from app.utils.string_utils import sanitize_collection_name
        
        # Sanitize collection name
        safe_collection_name = sanitize_collection_name(collection_name)
        
        # Connect to Milvus
        connections.connect(uri=settings.MILVUS_URI)
        
        # Check if collection exists
        if not utility.has_collection(safe_collection_name):
            print(f"Collection {safe_collection_name} does not exist")
            return False
        
        # Get the collection
        collection = Collection(safe_collection_name)
        collection.load()
        
        # Delete entities where source_file_id matches the file_id
        # Note: This uses the metadata that was stored when the file was ingested
        expr = f'source_file_id == {file_id}'
        
        # Execute the deletion
        collection.delete(expr)
        
        # Flush to ensure deletion is persisted
        collection.flush()
        
        print(f"Successfully removed vectors for file {file_id} from collection {safe_collection_name}")
        return True
        
    except Exception as e:
        print(f"Error removing file vectors from collection: {str(e)}")
        return False

@router.delete("/{conversation_id}/collection", operation_id="api_collections_delete_conversation_collection")
def delete_conversation_collection(
    conversation_id: str,
    delete_from_milvus: bool = Query(True, description="Whether to also delete the collection from Milvus"),
    current_user: models.User = Depends(get_current_user),  # Regular users can delete their own
    db: Session = Depends(get_db)
):
    """
    Delete a user's conversation collection.
    
    This will:
    1. Delete all files in the conversation from database, MinIO, and vector store
    2. Delete the conversation collection from Milvus
    3. Keep the conversation record but remove all files
    
    Users can only delete their own conversation collections.
    This effectively "resets" the conversation to have no files/context.
    """
    # Check if conversation exists and belongs to user
    conversation = crud.get_conversation(db, conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found"
        )
    
    if conversation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this conversation"
        )
    
    # Get all files in this conversation
    files = crud.get_conversation_files(db, conversation_id)
    
    if not files:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No files found in this conversation to delete"
        )
    
    collection_name = conversation_collection_name(conversation_id)
    deleted_files = []
    
    # Delete all files from the conversation
    for file in files:
        try:
            # Delete from MinIO
            minio_service.delete_file(file.file_path)
            
            # Delete from database
            crud.delete_file_storage(db, file.id)
            
            deleted_files.append({
                "id": file.id,
                "filename": file.original_filename,
                "file_path": file.file_path
            })
            
        except Exception as e:
            print(f"Error deleting file {file.id}: {str(e)}")
            # Continue with other files even if one fails
    
    # Delete the entire collection from Milvus if requested
    if delete_from_milvus:
        try:
            from app.utils.string_utils import sanitize_collection_name
            safe_collection_name = sanitize_collection_name(collection_name)
            success = ingestion_service.delete_collection(safe_collection_name)
            if success:
                print(f"Deleted Milvus collection: {safe_collection_name}")
            else:
                print(f"Warning: Could not delete Milvus collection: {safe_collection_name}")
        except Exception as e:
            print(f"Error deleting Milvus collection: {str(e)}")
            # Continue even if Milvus deletion fails
    
    return {
        "detail": "Conversation collection deleted successfully",
        "conversation_id": conversation_id,
        "collection_name": collection_name,
        "deleted_files_count": len(deleted_files),
        "deleted_files": deleted_files,
        "deleted_from_milvus": delete_from_milvus
    }

@router.get("/{conversation_id}/files/{file_id}/download", operation_id="api_collections_download_file")
def download_file_from_conversation(
    conversation_id: str,
    file_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Securely download a file from user's conversation collection.
    
    This endpoint:
    1. Validates that the conversation belongs to the user
    2. Validates that the file belongs to the conversation
    3. Streams the file content directly from MinIO
    4. Requires authentication for every download
    
    Users can only download files from their own conversations.
    """
    # Check if conversation exists and belongs to user
    conversation = crud.get_conversation(db, conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found"
        )
    
    if conversation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this conversation"
        )
    
    # Check if file exists and belongs to this conversation
    file = crud.get_file_storage(db, file_id)
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File with ID {file_id} not found"
        )
    
    if file.conversation_id != conversation_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File does not belong to this conversation"
        )
    
    if file.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to download this file"
        )
    
    # Download file from MinIO
    success, file_data = minio_service.download_file(file.file_path)
    
    if not success or not file_data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download file from storage"
        )
    
    # Create streaming response
    def generate():
        try:
            file_data.seek(0)  # Ensure we're at the beginning
            while True:
                chunk = file_data.read(8192)  # Read in 8KB chunks
                if not chunk:
                    break
                yield chunk
        finally:
            file_data.close()
    
    # Return streaming response with appropriate headers
    return StreamingResponse(
        generate(),
        media_type=file.mime_type or "application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{file.original_filename}"',
            "Content-Length": str(file.file_size) if file.file_size else None
        }
    )