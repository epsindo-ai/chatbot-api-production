from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, File, Form, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse, JSONResponse
from typing import List, Dict, Any, Optional, Union
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import json
import uuid
import time
import requests
from pymilvus import connections, utility
import asyncio
import logging
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
import os

from app.utils.auth import get_current_active_user
from app.db import models, schemas, crud
from app.services.llm_service import get_llm_response, get_streaming_llm_response, generate_conversation_headline
from app.services.rag_service import RagChatService, RemoteVectorStoreManager
from app.services.minio_service import MinioService
from app.services.title_service import TitleGenerationService
from app.db.database import get_db
from app.config import settings
from app.utils.infinity_embedder import InfinityEmbedder
from app.services.ingestion_service import DocumentIngestionService
from app.utils.string_utils import sanitize_collection_name, conversation_collection_name, sanitize_filename
from app.services.admin_config_service import AdminConfigService
from app.services.rag_config_service import RAGConfigService

"""
Unified Chat API

This module provides a unified interface for both regular chat and RAG-enabled chat.
It combines the functionality of the separate chat and RAG endpoints into a single API.

Key features:
1. Support for both regular chat and RAG-enabled chat through a single endpoint
2. Option to use predefined (admin) collections for RAG
3. Ability to attach user files to conversations and use them for RAG
4. Background processing of uploaded files for vector embedding
5. File storage in MinIO and vector data in Milvus

Usage:
- For regular chat: don't provide collection_name or files
- For RAG with admin collections: provide collection_name
- For RAG with user files: provide files (list of file IDs)

Important: You cannot use both a predefined collection and user files simultaneously.
The system will return an error if both collection_name and files are provided.

Input validation:
- Default placeholder values like "string" are automatically filtered out
- Invalid file IDs are skipped rather than causing the entire request to fail
- Empty file lists will fall back to regular chat without RAG

The system automatically determines whether to use RAG based on:
1. If collection_name is provided, it will use the specified admin collection for RAG
2. If files are provided or already attached to the conversation, it will use those for RAG
3. Otherwise, it will fall back to regular chat without RAG

Each file is tied to the conversation and stored in MinIO, with its vector representation in Milvus.
"""

router = APIRouter()

# WebSocket connection manager for file processing notifications
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, conversation_id: str):
        await websocket.accept()
        if conversation_id not in self.active_connections:
            self.active_connections[conversation_id] = []
        self.active_connections[conversation_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, conversation_id: str):
        if conversation_id in self.active_connections:
            self.active_connections[conversation_id].remove(websocket)
            if not self.active_connections[conversation_id]:
                del self.active_connections[conversation_id]
    
    async def send_message(self, message: dict, conversation_id: str):
        if conversation_id in self.active_connections:
            for connection in self.active_connections[conversation_id]:
                try:
                    await connection.send_text(json.dumps(message))
                except:
                    # Remove dead connections
                    self.active_connections[conversation_id].remove(connection)

manager = ConnectionManager()

# Initialize services
rag_service = RagChatService(
    milvus_uri=settings.MILVUS_URI
)
minio_service = MinioService()
vector_store_manager = RemoteVectorStoreManager(
    milvus_uri=settings.MILVUS_URI
)
ingestion_service = DocumentIngestionService()

# Define the UnifiedChatRequest schema here if it's not in schemas.py
class UnifiedChatRequest(schemas.ChatRequest):
    """Simplified unified schema for chat - collections and files are auto-bound."""
    pass  # All needed fields are in the base ChatRequest

# Define the UnifiedChatResponse schema here if it's not in schemas.py
class UnifiedChatResponse(schemas.ChatResponse):
    """Simplified unified response schema for chat."""
    used_rag: bool = False

class UnifiedStreamingChatResponse(schemas.StreamingChatResponse):
    """Simplified unified streaming response schema."""
    used_rag: bool = False

class EmbeddingRequest(BaseModel):
    """Request model for embedding generation."""
    text: Union[str, List[str]]
    model: Optional[str] = None

class EmbeddingResponse(BaseModel):
    """Response model for embedding generation."""
    embeddings: Union[List[float], List[List[float]]]
    model: str
    dimension: int
    text_count: int

class ConversationDeletionRequest(BaseModel):
    """Request body for deleting user conversations with granular control."""
    
    # File and collection cleanup options
    delete_files_and_collections: bool = Field(
        True, 
        description="Whether to also delete files and collections associated with conversations"
    )
    
    # Conversation type filters
    delete_regular_chats: bool = Field(
        True, 
        description="Whether to delete regular chat conversations (no files or collections)"
    )
    delete_user_file_conversations: bool = Field(
        True, 
        description="Whether to delete conversations with user-uploaded files and their collections"
    )
    delete_global_collection_conversations: bool = Field(
        True, 
        description="Whether to delete conversations linked to global collections (admin knowledge bases)"
    )
    delete_null_conversations: bool = Field(
        True, 
        description="Whether to delete conversations with null/missing conversation types (cleanup orphaned conversations)"
    )

@router.post("/", response_model=UnifiedChatResponse)
async def unified_chat(
    request: UnifiedChatRequest,
    background_tasks: BackgroundTasks,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Simplified unified chat endpoint.
    Collections and files are auto-bound through conversation initiation and upload processes.
    """
    print(f"DEBUG: Processing chat request for conversation_id={request.conversation_id}")
    
    # Process the conversation ID
    conversation_id = request.conversation_id
    if not conversation_id or conversation_id == "string":
        conversation_id = str(uuid.uuid4())
    
    # Get the conversation if it exists
    conversation = None
    if conversation_id:
        conversation = crud.get_conversation(db, conversation_id)
        if conversation:
            print(f"DEBUG: Found conversation {conversation_id}, type={conversation.conversation_type}")
        else:
            print(f"DEBUG: Conversation {conversation_id} not found")
    
    # Handle RAG request based on conversation type
    if conversation and conversation.conversation_type == models.ConversationType.GLOBAL_COLLECTION:
        # Check if the global collection has changed and handle based on behavior setting
        if crud.is_global_collection_outdated(db, conversation_id):
            from app.services.admin_config_service import AdminConfigService
            behavior = AdminConfigService.get_config(db, models.AdminConfig.KEY_GLOBAL_COLLECTION_BEHAVIOR, "auto_update")
            
            if behavior == "readonly_on_change":
                return UnifiedChatResponse(
                    status_code=423,  # Locked
                    error="The knowledge base has been updated. This conversation is now read-only. Please start a new conversation or migrate to the current knowledge base.",
                    response="",
                    conversation_id=conversation_id,
                    used_rag=False
                )
            elif behavior == "auto_update":
                # Auto-update the conversation to use the current global collection
                updated_conversation = crud.update_conversation_to_current_global_collection(db, conversation_id)
                if updated_conversation:
                    conversation = updated_conversation
                    print(f"DEBUG: Auto-updated conversation {conversation_id} to current global collection")
        
        # This is a global collection conversation, so we use the linked collection
        print(f"DEBUG: Using existing global collection conversation (id={conversation.id})")
        collection_name = None
        if conversation.linked_global_collection:
            collection = conversation.linked_global_collection
            collection_name = collection.name
            print(f"DEBUG: Using linked global collection: {collection_name}, collection_id={collection.id}")
            
            # Check if the collection exists in Milvus
            from app.utils.string_utils import sanitize_collection_name
            
            safe_collection_name = sanitize_collection_name(collection_name)
            milvus_collection_exists = vector_store_manager.collection_exists(safe_collection_name)
            print(f"DEBUG: Does collection exist in Milvus? '{safe_collection_name}' -> {milvus_collection_exists}")
            
            if not milvus_collection_exists:
                print(f"DEBUG: WARNING - Global collection '{safe_collection_name}' not found in Milvus vectorstore")
                
        else:
            print(f"DEBUG: WARNING - Global collection conversation without linked collection. conversation_id={conversation.id}, linked_id={conversation.linked_global_collection_id}")
            
            # Try to repair the link if possible
            if conversation.linked_global_collection_id:
                print(f"DEBUG: Attempting to repair missing linked collection object. Looking for collection id={conversation.linked_global_collection_id}")
                try:
                    collection = crud.get_collection(db, conversation.linked_global_collection_id)
                    if collection:
                        collection_name = collection.name
                        print(f"DEBUG: Found collection by id: {collection_name}, collection_id={collection.id}")
                    else:
                        print(f"DEBUG: ERROR - Collection not found with id={conversation.linked_global_collection_id}")
                except Exception as e:
                    print(f"DEBUG: ERROR - Failed to repair collection link: {str(e)}")
        
    # Handle RAG request
    try:
        # Handle the different cases for RAG
        if conversation and conversation.conversation_type == models.ConversationType.GLOBAL_COLLECTION and collection_name:
            print(f"DEBUG: Processing RAG request with admin collection {collection_name}")
            
            # Save the user message first
            user_message = schemas.MessageCreate(
                conversation_id=conversation_id,
                role="user",
                content=request.message
            )
            crud.create_message(db, user_message)
            
            # Get response from RAG service
            response = await rag_service.get_rag_response(
                db=db,
                user_id=current_user.id,
                message=request.message,
                collection_name=collection_name,
                conversation_id=conversation_id,
                meta_data=request.meta_data
            )
            
            # Check if messages were created
            messages = crud.get_conversation_messages(db, conversation_id)
            print(f"DEBUG: Found {len(messages)} messages for conversation {conversation_id}")
            for msg in messages:
                print(f"DEBUG: Message {msg.id}: role={msg.role}, has_context={'Yes' if msg.rag_context else 'No'}")
            
            # Add background task to update the conversation title based on the new message
            background_tasks.add_task(
                process_title_update,
                db_conn_string=settings.DATABASE_URL,
                conversation_id=conversation_id,
                user_message=request.message
            )
            
            return UnifiedChatResponse(
                status_code=200,
                error=None,
                response=response["response"],
                conversation_id=response["conversation_id"],
                meta_data=response["meta_data"],
                used_rag=True
            )
            
        elif conversation and conversation.conversation_type == models.ConversationType.USER_FILES:
            # Special case for using files
            print(f"DEBUG: Processing RAG request with user files")
            
            # Save the user message
            user_message = schemas.MessageCreate(
                conversation_id=conversation_id,
                role="user",
                content=request.message
            )
            crud.create_message(db, user_message)
            
            # Create a temporary collection name based on conversation ID
            temp_collection_name = conversation_collection_name(conversation_id)
            
            # Get response from RAG service's conversation method
            response = await rag_service.get_conversation_rag_response(
                db=db,
                conversation_id=conversation_id,
                query=request.message,
                user_id=current_user.id,
                conversation_collection=temp_collection_name
            )
            
            # Save the assistant's response
            assistant_message = schemas.MessageCreate(
                conversation_id=conversation_id,
                role="assistant",
                content=response
            )
            crud.create_message(db, assistant_message)
            
            # Check if messages were created
            messages = crud.get_conversation_messages(db, conversation_id)
            print(f"DEBUG: Found {len(messages)} messages for conversation {conversation_id}")
            
            # Add background task to update the conversation title based on the new message
            background_tasks.add_task(
                process_title_update,
                db_conn_string=settings.DATABASE_URL,
                conversation_id=conversation_id,
                user_message=request.message
            )
            
            return UnifiedChatResponse(
                status_code=200,
                error=None,
                response=response,
                conversation_id=conversation_id,
                meta_data=request.meta_data,
                used_rag=True
            )
            
        # Regular chat (no RAG)
        else:
            print("DEBUG: Processing regular chat request (no RAG)")
            
            # If conversation doesn't exist, create a new one
            db_conversation = crud.get_conversation(db, conversation_id)
            
            if not db_conversation:
                db_conversation = crud.create_conversation(db, current_user.id, request.meta_data)
                conversation_id = db_conversation.id
            
            # Get response from LLM
            response = await get_llm_response(
                db=db,
                user_id=current_user.id,
                message=request.message,
                conversation_id=conversation_id,
                meta_data=request.meta_data
            )
            
            # Check if messages were created
            messages = crud.get_conversation_messages(db, conversation_id)
            print(f"DEBUG: Found {len(messages)} messages for conversation {conversation_id}")
            
            # Add background task to update the conversation title based on the new message
            background_tasks.add_task(
                process_title_update,
                db_conn_string=settings.DATABASE_URL,
                conversation_id=conversation_id,
                user_message=request.message
            )
            
            return UnifiedChatResponse(
                status_code=200,
                error=None,
                response=response,
                conversation_id=conversation_id,
                meta_data=request.meta_data,
                used_rag=False
            )
    
    except Exception as e:
        print(f"DEBUG: Error processing chat request: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return UnifiedChatResponse(
            status_code=500,
            error=f"Error: {str(e)}",
            response="",
            conversation_id=conversation_id,
            meta_data=request.meta_data,
            used_rag=False
        )

@router.post("/stream")
async def unified_stream_chat(
    request: UnifiedChatRequest,
    background_tasks: BackgroundTasks,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Simplified unified streaming chat endpoint.
    Collections and files are auto-bound through conversation initiation and upload processes.
    """
    # Process the conversation ID
    conversation_id = request.conversation_id
    if not conversation_id or conversation_id == "string":
        conversation_id = str(uuid.uuid4())
    
    # Track conversation data
    conversation_data = {
        "id": conversation_id,
        "used_rag": False
    }
    
    # Get the conversation if it exists
    conversation = None
    if conversation_id:
        conversation = crud.get_conversation(db, conversation_id)
    
    # Handle conversation type-based logic
    if conversation and conversation.conversation_type == models.ConversationType.GLOBAL_COLLECTION:
        # Check if the global collection has changed and handle based on behavior setting
        if crud.is_global_collection_outdated(db, conversation_id):
            from app.services.admin_config_service import AdminConfigService
            behavior = AdminConfigService.get_config(db, models.AdminConfig.KEY_GLOBAL_COLLECTION_BEHAVIOR, "auto_update")
            
            if behavior == "readonly_on_change":
                return StreamingResponse(
                    generate_error_stream("The knowledge base has been updated. This conversation is now read-only. Please start a new conversation or migrate to the current knowledge base."),
                    media_type="application/x-ndjson"
                )
            elif behavior == "auto_update":
                # Auto-update the conversation to use the current global collection
                updated_conversation = crud.update_conversation_to_current_global_collection(db, conversation_id)
                if updated_conversation:
                    conversation = updated_conversation
                    print(f"DEBUG: Auto-updated conversation {conversation_id} to current global collection")
        
        # Use the linked global collection
        collection = conversation.linked_global_collection
        if not collection:
            return StreamingResponse(
                generate_error_stream("The linked global collection was not found."),
                media_type="application/x-ndjson"
            )
        # Add admin prefix for global collections since they're stored with admin prefix in Milvus
        collection_name = f"admin_{collection.name}"
        
    
    # Check if files are still processing before starting the stream
    if conversation and conversation.conversation_type == models.ConversationType.USER_FILES:
        # Get files attached to this conversation
        conversation_files = crud.get_conversation_files(db, conversation_id)
        
        # Check if any files are still being processed
        files_processing = False
        for file in conversation_files:
            if file.file_metadata is None or not file.file_metadata.get("is_processed_for_rag", False):
                # File exists but hasn't been processed yet
                files_processing = True
                break
        
        # If files are still processing, return a message
        if files_processing:
            return StreamingResponse(
                generate_error_stream("Files are still being processed. Please wait a moment before chatting."),
                media_type="application/x-ndjson"
            )
    
    async def stream_response():
        try:
            # Get or create conversation first to get the conversation_id
            db_conversation = None
            if conversation_data["id"]:
                db_conversation = crud.get_conversation(db, conversation_data["id"])
            
            # If conversation doesn't exist, create a new one
            if not db_conversation:
                # Create a new conversation
                db_conversation = crud.create_conversation(db, current_user.id, request.meta_data)
                conversation_data["id"] = db_conversation.id
            
            # NOTE: Save user message once here rather than in each service function
            user_message = schemas.MessageCreate(
                conversation_id=conversation_data["id"],
                role="user",
                content=request.message
            )
            crud.create_message(db, user_message)
            
            # Add background task to generate/update the conversation title based on the new message
            background_tasks.add_task(
                process_title_update,
                db_conn_string=settings.DATABASE_URL,
                conversation_id=conversation_data["id"],
                user_message=request.message
            )
            
            # Scenario 1: RAG with admin collection
            if conversation and conversation.conversation_type == models.ConversationType.GLOBAL_COLLECTION and collection_name:
                conversation_data["used_rag"] = True
                
                # Check if collection exists
                available_collections = rag_service.list_available_collections()
                if collection_name not in available_collections:
                    yield json.dumps({
                        "status": "error",
                        "message": f"Collection '{collection_name}' not found. Available collections: {', '.join(available_collections)}"
                    }) + "\n"
                    return
                
                # Use RAG with streaming
                try:
                    # Initial message
                    yield json.dumps({
                        "status": "info",
                        "message": "Using RAG with collection: " + collection_name
                    }) + "\n"
                    
                    # Get streaming response from RAG service - don't save user message again
                    stream_gen = rag_service.get_streaming_rag_response(
                        db=db,
                        user_id=current_user.id,
                        message=request.message,
                        collection_name=collection_name,
                        conversation_id=conversation_data["id"],
                        meta_data=request.meta_data,
                        save_user_message=False  # We already saved it
                    )
                    
                    # Handle the async generator
                    async for chunk in stream_gen:
                        yield json.dumps({
                            "status": "token",
                            "token": chunk
                        }) + "\n"
                    
                    # Send final message with metadata
                    yield json.dumps({
                        "status": "done",
                        "conversation_id": conversation_data["id"],
                        "used_rag": True
                    }) + "\n"
                    
                except Exception as e:
                    yield json.dumps({
                        "status": "error",
                        "message": f"Error in RAG response: {str(e)}"
                    }) + "\n"
                
            else:
                # Scenario 2: Check for files attached to conversation
                conversation_files = crud.get_conversation_files(db, conversation_data["id"])
                
                if conversation_files and conversation and conversation.conversation_type == models.ConversationType.USER_FILES:
                    conversation_data["used_rag"] = True
                    
                    # Create a temporary collection for this conversation
                    temp_collection_name = conversation_collection_name(conversation_data["id"])
                    
                    # Double-check that all files are processed
                    all_processed = True
                    for file in conversation_files:
                        if file.file_metadata is None or not file.file_metadata.get("is_processed_for_rag", False):
                            all_processed = False
                            break
                    
                    if not all_processed:
                        yield json.dumps({
                            "status": "error",
                            "message": "Some files are still being processed. Please wait a moment before chatting."
                        }) + "\n"
                        return
                    
                    # Use conversation-based RAG with streaming
                    try:
                        # Initial message
                        yield json.dumps({
                            "status": "info",
                            "message": "Using conversation files for RAG"
                        }) + "\n"
                        
                        # Get streaming response from conversation RAG - don't save user message again
                        stream_gen = rag_service.get_streaming_conversation_rag_response(
                            db=db,
                            conversation_id=conversation_data["id"],
                            query=request.message,
                            user_id=current_user.id,
                            conversation_collection=temp_collection_name,
                            save_user_message=False  # We already saved it
                        )
                        
                        # Since this is an async generator, we need to iterate through it with async for
                        async for chunk in stream_gen:
                            yield json.dumps({
                                "status": "token",
                                "token": chunk
                            }) + "\n"
                        
                        # Send final message with metadata
                        yield json.dumps({
                            "status": "done",
                            "conversation_id": conversation_data["id"],
                            "used_rag": True
                        }) + "\n"
                        
                    except Exception as e:
                        yield json.dumps({
                            "status": "error",
                            "message": f"Error in conversation RAG response: {str(e)}"
                        }) + "\n"
                    
                else:
                    # Scenario 3: Regular chat (no RAG) - don't save user message again
                    stream_gen = get_streaming_llm_response(
                        db=db,
                        user_id=current_user.id,
                        message=request.message,
                        conversation_id=conversation_data["id"],
                        meta_data=request.meta_data,
                        save_user_message=False  # We already saved it
                    )
                    
                    # Handle the async generator
                    async for chunk in stream_gen:
                        yield json.dumps({
                            "status": "token",
                            "token": chunk
                        }) + "\n"
                    
                    # Send final message with metadata
                    yield json.dumps({
                        "status": "done",
                        "conversation_id": conversation_data["id"],
                        "used_rag": False
                    }) + "\n"
                
        except Exception as e:
            # Log the exception
            print(f"Error in stream_response: {str(e)}")
            
            # Return error to client
            yield json.dumps({
                "status": "error",
                "message": f"Error: {str(e)}"
            }) + "\n"
    
    # Return streaming response
    return StreamingResponse(
        stream_response(),
        media_type="application/x-ndjson"
    )

# Helper function to process title updates in background
async def process_title_update(db_conn_string: str, conversation_id: str, user_message: str):
    """Background task to process title updates for conversations."""
    try:
        # Create a new database session for this background task
        engine = create_engine(db_conn_string)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        try:
            # Process the message using our title service
            await TitleGenerationService.process_new_message(db, conversation_id, user_message)
        finally:
            db.close()
    except Exception as e:
        print(f"Error processing title update: {str(e)}")

# Helper function for processing files
async def process_file_for_rag(db: Session, file_id: str, collection_name: str):
    """Process a file for RAG in the background."""
    try:
        # Get file info
        file = crud.get_file_storage(db, file_id)
        if not file:
            return
        
        # Download file from MinIO
        download_success, file_data = minio_service.download_file(file.file_path)
        if not download_success:
            return
        
        # Ensure collection name is valid for Milvus
        safe_collection_name = sanitize_collection_name(collection_name)
        
        # Process file for vector storage
        num_docs = ingestion_service.ingest_file_object(
            file_obj=file_data,
            filename=file.filename,
            collection_name=safe_collection_name,
            metadata={"source_file_id": file.id, "file_name": file.original_filename}
        )
        
        # Update file metadata
        crud.update_file_storage(db, file_id, {
            "file_metadata": {
                **(file.file_metadata or {}),
                "is_processed_for_rag": True,
                "chunk_count": num_docs,
                "processed_at": datetime.utcnow().isoformat()
            }
        })
        
    except Exception as e:
        print(f"Error processing file {file_id} for RAG: {e}")

@router.get("/conversations", response_model=List[schemas.Conversation])
async def get_user_conversations(
    skip: int = 0,
    limit: int = 100,
    include_empty: bool = True,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all conversations for the current user.
    Set include_empty=false to exclude conversations without messages.
    """
    conversations = crud.get_user_conversations(db, current_user.id, skip, limit, include_empty)
    return conversations

@router.get("/conversations/{conversation_id}", response_model=schemas.ConversationWithMessages)
async def get_conversation(
    conversation_id: str,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific conversation with all messages.
    """
    conversation = crud.get_conversation(db, conversation_id)
    
    if not conversation or conversation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    messages = crud.get_conversation_messages(db, conversation_id)
    
    return {
        **conversation.__dict__,
        "messages": messages
    }

@router.get("/conversations/{conversation_id}/files", response_model=schemas.ConversationWithFiles)
async def get_conversation_with_files(
    conversation_id: str,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific conversation with its associated files.
    """
    conversation = crud.get_conversation(db, conversation_id)
    
    if not conversation or conversation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    files = crud.get_conversation_files(db, conversation_id)
    
    # Get the display file if one is attached
    display_file = None
    if conversation.display_file_id:
        display_file = crud.get_file_storage(db, conversation.display_file_id)
    
    response_dict = {
        **conversation.__dict__,
        "files": files
    }
    
    return response_dict

@router.delete("/conversations/all", operation_id="api_chat_delete_all_user_conversations")
def delete_all_user_conversations(
    request: ConversationDeletionRequest,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete user's own conversations with granular control over conversation types.
    
    This will:
    1. Delete selected types of user's conversations from database
    2. Optionally delete all files associated with those conversations from MinIO
    3. Optionally delete user collections from Milvus vector store
    
    Conversation Types:
    - REGULAR: Basic chat conversations (no files or collections)
    - USER_FILES: Conversations with user-uploaded files and collections
    - GLOBAL_COLLECTION: Conversations linked to admin knowledge bases
    - NULL/ORPHANED: Conversations with missing or null conversation types (cleanup)
    
    Request Body Options:
    - delete_files_and_collections: Whether to clean up files and vector collections
    - delete_regular_chats: Whether to include regular chat conversations
    - delete_user_file_conversations: Whether to include conversations with user files
    - delete_global_collection_conversations: Whether to include global collection conversations
    - delete_null_conversations: Whether to include orphaned conversations with null types
    
    Users can only delete their own conversations.
    This operation cannot be undone.
    """
    deleted_stats = {
        "conversations_deleted": 0,
        "files_deleted": 0,
        "collections_deleted": 0,
        "regular_conversations_deleted": 0,
        "user_files_conversations_deleted": 0,
        "global_collection_conversations_deleted": 0,
        "null_conversations_deleted": 0,  # New: track conversations with null/missing type
        "errors": []
    }
    
    try:
        # Get all user's conversations
        user_conversations = crud.get_user_conversations(db, current_user.id)
        
        if not user_conversations:
            return {
                "detail": "No conversations found to delete",
                "deleted_stats": deleted_stats
            }
        
        # Filter conversations based on user's preferences
        conversations_to_delete = []
        for conversation in user_conversations:
            should_delete = False
            
            # Handle conversations with null/missing conversation type (cleanup orphaned conversations)
            if conversation.conversation_type is None and request.delete_null_conversations:
                should_delete = True
            elif conversation.conversation_type == models.ConversationType.REGULAR and request.delete_regular_chats:
                should_delete = True
            elif conversation.conversation_type == models.ConversationType.USER_FILES and request.delete_user_file_conversations:
                should_delete = True
            elif conversation.conversation_type == models.ConversationType.GLOBAL_COLLECTION and request.delete_global_collection_conversations:
                should_delete = True
            
            if should_delete:
                conversations_to_delete.append(conversation)
        
        if not conversations_to_delete:
            return {
                "detail": "No conversations matching the specified criteria found to delete",
                "deleted_stats": deleted_stats
            }
        
        for conversation in conversations_to_delete:
            try:
                conversation_type = conversation.conversation_type
                
                # Delete associated collections and files if requested
                if request.delete_files_and_collections:
                    # Delete user collection from Milvus if it's a USER_FILES conversation
                    if conversation_type == models.ConversationType.USER_FILES:
                        try:
                            collection_name = conversation_collection_name(conversation.id)
                            safe_collection_name = sanitize_collection_name(collection_name)
                            
                            # Initialize ingestion service
                            ingestion_service = DocumentIngestionService()
                            success = ingestion_service.delete_collection(safe_collection_name)
                            # Always count as successful since non-existent collections are effectively "already deleted"
                            deleted_stats["collections_deleted"] += 1
                            if success:
                                print(f"Successfully deleted Milvus collection: {safe_collection_name}")
                            else:
                                print(f"Milvus collection {safe_collection_name} did not exist (already deleted)")
                        except Exception as e:
                            deleted_stats["errors"].append(f"Error deleting Milvus collection for conversation {conversation.id}: {str(e)}")
                    
                    # Delete files associated with conversation (only USER_FILES conversations have files)
                    if conversation_type == models.ConversationType.USER_FILES:
                        conversation_files = crud.get_conversation_files(db, conversation.id)
                        for file in conversation_files:
                            try:
                                # Initialize MinIO service
                                minio_service = MinioService()
                                minio_service.delete_file(file.file_path)
                                deleted_stats["files_deleted"] += 1
                            except Exception as e:
                                deleted_stats["errors"].append(f"Error deleting file {file.id}: {str(e)}")
                
                # Delete conversation (cascade deletes messages and files automatically)
                success = crud.delete_conversation(db, conversation.id)
                if success:
                    deleted_stats["conversations_deleted"] += 1
                    
                    # Track by conversation type
                    if conversation_type is None:
                        deleted_stats["null_conversations_deleted"] += 1
                    elif conversation_type == models.ConversationType.REGULAR:
                        deleted_stats["regular_conversations_deleted"] += 1
                    elif conversation_type == models.ConversationType.USER_FILES:
                        deleted_stats["user_files_conversations_deleted"] += 1
                    elif conversation_type == models.ConversationType.GLOBAL_COLLECTION:
                        deleted_stats["global_collection_conversations_deleted"] += 1
                else:
                    deleted_stats["errors"].append(f"Failed to delete conversation {conversation.id}")
                    
            except Exception as e:
                deleted_stats["errors"].append(f"Error processing conversation {conversation.id}: {str(e)}")
        
        # Generate summary message
        total_deleted = deleted_stats["conversations_deleted"]
        detail_parts = [f"Successfully deleted {total_deleted} conversations"]
        
        if deleted_stats["regular_conversations_deleted"] > 0:
            detail_parts.append(f"{deleted_stats['regular_conversations_deleted']} regular chat conversations")
        if deleted_stats["user_files_conversations_deleted"] > 0:
            detail_parts.append(f"{deleted_stats['user_files_conversations_deleted']} user file conversations")
        if deleted_stats["global_collection_conversations_deleted"] > 0:
            detail_parts.append(f"{deleted_stats['global_collection_conversations_deleted']} global collection conversations")
        if deleted_stats["null_conversations_deleted"] > 0:
            detail_parts.append(f"{deleted_stats['null_conversations_deleted']} orphaned/null conversations")
        
        detail_message = detail_parts[0]
        if len(detail_parts) > 1:
            detail_message += f" ({', '.join(detail_parts[1:])})"
        
        return {
            "detail": detail_message,
            "deleted_stats": deleted_stats
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete conversations: {str(e)}"
        )

@router.delete("/conversations/{conversation_id}", response_model=Dict[str, Any])
async def delete_conversation(
    conversation_id: str,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete a conversation and all its associated data.
    
    This will:
    1. Delete the conversation from the database (cascade deletes messages and files automatically)
    2. Clean up user collection vectors from Milvus (but preserve global collections)
    3. Remove files from MinIO storage
    
    Users can only delete their own conversations.
    Admin users can delete any conversation.
    """
    # Check if conversation exists
    conversation = crud.get_conversation(db, conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found"
        )
    
    # Check permission - users can only delete their own conversations, admins can delete any
    if conversation.user_id != current_user.id and current_user.role != models.UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this conversation"
        )
    
    # Store conversation info for response
    conversation_type = conversation.conversation_type
    user_id = conversation.user_id
    
    # Get files for cleanup info before deletion
    files = crud.get_conversation_files(db, conversation_id)
    file_count = len(files) if files else 0
    
    # Delete the conversation using the CRUD function
    success = crud.delete_conversation(db, conversation_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete conversation"
        )
    
    return {
        "detail": "Conversation deleted successfully",
        "conversation_id": conversation_id,
        "conversation_type": conversation_type.value if conversation_type else "regular",
        "deleted_files_count": file_count,
        "user_id": user_id
    }

@router.post("/conversations/{conversation_id}/generate-headline", response_model=schemas.Conversation)
async def generate_headline(
    conversation_id: str,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Manually generate or regenerate a headline for a conversation.
    Uses the enhanced title generation service for better quality titles.
    """
    # Check if the conversation exists and belongs to the user
    conversation = crud.get_conversation(db, conversation_id)
    if not conversation or conversation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    # Generate headline using the title service
    title = await TitleGenerationService.update_title_periodic(db, conversation_id)
    
    # Return the updated conversation
    return crud.get_conversation(db, conversation_id)

@router.post("/conversations/{conversation_id}/generate-final-headline", response_model=schemas.Conversation)
async def generate_final_headline(
    conversation_id: str,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Generate a comprehensive final headline for a completed conversation.
    This considers the entire conversation context to create a more detailed title.
    """
    # Check if the conversation exists and belongs to the user
    conversation = crud.get_conversation(db, conversation_id)
    if not conversation or conversation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    # Generate final headline
    title = await TitleGenerationService.generate_final_title(db, conversation_id)
    
    # Return the updated conversation
    return crud.get_conversation(db, conversation_id)

@router.get("/system/health")
async def system_health_check():
    """
    Check the health of all system components.
    """
    health = {
        "status": "healthy",
        "timestamp": time.time(),
        "components": {}
    }
    
    # Check PostgreSQL
    try:
        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            assert result.scalar() == 1
        health["components"]["database"] = {"status": "healthy"}
    except Exception as e:
        health["components"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health["status"] = "degraded"
    
    # Check MinIO
    try:
        minio = MinioService()
        buckets = minio.client.list_buckets()
        health["components"]["minio"] = {
            "status": "healthy", 
            "buckets": len(buckets)
        }
    except Exception as e:
        health["components"]["minio"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health["status"] = "degraded"
    
    # Check Milvus
    try:
        connections.connect(uri=settings.MILVUS_URI)
        collections = utility.list_collections()
        health["components"]["milvus"] = {
            "status": "healthy", 
            "collections": collections
        }
    except Exception as e:
        health["components"]["milvus"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health["status"] = "degraded"
    
    # Check vLLM API
    try:
        response = requests.post(
            f"{settings.OPENAI_API_BASE}/chat/completions",
            headers={"Content-Type": "application/json"},
            json={
                "model": settings.LLM_MODEL,
                "messages": [{"role": "user", "content": "health check"}],
                "max_tokens": 5
            },
            timeout=5
        )
        if response.status_code == 200:
            health["components"]["vllm"] = {"status": "healthy"}
        else:
            health["components"]["vllm"] = {
                "status": "unhealthy",
                "error": f"HTTP {response.status_code}: {response.text}"
            }
            health["status"] = "degraded"
    except Exception as e:
        health["components"]["vllm"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health["status"] = "degraded"
    
    # Check Infinity Embeddings
    try:
        embedder = InfinityEmbedder(
            model=settings.INFINITY_EMBEDDINGS_MODEL,
            infinity_api_url=settings.INFINITY_API_URL
        )
        embedding_health = embedder.health_check()
        if embedding_health["status"] == "healthy":
            health["components"]["infinity_embeddings"] = embedding_health
        else:
            health["components"]["infinity_embeddings"] = embedding_health
            health["status"] = "degraded"
    except Exception as e:
        health["components"]["infinity_embeddings"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health["status"] = "degraded"
    
    if any(comp["status"] == "unhealthy" for comp in health["components"].values()):
        health["status"] = "unhealthy"
    
    return JSONResponse(
        status_code=200 if health["status"] != "unhealthy" else 500,
        content=health
    )

# Add the upload endpoint to unified_chat router
@router.post("/upload-file", response_model=List[schemas.FileStorageResponse])
async def upload_file(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    conversation_id: str = Form(...),  # Required, no default
    sync_processing: bool = Form(True),  # Default to synchronous processing
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Upload up to 3 files and process them for RAG.
    
    - conversation_id: Required - The conversation to attach these files to
    - sync_processing: If True (default), wait for processing to complete before returning
    
    When sync_processing=True:
    - Files are processed immediately and conversation is ready for chat
    - Returns "completed" status for successfully processed files
    - Takes longer to respond but conversation is immediately ready
    
    When sync_processing=False:
    - Files are processed in background
    - Returns "pending" status immediately
    - Use /file-status/{conversation_id} to check when ready
    """
    try:
        # Limit the number of files to 3
        if len(files) > 3:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": f"Too many files. Maximum allowed: 3, received: {len(files)}"}
            )
            
        # Check if the conversation exists and belongs to the user
        conversation = crud.get_conversation(db, conversation_id)
        if not conversation:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"detail": f"Conversation {conversation_id} not found"}
            )
        
        if conversation.user_id != current_user.id:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "You don't have access to this conversation"}
            )
        
        result = []
        supported_extensions = ['.pdf', '.txt', '.doc', '.docx', '.csv', '.md']
        max_file_size = 10 * 1024 * 1024  # 10MB
        
        for file in files:
            # Check file type and size
            file_ext = os.path.splitext(file.filename)[1].lower()
            is_supported_type = any(file_ext.endswith(ext) for ext in supported_extensions)
            
            if not is_supported_type:
                result.append({
                    "filename": file.filename,
                    "error": f"Unsupported file type: {file_ext}. Supported types: {', '.join(supported_extensions)}",
                    "processing_status": "failed"
                })
                continue
            
            # Read and upload file to MinIO
            file_content = await file.read()
            file_size = len(file_content)
            
            # Check file size limit (default: 10MB)
            if file_size > max_file_size:
                result.append({
                    "filename": file.filename,
                    "error": f"File too large. Maximum size: {max_file_size/1024/1024}MB",
                    "processing_status": "failed"
                })
                continue
            
            # Generate a safe filename
            timestamp = int(time.time())
            safe_filename = f"{timestamp}_{sanitize_filename(file.filename)}"
            
            # Create directory structure: user_id/conversation_id/
            file_path = f"{current_user.id}/{conversation_id}/{safe_filename}"
            
            # Upload to MinIO
            meta_data = {}
            try:
                # Reset file position
                await file.seek(0)
                
                minio_service.upload_file(
                    file_data=file_content,
                    file_path=file_path,
                    content_type=file.content_type
                )
            except Exception as e:
                result.append({
                    "filename": file.filename,
                    "error": f"Error uploading file: {str(e)}",
                    "processing_status": "failed"
                })
                continue
            
            # Create a new file record in the database
            db_file = crud.create_file_storage(
                db=db,
                file_data=schemas.FileStorageCreate(
                    user_id=current_user.id,
                    filename=safe_filename,
                    original_filename=file.filename,
                    file_path=file_path,
                    file_size=file_size,
                    mime_type=file.content_type,
                    file_metadata=meta_data,
                    conversation_id=conversation_id
                )
            )
            
            # Process files based on sync_processing flag
            if sync_processing and is_supported_type:
                # Process synchronously - wait for completion
                try:
                    # Create collection name for this conversation
                    collection_name = conversation_collection_name(conversation_id)
                    
                    # Process the file synchronously
                    success = await process_file_sync(
                        db_file_id=db_file.id,
                        conversation_id=conversation_id,
                        user_id=current_user.id,
                        collection_name=collection_name
                    )
                    
                    if success:
                        # Refresh the file object to get updated metadata
                        db.refresh(db_file)
                        
                        # Create secure download URL
                        file_dict = schemas.FileStorage.from_orm(db_file).dict()
                        file_dict["download_url"] = f"/api/collections/{conversation_id}/files/{db_file.id}/download"
                        file_dict["processing_status"] = "completed"
                        
                        result.append(file_dict)
                    else:
                        file_dict = schemas.FileStorage.from_orm(db_file).dict()
                        file_dict["download_url"] = f"/api/collections/{conversation_id}/files/{db_file.id}/download"
                        file_dict["processing_status"] = "failed"
                        file_dict["error"] = "Failed to process file for RAG"
                        
                        result.append(file_dict)
                except Exception as e:
                    file_dict = schemas.FileStorage.from_orm(db_file).dict()
                    file_dict["download_url"] = f"/api/collections/{conversation_id}/files/{db_file.id}/download"
                    file_dict["processing_status"] = "failed"
                    file_dict["error"] = f"Processing error: {str(e)}"
                    
                    result.append(file_dict)
            else:
                # Process asynchronously in background
                if is_supported_type:
                    background_tasks.add_task(
                        process_uploaded_file_for_rag,
                        db_file_id=db_file.id,
                        conversation_id=conversation_id,
                        user_id=current_user.id,
                        db_conn_string=settings.DATABASE_URL
                    )
                    
                    result.append({
                        **schemas.FileStorage.from_orm(db_file).dict(),
                        "download_url": f"/api/collections/{conversation_id}/files/{db_file.id}/download",
                        "processing_status": "pending"
                    })
        
        # Update conversation type if any files were processed successfully
        if result and not all(r.get("error", None) for r in result):
            conversation.conversation_type = models.ConversationType.USER_FILES
            db.commit()
        
        # Return file information with processing status for all files
        return result
    except Exception as e:
        print(f"Error uploading files: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": f"Error processing request: {str(e)}"}
        )

# Add the missing process_file_sync function
async def process_file_sync(db_file_id: int, conversation_id: str, user_id: int, collection_name: str) -> bool:
    """Process a file synchronously and wait for completion."""
    try:
        # Create a new database session
        engine = create_engine(settings.DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        try:
            # Initialize ingestion service
            from app.services.ingestion_service import DocumentIngestionService
            ingestion_service = DocumentIngestionService()
            
            # Ensure the collection exists first
            print(f"DEBUG: Ensuring collection exists: {collection_name}")
            await asyncio.to_thread(
                ingestion_service.create_new_collection, 
                collection_name, 
                f"Collection for conversation {conversation_id}"
            )
            
            # Process the file synchronously using thread pool
            success = await asyncio.to_thread(
                process_file_for_collection_sync, 
                db_file_id, 
                collection_name, 
                db, 
                user_id
            )
            
            return success
        finally:
            db.close()
    except Exception as e:
        print(f"Error in process_file_sync: {str(e)}")
        return False

# Helper function to process files for collections
def process_file_for_collection(file_id: int, collection_id: int, db: Session):
    """Process a file for RAG and add it to a collection."""
    try:
        # Get file and collection
        file = crud.get_file_storage(db, file_id)
        collection = crud.get_collection(db, collection_id)
        
        if not file or not collection:
            print(f"File or collection not found: file_id={file_id}, collection_id={collection_id}")
            return
        
        # Get collection file association
        collection_file = db.query(models.CollectionFile).filter(
            models.CollectionFile.file_id == file_id,
            models.CollectionFile.collection_id == collection_id
        ).first()
        
        if not collection_file:
            print(f"Collection file association not found")
            return
        
        # Initialize services
        from app.services.minio_service import MinioService
        from app.services.ingestion_service import DocumentIngestionService
        from app.utils.string_utils import sanitize_collection_name
        
        minio_service = MinioService()
        ingestion_service = DocumentIngestionService()
        
        # Sanitize collection name for Milvus
        safe_collection_name = sanitize_collection_name(collection.name)
        
        # Download file from MinIO
        download_success, file_data = minio_service.download_file(file.file_path)
        if not download_success:
            print(f"Failed to download file from storage: {file.file_path}")
            return
        
        # Process file for vector storage
        num_docs = ingestion_service.ingest_file_object(
            file_obj=file_data,
            filename=file.filename,
            collection_name=safe_collection_name,
            metadata={"source_file_id": file.id, "file_name": file.original_filename}
        )
        
        # Update collection file
        collection_file.is_processed = True
        db.commit()
        
        print(f"Successfully processed file {file_id} for collection {collection_id}: {num_docs} chunks")
        return True
    except Exception as e:
        print(f"Error processing file {file_id} for collection {collection_id}: {str(e)}")
        return False

# Add the missing functions for file processing
def process_file_for_collection_sync(file_id: int, collection_name: str, db: Session, user_id: int):
    """Process a file for RAG synchronously for a conversation-specific collection."""
    try:
        # Get file
        file = crud.get_file_storage(db, file_id)
        if not file:
            print(f"File not found: file_id={file_id}")
            return False
        
        # Initialize services
        from app.services.minio_service import MinioService
        from app.services.ingestion_service import DocumentIngestionService
        from app.utils.string_utils import sanitize_collection_name
        
        minio_service = MinioService()
        ingestion_service = DocumentIngestionService()
        
        # Sanitize collection name for Milvus
        safe_collection_name = sanitize_collection_name(collection_name)
        
        # Download file from MinIO
        download_success, file_data = minio_service.download_file(file.file_path)
        if not download_success:
            print(f"Failed to download file from storage: {file.file_path}")
            return False
        
        # Process file for vector storage
        try:
            num_docs = ingestion_service.ingest_file_object(
                file_obj=file_data,
                filename=file.filename,
                collection_name=safe_collection_name,
                metadata={"source_file_id": file.id, "file_name": file.original_filename, "user_id": user_id}
            )
            
            # Update file metadata with processing info
            new_metadata = dict(file.file_metadata or {})
            new_metadata["is_processed_for_rag"] = True
            new_metadata["chunk_count"] = num_docs
            new_metadata["processed_at"] = datetime.utcnow().isoformat()

            crud.update_file_storage(db, file.id, {"file_metadata": new_metadata})
            
            print(f"Successfully processed file {file_id} for collection {collection_name}: {num_docs} chunks")
            return True
        except Exception as e:
            print(f"Error processing file content for collection {collection_name}: {str(e)}")
            return False
    except Exception as e:
        print(f"Error processing file {file_id} for collection {collection_name}: {str(e)}")
        return False

async def process_uploaded_file_for_rag(db_file_id: int, conversation_id: str, user_id: int, db_conn_string: str):
    """Background task to process an uploaded file for RAG."""
    try:
        # Create a new database session for this background task
        engine = create_engine(db_conn_string)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        try:
            # Get file
            file = crud.get_file_storage(db, db_file_id)
            
            if not file:
                print(f"File not found: file_id={db_file_id}")
                return
            
            # Send processing started notification
            await manager.send_message({
                "type": "file_processing_started",
                "file_id": db_file_id,
                "filename": file.original_filename,
                "conversation_id": conversation_id
            }, conversation_id)
            
            # Create a collection name for this conversation
            collection_name = conversation_collection_name(conversation_id)
            
            # Initialize ingestion service
            from app.services.ingestion_service import DocumentIngestionService
            ingestion_service = DocumentIngestionService()
            
            # Explicitly create the collection first
            print(f"DEBUG: Ensuring collection exists: {collection_name}")
            try:
                # Run collection creation in thread pool to avoid blocking
                await asyncio.to_thread(
                    ingestion_service.create_new_collection, 
                    collection_name, 
                    f"Collection for conversation {conversation_id}"
                )
                print(f"DEBUG: Collection created or already exists: {collection_name}")
            except Exception as e:
                print(f"DEBUG: Error ensuring collection exists: {str(e)}")
            
            # Process the file in a thread pool to avoid blocking the event loop
            success = await asyncio.to_thread(
                process_file_for_collection_sync, 
                db_file_id, 
                collection_name, 
                db, 
                user_id
            )
            
            if success:
                print(f"Successfully processed file {db_file_id} for conversation {conversation_id}")
                # Send success notification
                await manager.send_message({
                    "type": "file_processing_completed",
                    "file_id": db_file_id,
                    "filename": file.original_filename,
                    "conversation_id": conversation_id,
                    "status": "success"
                }, conversation_id)
            else:
                print(f"Failed to process file {db_file_id} for conversation {conversation_id}")
                # Send failure notification
                await manager.send_message({
                    "type": "file_processing_completed",
                    "file_id": db_file_id,
                    "filename": file.original_filename,
                    "conversation_id": conversation_id,
                    "status": "failed"
                }, conversation_id)
                
            # Check if all files in conversation are processed
            conversation_files = crud.get_conversation_files(db, conversation_id)
            all_processed = all(
                f.file_metadata and f.file_metadata.get("is_processed_for_rag", False)
                for f in conversation_files
            )
            
            if all_processed:
                # Send all files completed notification
                await manager.send_message({
                    "type": "all_files_processed",
                    "conversation_id": conversation_id,
                    "total_files": len(conversation_files)
                }, conversation_id)
                
        finally:
            db.close()
            
    except Exception as e:
        print(f"Error in background file processing: {str(e)}")
        # Send error notification
        try:
            await manager.send_message({
                "type": "file_processing_error",
                "file_id": db_file_id,
                "conversation_id": conversation_id,
                "error": str(e)
            }, conversation_id)
        except:
            pass  # Don't fail if WebSocket notification fails

@router.get("/files/download/{path:path}")
async def download_file(
    path: str,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Download a file directly from the API.
    This is a fallback for when MinIO presigned URLs don't work.
    """
    try:
        # Find the file in the database
        db_file = db.query(models.FileStorage).filter(models.FileStorage.file_path == path).first()
        if not db_file:
            # Try with the path as the object name
            db_file = db.query(models.FileStorage).filter(models.FileStorage.file_path == path).first()
            
        if not db_file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        # Check if the user has access to this file
        if db_file.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this file"
            )
        
        # Download the file from MinIO
        success, file_data = minio_service.download_file(db_file.file_path)
        
        if not success or not file_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found in storage"
            )
        
        # Reset the file pointer to the beginning
        file_data.seek(0)
        
        # Return the file as a streaming response
        return StreamingResponse(
            file_data,
            media_type=db_file.mime_type or "application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="{db_file.filename}"'
            }
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error downloading file: {str(e)}"
        )

# Add a new endpoint to check file processing status
@router.get("/file-status/{conversation_id}")
async def get_file_processing_status(
    conversation_id: str,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Check if files for a conversation have been processed and are ready for RAG.
    Returns the status of all files in the conversation.
    """
    try:
        # Get files attached to this conversation
        conversation_files = crud.get_conversation_files(db, conversation_id)
        
        if not conversation_files:
            return {
                "status": "no_files",
                "message": "No files found for this conversation",
                "files": []
            }
        
        # Check processing status of each file
        files_status = []
        all_processed = True
        
        for file in conversation_files:
            is_processed = (
                file.file_metadata is not None and 
                file.file_metadata.get("is_processed_for_rag", False)
            )
            
            if not is_processed:
                all_processed = False
            
            files_status.append({
                "file_id": file.id,
                "filename": file.original_filename,
                "is_processed": is_processed
            })
        
        return {
            "status": "ready" if all_processed else "processing",
            "message": "All files processed and ready" if all_processed else "Some files are still being processed",
            "files": files_status
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error checking file status: {str(e)}",
            "files": []
        }

# Helper function for error streaming
async def generate_error_stream(error_message):
    yield json.dumps({
        "status": "error",
        "message": error_message
    }) + "\n"

# Endpoint to initiate an empty conversation
@router.post("/initiate", response_model=schemas.ConversationInitiateResponse, status_code=status.HTTP_201_CREATED)
async def initiate_empty_conversation(
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Creates a new, empty conversation that will expire if not used.
    Returns the conversation ID and its expiration time.
    """
    try:
        conversation = crud.create_empty_conversation(db=db, user_id=current_user.id)
        return schemas.ConversationInitiateResponse(
            conversation_id=conversation.id,
            expires_at=conversation.expires_at
        )
    except Exception as e:
        # Log the exception e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not initiate conversation."
        )
        
# Endpoint to initiate a conversation with the global default collection
@router.post("/initiate-with-global-collection", response_model=schemas.ConversationInitiateResponse, status_code=status.HTTP_201_CREATED)
async def initiate_with_global_collection(
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Creates a new conversation linked to the current global default collection.
    Returns the conversation ID.
    """
    try:
        # Get the RAG config to find the predefined collection
        from app.services.rag_config_service import RAGConfigService
        
        print(f"DEBUG: Starting initiate_with_global_collection for user_id={current_user.id}")
        
        # Try to get the global default collection directly first
        global_collection = crud.get_global_default_collection(db)
        if global_collection:
            collection_name = global_collection.name
            print(f"DEBUG: Found global default collection directly: {collection_name}, id={global_collection.id}")
        else:
            # Fall back to RAG config
            print(f"DEBUG: No global default collection found, trying RAG config")
            try:
                rag_config = RAGConfigService.get_rag_config(db)
                collection_name = rag_config.get("predefined_collection")
                print(f"DEBUG: Retrieved predefined_collection from RAG config: '{collection_name}'")
            except Exception as e:
                print(f"DEBUG: Error getting RAG config: {str(e)}")
                collection_name = None
        
        if not collection_name:
            print("DEBUG: ERROR - No predefined collection has been defined")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No predefined collection has been defined in the RAG configuration. Please contact an administrator."
            )
        
        # Get the collection by name
        collection = crud.get_collection_by_name(db, collection_name)
        print(f"DEBUG: Retrieved collection from DB by name: {collection_name} -> {collection}")
        
        if not collection:
            print(f"DEBUG: ERROR - Collection '{collection_name}' not found in database")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection '{collection_name}' defined in the RAG configuration was not found in the database. Please contact an administrator."
            )
        
        # Check if the collection exists in Milvus
        try:
            from app.services.rag_service import RemoteVectorStoreManager
            from app.utils.string_utils import sanitize_collection_name
            
            vector_store_manager = RemoteVectorStoreManager(
                milvus_uri=settings.MILVUS_URI
            )
            
            # Global collections are admin collections and have admin_ prefix in Milvus
            safe_collection_name = sanitize_collection_name(f"admin_{collection_name}")
            collection_exists = vector_store_manager.collection_exists(safe_collection_name)
            print(f"DEBUG: Checking if global collection exists in Milvus: '{safe_collection_name}' -> {collection_exists}")
            
            if not collection_exists:
                print(f"DEBUG: WARNING - Global collection '{safe_collection_name}' not found in Milvus. This may cause issues when chatting.")
        except Exception as e:
            print(f"DEBUG: Error checking Milvus collection: {str(e)}")
            # Continue anyway as we can still create the conversation
        
        # Create the conversation linked to this collection
        try:
            conversation = crud.create_conversation_with_global_collection(db=db, user_id=current_user.id)
            print(f"DEBUG: Created conversation: {conversation}")
            
            if not conversation:
                print("DEBUG: ERROR - Failed to create conversation with global collection")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create conversation with global collection."
                )
            
            print(f"DEBUG: Successfully created conversation ID: {conversation.id} with global collection: {collection_name}")
            
            return schemas.ConversationInitiateResponse(
                conversation_id=conversation.id,
                expires_at=conversation.expires_at  # Return the actual expiration time
            )
        except Exception as e:
            print(f"DEBUG: Error creating conversation: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating conversation: {str(e)}"
            )
    except HTTPException:
        raise
    except Exception as e:
        # Log the exception e
        print(f"DEBUG: EXCEPTION in initiate_with_global_collection: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not initiate conversation with global collection."
        )

# Endpoint to migrate a conversation to the current global collection
@router.post("/conversations/{conversation_id}/migrate-to-current-global", response_model=schemas.Conversation)
async def migrate_to_current_global_collection(
    conversation_id: str,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Updates a conversation to use the current global default collection.
    This is used when the global default collection has changed.
    """
    # Get the conversation
    conversation = crud.get_conversation(db, conversation_id)
    if not conversation or conversation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    # Check if this is a global collection conversation
    if conversation.conversation_type != models.ConversationType.GLOBAL_COLLECTION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This conversation is not linked to a global collection"
        )
    
    # Check if outdated
    if not crud.is_global_collection_outdated(db, conversation_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This conversation is already using the current global collection"
        )
    
    # Update to current global collection
    updated_conversation = crud.update_conversation_to_current_global_collection(db, conversation_id)
    if not updated_conversation:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update conversation to current global collection"
        )
    
    return updated_conversation

@router.get("/conversations/{conversation_id}/global-collection-status", response_model=Dict[str, Any])
async def get_global_collection_status(
    conversation_id: str,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get the global collection status for a conversation.
    Returns information about whether the conversation is outdated and what actions are available.
    """
    # Get the conversation
    conversation = crud.get_conversation(db, conversation_id)
    if not conversation or conversation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    # Only applies to global collection conversations
    if conversation.conversation_type != models.ConversationType.GLOBAL_COLLECTION:
        return {
            "conversation_type": conversation.conversation_type.value,
            "is_global_collection": False,
            "message": "This conversation is not linked to a global collection"
        }
    
    # Get current behavior setting
    from app.services.admin_config_service import AdminConfigService
    behavior = AdminConfigService.get_config(db, models.AdminConfig.KEY_GLOBAL_COLLECTION_BEHAVIOR, "auto_update")
    
    # Check if outdated
    is_outdated = crud.is_global_collection_outdated(db, conversation_id)
    
    # Get current global collection info
    from app.services.rag_config_service import RAGConfigService
    rag_config = RAGConfigService.get_rag_config(db)
    current_global_collection_name = rag_config.get("predefined_collection")
    
    result = {
        "conversation_type": conversation.conversation_type.value,
        "is_global_collection": True,
        "behavior": behavior,
        "is_outdated": is_outdated,
        "original_collection_name": conversation.original_global_collection_name,
        "current_global_collection_name": current_global_collection_name,
        "linked_collection_id": conversation.linked_global_collection_id,
        "can_migrate": is_outdated and behavior == "readonly_on_change",
        "is_readonly": is_outdated and behavior == "readonly_on_change",
        "auto_updates": behavior == "auto_update"
    }
    
    if is_outdated:
        if behavior == "auto_update":
            result["message"] = "This conversation automatically uses the latest global collection"
        else:
            result["message"] = "This conversation is read-only because the global collection has changed. You can migrate to the current collection or start a new conversation."
    else:
        result["message"] = "This conversation is up to date with the current global collection"
    
    return result

@router.get("/debug/check-file-vectors/{file_id}", response_model=Dict[str, Any])
async def debug_check_file_vectors(
    file_id: int,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Debug endpoint to check if a file's vectors were properly indexed in Milvus."""
    try:
        # Admin access check
        if current_user.role != models.UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admin users can access this endpoint"
            )
            
        # Get the file
        file = crud.get_file_storage(db, file_id)
        if not file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File with ID {file_id} not found"
            )
            
        # Get the conversation
        conversation = None
        if file.conversation_id:
            conversation = crud.get_conversation(db, file.conversation_id)
            
        # Check if file has been processed
        file_metadata = file.file_metadata or {}
        print(f"DEBUG: File metadata for file_id={file_id}: {file_metadata}")
        is_processed = file_metadata.get("is_processed_for_rag", False)
        chunk_count = file_metadata.get("chunk_count", 0)
        
        # Get collection name
        collection_name = None
        if conversation:
            collection_name = conversation_collection_name(conversation.id)
            
        # Get collection info from Milvus
        from app.services.rag_service import RemoteVectorStoreManager
        vector_store_manager = RemoteVectorStoreManager(
            milvus_uri=settings.MILVUS_URI
        )
        
        # Check if collection exists in Milvus
        safe_collection_name = sanitize_collection_name(collection_name) if collection_name else None
        collection_exists = False
        entities_count = 0
        
        if safe_collection_name:
            collection_exists = vector_store_manager.collection_exists(safe_collection_name)
            
            # If collection exists, get count of entities
            if collection_exists:
                from pymilvus import connections, utility, Collection
                connections.connect(uri=settings.MILVUS_URI)
                collection = Collection(safe_collection_name)
                collection.load()
                entities_count = collection.num_entities
                
        return {
            "file_id": file.id,
            "filename": file.original_filename,
            "conversation_id": file.conversation_id,
            "is_processed": is_processed,
            "chunk_count": chunk_count,
            "collection_name": safe_collection_name,
            "collection_exists": collection_exists,
            "collection_entity_count": entities_count
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error checking file vectors: {str(e)}"
        ) 

# Add WebSocket endpoint after the existing endpoints
@router.websocket("/ws/file-processing/{conversation_id}")
async def websocket_file_processing(websocket: WebSocket, conversation_id: str):
    """
    WebSocket endpoint for real-time file processing notifications.
    Frontend can connect to this to receive updates when files are processed.
    """
    await manager.connect(websocket, conversation_id)
    try:
        while True:
            # Keep connection alive and listen for any messages
            data = await websocket.receive_text()
            # Echo back for heartbeat
            await websocket.send_text(json.dumps({"type": "heartbeat", "status": "connected"}))
    except WebSocketDisconnect:
        manager.disconnect(websocket, conversation_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket, conversation_id)

# Add SSE endpoint for file processing notifications
@router.get("/sse/file-processing/{conversation_id}")
async def sse_file_processing(
    conversation_id: str,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Server-Sent Events endpoint for file processing notifications.
    Alternative to WebSocket for browsers that prefer SSE.
    """
    async def event_stream():
        # Send initial connection message
        yield f"data: {json.dumps({'type': 'connected', 'conversation_id': conversation_id})}\n\n"
        
        # Check initial status
        conversation_files = crud.get_conversation_files(db, conversation_id)
        if conversation_files:
            all_processed = all(
                f.file_metadata and f.file_metadata.get("is_processed_for_rag", False)
                for f in conversation_files
            )
            
            if all_processed:
                yield f"data: {json.dumps({'type': 'all_files_processed', 'conversation_id': conversation_id})}\n\n"
                return
        
        # Poll for changes (in a real implementation, you'd use a more efficient method)
        last_check = {}
        while True:
            try:
                conversation_files = crud.get_conversation_files(db, conversation_id)
                current_status = {f.id: f.file_metadata.get("is_processed_for_rag", False) if f.file_metadata else False for f in conversation_files}
                
                # Check for changes
                for file_id, is_processed in current_status.items():
                    if file_id not in last_check or last_check[file_id] != is_processed:
                        if is_processed:
                            file = next(f for f in conversation_files if f.id == file_id)
                            yield f"data: {json.dumps({'type': 'file_processing_completed', 'file_id': file_id, 'filename': file.original_filename, 'status': 'success'})}\n\n"
                
                last_check = current_status
                
                # Check if all files are processed
                if all(current_status.values()) and current_status:
                    yield f"data: {json.dumps({'type': 'all_files_processed', 'conversation_id': conversation_id})}\n\n"
                    break
                
                await asyncio.sleep(2)  # Poll every 2 seconds
                
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                break
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

@router.get("/conversation-ready/{conversation_id}")
async def check_conversation_ready(
    conversation_id: str,
    current_user: schemas.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Check if a conversation is ready for chat.
    Returns true if all files are processed or if no files are attached.
    """
    try:
        # Check if conversation exists and belongs to user
        conversation = crud.get_conversation(db, conversation_id)
        if not conversation or conversation.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        # Get files attached to this conversation
        conversation_files = crud.get_conversation_files(db, conversation_id)
        
        if not conversation_files:
            # No files attached, conversation is ready
            return {
                "ready": True,
                "message": "Conversation is ready for chat",
                "files_count": 0,
                "processed_count": 0
            }
        
        # Check if all files are processed
        processed_count = 0
        for file in conversation_files:
            if file.file_metadata and file.file_metadata.get("is_processed_for_rag", False):
                processed_count += 1
        
        all_processed = processed_count == len(conversation_files)
        
        return {
            "ready": all_processed,
            "message": "All files processed" if all_processed else f"Processing files: {processed_count}/{len(conversation_files)} completed",
            "files_count": len(conversation_files),
            "processed_count": processed_count,
            "files": [
                {
                    "id": f.id,
                    "filename": f.original_filename,
                    "processed": f.file_metadata.get("is_processed_for_rag", False) if f.file_metadata else False
                }
                for f in conversation_files
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error checking conversation status: {str(e)}"
        )