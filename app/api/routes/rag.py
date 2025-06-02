from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db import crud, models, schemas
from app.db.database import get_db
from app.utils.auth import get_current_user, get_admin_access
from app.services.rag_service import RagChatService
from app.config import settings
from app.utils.string_utils import sanitize_collection_name

router = APIRouter()

# Initialize the RAG service
rag_service = RagChatService(
    embedding_url=settings.REMOTE_EMBEDDER_URL,
    milvus_uri=settings.MILVUS_URI
)

@router.get("/collections", response_model=schemas.CollectionsResponse, operation_id="api_rag_list_collections")
async def list_collections(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all available vector store collections for RAG.
    Regular users can only see non-admin collections.
    Admin users can see all collections.
    """
    if current_user.role == models.UserRole.ADMIN:
        # Admin users can see all collections
        collections = crud.get_all_collections(db)
    else:
        # Regular users can only see non-admin collections (public collections)
        collections = db.query(models.Collection).filter(
            models.Collection.is_admin_only == False,
            models.Collection.is_active == True
        ).all()
    
    # Get collection info with document count from Milvus
    milvus_collections = rag_service.list_available_collections()
    
    collection_infos = []
    for collection in collections:
        # Default document count (if not found in Milvus)
        doc_count = 0
        
        # Try to find count in Milvus collections
        if collection.name in milvus_collections:
            # In a real implementation, you'd fetch the count from Milvus
            # This is a placeholder
            doc_count = -1  # Indicates "available but count unknown"
        
        collection_infos.append(schemas.CollectionInfo(
            name=collection.name,
            description=collection.description,
            document_count=doc_count,
            is_admin_only=collection.is_admin_only
        ))
    
    return schemas.CollectionsResponse(collections=collection_infos)

@router.post("/chat", response_model=schemas.RagChatResponse, operation_id="api_rag_chat_with_collection")
async def rag_chat(
    request: schemas.RagChatRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Chat with RAG-enabled LLM using a specific knowledge collection.
    """
    try:
        # Check if collection exists and user has access
        collection = crud.get_collection_by_name(db, request.collection_name)
        if not collection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection '{request.collection_name}' not found"
            )
        
        # Check permission for admin-only collections
        if collection.is_admin_only and current_user.role != models.UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to use this collection"
            )
        
        # Get response from RAG service
        response = rag_service.get_rag_response(
            db=db,
            user_id=current_user.id,
            message=request.message,
            collection_name=request.collection_name,
            conversation_id=request.conversation_id,
            meta_data=request.meta_data
        )
        
        return schemas.RagChatResponse(
            response=response["answer"],
            conversation_id=response["conversation_id"],
            collection_name=request.collection_name,
            meta_data=response.get("meta_data")
        )
    
    except Exception as e:
        # Handle other exceptions
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing RAG chat: {str(e)}"
        )

@router.post("/chat/stream", operation_id="api_rag_stream_chat_with_collection")
async def stream_rag_chat(
    request: schemas.RagChatRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Stream chat responses with RAG-enabled LLM using a specific knowledge collection.
    """
    try:
        # Check if collection exists and user has access
        collection = crud.get_collection_by_name(db, request.collection_name)
        if not collection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection '{request.collection_name}' not found"
            )
        
        # Check permission for admin-only collections
        if collection.is_admin_only and current_user.role != models.UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to use this collection"
            )
        
        # Create streaming response
        return StreamingResponse(
            rag_service.get_streaming_rag_response(
                db=db,
                user_id=current_user.id,
                message=request.message,
                collection_name=request.collection_name,
                conversation_id=request.conversation_id,
                meta_data=request.meta_data
            ),
            media_type="text/event-stream"
        )
    
    except Exception as e:
        # Handle exceptions
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing streaming RAG chat: {str(e)}"
        )

@router.post("/process-collection/{collection_name}", operation_id="api_rag_process_collection_files")
async def process_collection_files(
    collection_name: str,
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(get_admin_access),  # Admin only
    db: Session = Depends(get_db)
):
    """
    Process all files in a collection that haven't been processed yet.
    This is an admin-only endpoint that runs in the background.
    """
    collection = crud.get_collection_by_name(db, collection_name)
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection '{collection_name}' not found"
        )
    
    # Get unprocessed files in the collection
    collection_files = db.query(models.CollectionFile).filter(
        models.CollectionFile.collection_id == collection.id,
        models.CollectionFile.is_processed == False
    ).all()
    
    if not collection_files:
        return {"detail": "No unprocessed files found in collection"}
    
    # Add processing task to background
    # In a real implementation, this would process files one by one
    background_tasks.add_task(
        process_files_background,
        db_session=db,
        collection_files=collection_files,
        collection_name=collection_name
    )
    
    return {
        "detail": f"Processing {len(collection_files)} files in the background",
        "collection": collection_name,
        "files_count": len(collection_files)
    }

# Background processing function
async def process_files_background(db_session: Session, collection_files: List[models.CollectionFile], collection_name: str):
    """Process files in the background."""
    from app.services.minio_service import MinioService
    from app.services.ingestion_service import DocumentIngestionService
    
    # Initialize services
    minio_service = MinioService()
    ingestion_service = DocumentIngestionService()
    
    # Sanitize collection name for Milvus
    safe_collection_name = sanitize_collection_name(collection_name)
    
    for cf in collection_files:
        try:
            # Get file info
            file = db_session.query(models.FileStorage).filter(models.FileStorage.id == cf.file_id).first()
            if not file:
                continue
            
            # Download file from MinIO
            download_success, file_data = minio_service.download_file(file.file_path)
            if not download_success:
                continue
            
            # Process file for vector storage
            num_docs = ingestion_service.ingest_file_object(
                file_obj=file_data,
                filename=file.filename,
                collection_name=safe_collection_name,
                metadata={"source_file_id": file.id, "file_name": file.original_filename}
            )
            
            # Update collection file status
            cf.is_processed = True
            db_session.commit()
            
        except Exception as e:
            print(f"Error processing file {file.id} for collection {collection_name}: {e}")
            continue

@router.post("/chat/conversation", response_model=schemas.RagChatResponse, operation_id="api_rag_chat_with_conversation")
async def conversation_rag_chat(
    request: schemas.ConversationRagChatRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Chat with RAG-enabled LLM using files from a specific conversation.
    """
    try:
        # Check if conversation exists and user has access
        conversation = crud.get_conversation(db, request.conversation_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation '{request.conversation_id}' not found"
            )
        
        # Check permission for the conversation
        if conversation.user_id != current_user.id and current_user.role != models.UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this conversation"
            )
        
        # Get response from RAG service using conversation files
        response = rag_service.get_conversation_rag_response(
            db=db,
            user_id=current_user.id,
            message=request.message,
            conversation_id=request.conversation_id,
            meta_data=request.meta_data
        )
        
        return schemas.RagChatResponse(
            response=response["answer"],
            conversation_id=response["conversation_id"],
            collection_name="conversation_files",  # Using a placeholder since we're not using a collection
            meta_data=response.get("meta_data")
        )
    
    except Exception as e:
        # Handle other exceptions
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing conversation RAG chat: {str(e)}"
        )

@router.post("/chat/conversation/stream", operation_id="api_rag_stream_chat_with_conversation")
async def stream_conversation_rag_chat(
    request: schemas.ConversationRagChatRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Stream chat responses with RAG-enabled LLM using files from a specific conversation.
    """
    try:
        # Check if conversation exists and user has access
        conversation = crud.get_conversation(db, request.conversation_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation '{request.conversation_id}' not found"
            )
        
        # Check permission for the conversation
        if conversation.user_id != current_user.id and current_user.role != models.UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this conversation"
            )
        
        # Create streaming response
        return StreamingResponse(
            rag_service.get_streaming_conversation_rag_response(
                db=db,
                user_id=current_user.id,
                message=request.message,
                conversation_id=request.conversation_id,
                meta_data=request.meta_data
            ),
            media_type="text/event-stream"
        )
    
    except Exception as e:
        # Handle exceptions
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing streaming conversation RAG chat: {str(e)}"
        )
