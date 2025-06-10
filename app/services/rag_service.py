from typing import Generator, Dict, Optional, List, AsyncGenerator
from sqlalchemy.orm import Session
import os
import json
import uuid
from langchain_core.documents import Document
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.documents.transformers import BaseDocumentTransformer
from langchain.retrievers.document_compressors import DocumentCompressorPipeline
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_openai import ChatOpenAI
from langchain_milvus.vectorstores import Milvus
from langchain.retrievers import ContextualCompressionRetriever
from langchain_core.chat_history import BaseChatMessageHistory
# PostgresMessageHistory is not available in this version of langchain
from langchain.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)

from app.db import crud, models, schemas
from app.db.database import get_db
from app.config import settings
from app.services.message_history import CustomMessageHistory
from app.services.rag_config_service import RAGConfigService
from app.utils.embeddings import RemoteEmbedder
from app.utils.infinity_embedder import InfinityEmbedder
from app.utils.string_utils import sanitize_collection_name, conversation_collection_name
from app.services.llm_service import get_streaming_llm_response
import asyncio

# Debug print to verify imports loaded properly
print("DEBUG: All necessary imports loaded for RAG service including RunnableWithMessageHistory from langchain_core")

# Default RAG system prompt to use if not defined in settings
DEFAULT_RAG_SYSTEM_PROMPT = """
You are a helpful AI assistant. Answer the user's question based on the provided context and chat history.
If the answer isn't in the context, politely say you don't know rather than making up an answer.
Be concise, accurate, and helpful in your response.
"""

class RemoteVectorStoreManager:
    """Manages connection to a remote Milvus vector database."""
    
    def __init__(self, embedding_url: str, milvus_uri: str):
        # Keep legacy support for RemoteEmbedder for backward compatibility
        # but it will not be used by default
        self.remote_embedder = RemoteEmbedder(embedding_url)
        
        # Use InfinityEmbeddings as the primary embedder
        self.infinity_embedder = InfinityEmbedder(
            model=settings.INFINITY_EMBEDDINGS_MODEL,
            infinity_api_url=settings.INFINITY_API_URL,
            batch_size=32,
            retry_count=3,
            timeout=60
        )
        
        self.milvus_uri = milvus_uri
        self.vectorstore = None
        
        
    def get_vectorstore(self, collection_name: str):
        """Get or create a vectorstore with the specified collection."""
        # Sanitize collection name for Milvus
        safe_collection_name = sanitize_collection_name(collection_name)
        print(f"DEBUG: Getting vectorstore for collection: '{collection_name}' -> '{safe_collection_name}'")
        
        try:
            self.vectorstore = Milvus(
                embedding_function=self.infinity_embedder,
                collection_name=safe_collection_name,
                connection_args={"uri": self.milvus_uri}
            )
            print(f"DEBUG: Successfully got vectorstore for collection: '{safe_collection_name}'")
            return self.vectorstore
        except Exception as e:
            print(f"DEBUG: ERROR getting vectorstore: {str(e)}")
            raise
        
    def get_retriever(self, collection_name: str, top_k: int = 4):
        """Get a retriever for the specified collection."""
        print(f"DEBUG: Getting retriever for collection: '{collection_name}' with top_k={top_k}")
        
        # Ensure top_k is a valid value for Milvus (must be between 1 and 16384)
        if not isinstance(top_k, int) or top_k < 1:
            top_k = 4  # Default to a safe value
            print(f"DEBUG: Invalid top_k value, defaulting to {top_k}")
        elif top_k > 100:
            top_k = 100  # Cap at a reasonable maximum
            print(f"DEBUG: top_k too large, capping at {top_k}")
            
        try:
            vectorstore = self.get_vectorstore(collection_name)
            retriever = vectorstore.as_retriever(search_kwargs={"k": top_k})
            print(f"DEBUG: Successfully created retriever for collection: '{collection_name}'")
            return retriever
        except Exception as e:
            print(f"DEBUG: ERROR getting retriever: {str(e)}")
            raise
        
    def list_collections(self):
        """List all available collections in Milvus."""
        try:
            from pymilvus import connections, utility
            connections.connect(uri=self.milvus_uri)
            collections = utility.list_collections()
            return collections
        except Exception as e:
            print(f"DEBUG: ERROR listing collections: {str(e)}")
            return []
    
    def collection_exists(self, collection_name: str) -> bool:
        """Check if a collection exists in Milvus.
        
        Args:
            collection_name: Name of the collection to check
            
        Returns:
            True if the collection exists, False otherwise
        """
        try:
            from pymilvus import connections, utility
            connections.connect(uri=self.milvus_uri)
            exists = utility.has_collection(collection_name)
            print(f"DEBUG: Checking if collection '{collection_name}' exists in Milvus: {exists}")
            return exists
        except Exception as e:
            print(f"DEBUG: ERROR checking if collection exists: {str(e)}")
            return False
    
    def get_embedding_function(self):
        """Get the embedding function."""
        return self.infinity_embedder

class RagChatService:
    """Service for RAG-based chat using LangChain and PostgreSQL."""
    
    def __init__(self, embedding_url: str = None, milvus_uri: str = None):
        """Initialize the RAG chat service."""
        self.milvus_uri = milvus_uri or settings.MILVUS_URI
        self.embeddings = InfinityEmbedder(
            model=settings.INFINITY_EMBEDDINGS_MODEL,
            infinity_api_url=embedding_url or settings.INFINITY_API_URL
        )
        self.vectorstore_manager = RemoteVectorStoreManager(
            embedding_url=embedding_url or settings.REMOTE_EMBEDDER_URL,
            milvus_uri=self.milvus_uri
        )
    
    def _is_global_collection(self, db: Session, collection_name: str) -> bool:
        """
        Check if a collection is the global/predefined collection.
        
        Args:
            db: Database session
            collection_name: Name of the collection to check
            
        Returns:
            True if collection is the global collection, False otherwise
        """
        try:
            # Handle None case
            if collection_name is None:
                return False
                
            from app.services.rag_config_service import RAGConfigService
            predefined_collection = RAGConfigService.get_predefined_collection(db)
            
            # Check if collection name matches the predefined collection
            # Handle both direct name match and admin-prefixed names
            return (collection_name == predefined_collection or 
                    collection_name == f"admin_{predefined_collection}" or
                    collection_name.replace("admin_", "") == predefined_collection)
        except Exception as e:
            print(f"DEBUG: Error checking if collection is global: {str(e)}")
            return False
    
    def _get_rag_system_prompt(self, db: Session, collection_name: str = None) -> str:
        """
        Get the appropriate RAG system prompt based on collection type.
        
        Args:
            db: Database session
            collection_name: Name of the collection (optional)
            
        Returns:
            Appropriate system prompt for the collection type
        """
        try:
            from app.config import settings
            from app.services.rag_config_service import RAGConfigService
            
            # If collection is specified and it's a global collection, use global prompt
            if collection_name and self._is_global_collection(db, collection_name):
                print(f"DEBUG: Using global collection RAG prompt for collection: {collection_name}")
                return RAGConfigService.get_global_collection_rag_prompt(db)
            else:
                # Use configurable user collection prompt
                print(f"DEBUG: Using user collection RAG prompt for collection: {collection_name}")
                return RAGConfigService.get_user_collection_rag_prompt(db)
        except Exception as e:
            print(f"DEBUG: Error getting RAG system prompt, falling back to default: {str(e)}")
            return DEFAULT_RAG_SYSTEM_PROMPT

    def get_llm(self, db: Session, streaming: bool = False, override_thinking: Optional[bool] = None):
        """Get a configured LLM instance."""
        # Get the LLM config from the database (there's only one)
        config = crud.get_active_llm_config(db)
        
        # If no config exists, create a default one
        if not config:
            config = crud.create_default_llm_config(db)
        
        # Create model params from config
        model_params = {
            "model_name": config.model_name,
            "temperature": config.temperature,
            "top_p": config.top_p,
        }
        
        # Add max_tokens if set
        if config.max_tokens:
            model_params["max_tokens"] = config.max_tokens
        
        # Handle enable_thinking parameter
        enable_thinking = override_thinking if override_thinking is not None else getattr(config, 'enable_thinking', False)
        
        # Handle extra parameters
        if config.extra_params:
            if "base_url" in config.extra_params:
                model_params["base_url"] = config.extra_params["base_url"]
            
            if "api_key" in config.extra_params:
                model_params["api_key"] = config.extra_params["api_key"]
            
            # Add any other parameters
            for key, value in config.extra_params.items():
                if key not in ["base_url", "api_key"]:
                    model_params[key] = value
        
        # Use defaults from settings if not provided
        if "base_url" not in model_params:
            model_params["base_url"] = settings.OPENAI_API_BASE
            
        if "api_key" not in model_params:
            model_params["api_key"] = settings.OPENAI_API_KEY
        
        # Add thinking configuration to extra_body
        if "extra_body" not in model_params:
            model_params["extra_body"] = {}
        
        # Set chat_template_kwargs with enable_thinking
        if "chat_template_kwargs" not in model_params["extra_body"]:
            model_params["extra_body"]["chat_template_kwargs"] = {}
        
        model_params["extra_body"]["chat_template_kwargs"]["enable_thinking"] = enable_thinking
        
        # Enable streaming if requested
        if streaming:
            model_params["streaming"] = True
        
        # Return configured LLM
        return ChatOpenAI(**model_params)
    
    async def get_streaming_rag_response(self, db: Session, user_id: int, message: str, collection_name: str, conversation_id: Optional[str] = None, meta_data: Optional[dict] = None, save_user_message: bool = True):
        """Get a streaming RAG response."""
        # Set up conversation
        try:
            # Get or create conversation
            if conversation_id:
                db_conversation = crud.get_conversation(db, conversation_id)
                if not db_conversation:
                    raise ValueError(f"Conversation with ID {conversation_id} not found")
            else:
                db_conversation = crud.create_conversation(db, user_id)
                conversation_id = db_conversation.id
            
            # Update conversation meta_data if provided
            if meta_data:
                crud.update_conversation(db, conversation_id, meta_data)
            
            # Save user message to database if requested
            if save_user_message:
                user_message = schemas.MessageCreate(
                    conversation_id=conversation_id,
                    role="user",
                    content=message
                )
                crud.create_message(db, user_message)
            
            # Create streaming LLM
            llm = self.get_llm(db, streaming=True)
            
            # Create custom history for this conversation
            history = CustomMessageHistory(conversation_id, db)
            
            # Create retriever with admin-configurable top_k value
            from app.services.rag_config_service import RAGConfigService
            top_k = RAGConfigService.get_retriever_top_k(db)
            retriever = self.vectorstore_manager.get_retriever(collection_name, top_k=top_k)
            
            # Create the contextualize question chain
            contextualize_q_system_prompt = (
                "Transform the user's question into a clear, direct search query. "
                "Use chat history context only to make ambiguous questions more specific. "
                "Return only the search query without any explanations, formatting, or markdown. "
                "Keep the same language as the user's question. "
                "If the question is already clear, return it unchanged."
            )
            
            contextualize_q_prompt = ChatPromptTemplate.from_messages([
                ("system", contextualize_q_system_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
            ])
            
            # Use a non-streaming LLM for context with thinking disabled for efficiency
            context_llm = self.get_llm(db, streaming=False, override_thinking=False)
            contextualizer = contextualize_q_prompt | context_llm | StrOutputParser()
            
            # Get chat history
            chat_history = history.messages
            
            # Get contextualized question using LangChain's native async method
            contextualized_question = await contextualizer.ainvoke({
                "chat_history": chat_history,
                "input": message
            })
            
            # DEBUG: Print the contextualized question that will be sent to vectorstore
            print(f"DEBUG: Original user message: {message}")
            print(f"DEBUG: Contextualized question sent to vectorstore: {contextualized_question}")
            print(f"DEBUG: Chat history length: {len(chat_history)} messages")
            
            # Retrieve relevant documents using LangChain's native async method
            relevant_docs = await retriever.ainvoke(contextualized_question)
            
            # Format context from documents
            context_texts = []
            doc_info = []
            for i, doc in enumerate(relevant_docs):
                doc_info.append(self._get_doc_debug_info(doc, i))
                context_texts.append(self._extract_doc_text(doc))
            
            context = "\n\n".join(context_texts)
            print(f"DEBUG: Retrieved {len(relevant_docs)} documents: {', '.join(doc_info)}")
            print(f"DEBUG: Created context with {len(context)} characters")
            
            # Create streaming QA chain with appropriate prompt based on collection type
            base_system_prompt = self._get_rag_system_prompt(db, collection_name)
            qa_system_prompt = f"{base_system_prompt}\n\nContext: {{context}}"
            
            qa_prompt = ChatPromptTemplate.from_messages([
                ("system", qa_system_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
            ])
            
            # Prepare the final input variables for the LLM
            final_input_vars = {
                "context": context,
                "chat_history": chat_history,
                "input": message
            }
            
            # DEBUG: Show exactly what the LLM receives
            print("\n" + "="*80)
            print("🔍 FINAL LLM INPUT DEBUG - STREAMING RAG RESPONSE")
            print("="*80)
            
            # Format the final system prompt with context
            final_system_prompt = qa_system_prompt.format(context=context)
            print(f"\n📋 FINAL SYSTEM PROMPT:\n{final_system_prompt}")
            
            print(f"\n💬 CHAT HISTORY ({len(chat_history)} messages):")
            for i, msg in enumerate(chat_history):
                msg_type = type(msg).__name__
                if hasattr(msg, 'content'):
                    content_preview = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
                    print(f"  [{i}] {msg_type}: {content_preview}")
                else:
                    print(f"  [{i}] {msg_type}: {str(msg)[:100]}...")
            
            print(f"\n👤 USER INPUT:\n{message}")
            
            print(f"\n📚 RAG CONTEXT ({len(context)} chars):")
            context_preview = context[:500] + "..." if len(context) > 500 else context
            print(f"{context_preview}")
            
            print("\n" + "="*80)
            print("🚀 SENDING TO LLM...")
            print("="*80 + "\n")
            
            # Prepare to collect the full response
            full_response = []
            
            # Generate streaming response using LangChain's native async streaming
            chain = qa_prompt | llm
            
            # Use LangChain's native async streaming method
            async for chunk in chain.astream(final_input_vars):
                token = chunk.content
                full_response.append(token)
                yield token
            
            # Combine tokens to create the complete response
            complete_response = "".join(full_response)
            
            # Save the assistant response with RAG context
            assistant_message = schemas.MessageCreate(
                conversation_id=conversation_id,
                role="assistant",
                content=complete_response,
                rag_context=context
            )
            
            # Store the message
            crud.create_message(db, assistant_message)
            
        except Exception as e:
            # Log the exception and re-raise
            print(f"Error in streaming RAG response: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
    
    async def get_rag_response(self, db: Session, user_id: int, message: str, collection_name: str, conversation_id: Optional[str] = None, meta_data: Optional[dict] = None):
        """Get a non-streaming RAG response."""
        print(f"DEBUG: Starting get_rag_response with collection={collection_name}, user_id={user_id}, conversation_id={conversation_id}")
        try:
            # Get or create conversation
            if conversation_id:
                db_conversation = crud.get_conversation(db, conversation_id)
                if not db_conversation:
                    raise ValueError(f"Conversation with ID {conversation_id} not found")
            else:
                db_conversation = crud.create_conversation(db, user_id)
                conversation_id = db_conversation.id

            # Update conversation meta_data if provided
            if meta_data:
                print(f"DEBUG: Updating conversation metadata: {meta_data}")
                crud.update_conversation(db, conversation_id, meta_data)

            # Create LLM (non-streaming)
            llm = self.get_llm(db, streaming=False)

            # Create custom history for this conversation
            history = CustomMessageHistory(conversation_id, db)

            # Create retriever with admin-configurable top_k value
            from app.services.rag_config_service import RAGConfigService
            top_k = RAGConfigService.get_retriever_top_k(db)
            retriever = self.vectorstore_manager.get_retriever(collection_name, top_k=top_k)

            # Create the contextualize question chain
            contextualize_q_system_prompt = (
                "Transform the user's question into a clear, direct search query. "
                "Use chat history context only to make ambiguous questions more specific. "
                "Return only the search query without any explanations, formatting, or markdown. "
                "Keep the same language as the user's question. "
                "If the question is already clear, return it unchanged."
            )
            contextualize_q_prompt = ChatPromptTemplate.from_messages([
                ("system", contextualize_q_system_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
            ])
            # Use a non-streaming LLM for context with thinking disabled for efficiency
            context_llm = self.get_llm(db, streaming=False, override_thinking=False)
            contextualizer = contextualize_q_prompt | context_llm | StrOutputParser()

            # Get chat history
            chat_history = history.messages

            # Get contextualized question using LangChain's native async method
            contextualized_question = await contextualizer.ainvoke({
                "chat_history": chat_history,
                "input": message
            })

            # DEBUG: Print the contextualized question that will be sent to vectorstore
            print(f"DEBUG: Original user message: {message}")
            print(f"DEBUG: Contextualized question sent to vectorstore: {contextualized_question}")
            print(f"DEBUG: Chat history length: {len(chat_history)} messages")

            # Retrieve relevant documents using LangChain's native async method
            relevant_docs = await retriever.ainvoke(contextualized_question)

            # Format context from documents
            context_texts = []
            doc_info = []
            for i, doc in enumerate(relevant_docs):
                doc_info.append(self._get_doc_debug_info(doc, i))
                doc_text = self._extract_doc_text(doc)
                context_texts.append(doc_text)
            
            context = "\n\n".join(context_texts)
            print(f"DEBUG: Retrieved {len(relevant_docs)} documents: {', '.join(doc_info)}")
            print(f"DEBUG: Created context with {len(context)} characters")
            print(f"DEBUG: Final context preview: {context[:200]}...")

            # Create QA chain (non-streaming) with appropriate prompt based on collection type
            base_system_prompt = self._get_rag_system_prompt(db, collection_name)
            qa_system_prompt = f"{base_system_prompt}\n\nContext: {{context}}"
            qa_prompt = ChatPromptTemplate.from_messages([
                ("system", qa_system_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
            ])
            chain = qa_prompt | llm

            # Prepare the final input variables for the LLM
            final_input_vars = {
                "context": context,
                "chat_history": chat_history,
                "input": message
            }
            
            # DEBUG: Show exactly what the LLM receives
            print("\n" + "="*80)
            print("🔍 FINAL LLM INPUT DEBUG - NON-STREAMING RAG RESPONSE")
            print("="*80)
            
            # Format the final system prompt with context
            final_system_prompt = qa_system_prompt.format(context=context)
            print(f"\n📋 FINAL SYSTEM PROMPT:\n{final_system_prompt}")
            
            print(f"\n💬 CHAT HISTORY ({len(chat_history)} messages):")
            for i, msg in enumerate(chat_history):
                msg_type = type(msg).__name__
                if hasattr(msg, 'content'):
                    content_preview = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
                    print(f"  [{i}] {msg_type}: {content_preview}")
                else:
                    print(f"  [{i}] {msg_type}: {str(msg)[:100]}...")
            
            print(f"\n👤 USER INPUT:\n{message}")
            
            print(f"\n📚 RAG CONTEXT ({len(context)} chars):")
            context_preview = context[:500] + "..." if len(context) > 500 else context
            print(f"{context_preview}")
            
            print("\n" + "="*80)
            print("🚀 SENDING TO LLM...")
            print("="*80 + "\n")

            # Run the chain and collect the full response using LangChain's native async method
            result = await chain.ainvoke(final_input_vars)
            complete_response = result.content if hasattr(result, 'content') else str(result)

            # Save the assistant response with RAG context
            assistant_message = schemas.MessageCreate(
                conversation_id=conversation_id,
                role="assistant",
                content=complete_response,
                rag_context=context
            )
            crud.create_message(db, assistant_message)

            # Return processed result
            return {
                "response": complete_response,
                "conversation_id": conversation_id,
                "meta_data": meta_data
            }
        except Exception as e:
            print(f"DEBUG: ERROR in get_rag_response: {str(e)}")
            import traceback
            traceback.print_exc()
            # Create a fallback response
            return {
                "response": "I'm having trouble accessing the knowledge base. Please try again later.",
                "conversation_id": conversation_id or str(uuid.uuid4()),
                "meta_data": meta_data
            }
    
    def list_available_collections(self):
        """List all available collections in the vector store."""
        return self.vectorstore_manager.list_collections()

    async def get_conversation_rag_response(self, db: Session, conversation_id: str, query: str, 
                                 user_id: int, conversation_collection: Optional[str] = None) -> str:
        """
        Get a response from the RAG system for a conversation.
        
        Args:
            db: Database session
            conversation_id: Conversation ID
            query: User query
            user_id: User ID
            conversation_collection: Optional collection name for the conversation
            
        Returns:
            Response from the RAG system
        """
        try:
            # Import settings at the function level to avoid the UnboundLocalError
            from app.config import settings
            
            print(f"DEBUG: Starting get_conversation_rag_response for conversation {conversation_id}")
            print(f"DEBUG: Query: {query}")
            print(f"DEBUG: Provided collection name: {conversation_collection}")
            
            # Get conversation history
            history = self._get_conversation_history(db, conversation_id)
            print(f"DEBUG: Got conversation history: {len(history)} characters")
            
            # Get admin settings (safely - may not exist)
            try:
                admin_config = crud.get_latest_admin_config(db)
                print(f"DEBUG: Got admin config: {admin_config}")
            except Exception as e:
                print(f"DEBUG: Error getting admin config: {str(e)}")
                admin_config = {}
            
            # Create LLM using the get_llm method (disable thinking for efficiency)
            llm = self.get_llm(db, override_thinking=False)
            print(f"DEBUG: Created LLM with model {llm.model_name}")
            
            # Get appropriate system prompt based on collection type
            system_prompt = self._get_rag_system_prompt(db, conversation_collection)
            
            # Create prompt
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
                ("human", "Context: {context}")
            ])
            
            # Create document chain
            document_chain = create_stuff_documents_chain(llm, prompt)
            
            # Check if we have a collection for this conversation
            if conversation_collection:
                print(f"DEBUG: Using provided collection name: {conversation_collection}")
                
                try:
                    # Get retriever for this collection - use admin-configurable top_k value
                    from app.services.rag_config_service import RAGConfigService
                    top_k = RAGConfigService.get_retriever_top_k(db)
                    print(f"DEBUG: Using admin-configured top_k value: {top_k}")
                    retriever = self.vectorstore_manager.get_retriever(
                        collection_name=conversation_collection,
                        top_k=top_k
                    )
                    print(f"DEBUG: Created retriever for collection: {conversation_collection}")
                    
                    # DEBUG: Print the query that will be sent to vectorstore
                    print(f"DEBUG: Query sent to vectorstore: {query}")
                    print(f"DEBUG: Using top_k: {top_k}")
                    
                    # Retrieve relevant documents using LangChain's native async method
                    retrieved_docs = await retriever.ainvoke(query)
                    
                    # Join the text of the retrieved documents
                    context_texts = []
                    doc_info = []
                    for i, doc in enumerate(retrieved_docs):
                        doc_info.append(self._get_doc_debug_info(doc, i))
                        context_texts.append(self._extract_doc_text(doc))
                    
                    context = "\n\n".join(context_texts)
                    print(f"DEBUG: Retrieved {len(retrieved_docs)} documents: {', '.join(doc_info) if doc_info else 'None'}")
                    print(f"DEBUG: Created context with {len(context)} characters")
                    
                    # Use the context directly as a string without trying to create a Document using LangChain's native async method
                    result = await document_chain.ainvoke({
                        "input": query, 
                        "chat_history": history,
                        "context": context
                    })
                    print(f"DEBUG: Generated response with retrieved context: {result[:100]}...")
                    return result
                except Exception as e:
                    print(f"DEBUG: ERROR with retriever approach for collection {conversation_collection}: {str(e)}")
                    # Fall back to regular chat approach without any context
                    context = "No relevant documents were found for your question. I'll try to answer based on my general knowledge."
                    
                    try:
                        # Use the context directly as a string without trying to create a Document using LangChain's native async method
                        result = await document_chain.ainvoke({
                            "input": query, 
                            "chat_history": history,
                            "context": context
                        })
                        print(f"DEBUG: Generated response with fallback approach: {result[:100]}...")
                        return result
                    except Exception as e2:
                        print(f"DEBUG: ERROR in fallback approach: {str(e2)}")
                        # Final fallback - use regular LLM without context
                        return await self._get_regular_llm_response(db, query, user_id, conversation_id)
            else:
                print(f"DEBUG: No collection provided, using history-only approach")
                # No collection provided, use history only with the general context
                context = "I'll answer based on my general knowledge as no specific documents were provided."
                
                try:
                    result = await document_chain.ainvoke({
                        "input": query, 
                        "chat_history": history,
                        "context": context
                    })
                    print(f"DEBUG: Generated response with history-only approach: {result[:100]}...")
                    return result
                except Exception as e:
                    print(f"DEBUG: ERROR in history-only approach: {str(e)}")
                    # Fallback to regular LLM
                    return await self._get_regular_llm_response(db, query, user_id, conversation_id)
        except Exception as e:
            # Log the error
            print(f"DEBUG: ERROR in get_conversation_rag_response: {str(e)}")
            
            # Return a useful error message or fallback to a non-contextual response
            return await self._get_regular_llm_response(db, query, user_id, conversation_id)
    
    async def _get_regular_llm_response(self, db: Session, query: str, user_id: int, conversation_id: str) -> str:
        """Helper method to get a response from the regular LLM without RAG."""
        try:
            from app.services.llm_service import get_llm_response
            
            # Get response from regular LLM
            response = await get_llm_response(
                db=db,
                user_id=user_id,
                message=query,
                conversation_id=conversation_id
            )
            
            return response
        except Exception as e:
            print(f"DEBUG: ERROR in _get_regular_llm_response: {str(e)}")
            return "I'm having trouble processing your request. Please try again later or contact support."

    async def get_streaming_conversation_rag_response(self, db: Session, conversation_id: str, 
                                                query: str, user_id: int, 
                                                conversation_collection: Optional[str] = None,
                                                save_user_message: bool = True) -> AsyncGenerator[str, None]:
        """
        Get a streaming RAG response using files attached to a conversation.
        
        Args:
            db: Database session
            conversation_id: ID of the conversation
            query: User query
            user_id: ID of the user
            conversation_collection: Optional name of the collection for this conversation
            save_user_message: Whether to save the user message to the database (defaults to True)
            
        Yields:
            Tokens of the generated response
        """
        try:
            # Save user message to database first if requested
            if save_user_message:
                user_message = schemas.MessageCreate(
                    conversation_id=conversation_id,
                    role="user",
                    content=query
                )
                crud.create_message(db, user_message)
            
            # Get conversation history
            messages = crud.get_conversation_messages(db, conversation_id)
            
            # Format history for the LLM
            history = []
            for msg in messages:
                if msg.role == "user":
                    history.append(f"Human: {msg.content}")
                elif msg.role == "assistant":
                    history.append(f"Assistant: {msg.content}")
            
            history_text = "\n".join(history[-10:])  # Limit history to last 10 messages
            
            # Use the conversation-specific collection
            if not conversation_collection:
                conversation_collection = conversation_collection_name(conversation_id)
            
            # Ensure collection name is valid for Milvus
            safe_collection_name = sanitize_collection_name(conversation_collection)
            
            # Check if collection exists
            if not self.vectorstore_manager.collection_exists(safe_collection_name):
                # If no collection exists, fall back to regular chat
                # But don't create another user message since we already saved one above
                # Convert the synchronous generator to an async one
                stream_gen = get_streaming_llm_response(
                    db=db,
                    user_id=user_id,
                    message=query,
                    conversation_id=conversation_id,
                    meta_data=None,
                    save_user_message=False  # Don't save user message again
                )
                # Since we're in an async function but get_streaming_llm_response is synchronous,
                # we need to manually yield each token
                for chunk in stream_gen:
                    yield chunk
                return
            
            # Create vector store for the conversation
            vectorstore = Milvus(
                embedding_function=self.vectorstore_manager.get_embedding_function(),
                collection_name=safe_collection_name,
                connection_args={"uri": self.milvus_uri}
            )
            
            # Create retriever with admin-configured top_k value
            top_k = RAGConfigService.get_retriever_top_k(db)
            retriever = vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs={"k": top_k}
            )
            
            # DEBUG: Print the query that will be sent to vectorstore (streaming method)
            print(f"DEBUG STREAMING: Query sent to vectorstore: {query}")
            print(f"DEBUG STREAMING: Using top_k: {top_k}")
            print(f"DEBUG STREAMING: Chat history length: {len(history)} messages")
            
            # Get relevant documents using LangChain's native async method
            docs = await retriever.ainvoke(query)
            print(f"DEBUG STREAMING: Retrieved {len(docs)} documents")
            
            # Format context from documents
            context_parts = [self._extract_doc_text(doc) for doc in docs]
            context = "\n\n".join(context_parts)
            
            # DEBUG: Show context information
            print(f"DEBUG STREAMING: Context length: {len(context)} characters")
            for i, part in enumerate(context_parts[:3]):  # Show first 3 parts
                preview = part[:100] + "..." if len(part) > 100 else part
                print(f"DEBUG STREAMING: Context part {i+1}: {preview}")
            
            if len(context) > 0:
                context_preview = context[:200] + "..." if len(context) > 200 else context
                print(f"DEBUG STREAMING: Final context preview: {context_preview}")
            else:
                print("DEBUG STREAMING: No context retrieved!")
            
            # Create prompt with appropriate system prompt based on collection type
            base_system_prompt = self._get_rag_system_prompt(db, safe_collection_name)
            prompt = ChatPromptTemplate.from_messages([
                ("system", f"{base_system_prompt} Always cite the document source when referring to specific information."),
                ("system", "Context information is below.\n{context}"),
                ("system", "Previous conversation history:\n{chat_history}"),
                ("human", "{input}")
            ])
            
            # Create chat model using the get_llm method (disable thinking for efficiency)
            chat = self.get_llm(db, streaming=True, override_thinking=False)
            
            # Create chain
            chain = prompt | chat
            
            # Prepare the final input variables for the LLM
            final_input_vars = {
                "context": context,
                "chat_history": history_text,
                "input": query
            }
            
            # DEBUG: Show exactly what the LLM receives in streaming conversation RAG
            print("\n" + "="*80)
            print("🔍 FINAL LLM INPUT DEBUG - STREAMING CONVERSATION RAG")
            print("="*80)
            
            # Get the formatted messages that will be sent to the LLM
            formatted_messages = await prompt.aformat_messages(**final_input_vars)
            
            print(f"\n📋 FORMATTED MESSAGES TO LLM ({len(formatted_messages)} messages):")
            for i, msg in enumerate(formatted_messages):
                msg_type = type(msg).__name__
                role = getattr(msg, 'type', 'unknown')
                content_preview = msg.content[:300] + "..." if len(msg.content) > 300 else msg.content
                print(f"  [{i}] {msg_type} ({role}):\n{content_preview}\n")
            
            print(f"\n💬 RAW CHAT HISTORY INPUT:\n{history_text[:500]}...")
            print(f"\n👤 USER QUERY:\n{query}")
            print(f"\n📚 RAG CONTEXT ({len(context)} chars):\n{context[:500]}...")
            
            print("\n" + "="*80)
            print("🚀 SENDING TO LLM...")
            print("="*80 + "\n")
            
            # Stream the response
            full_response = []
            
            # Use LangChain's native async streaming method
            async for chunk in chain.astream(final_input_vars):
                token = chunk.content
                full_response.append(token)
                yield token
            
            # Combine all tokens into the complete response
            complete_response = "".join(full_response)
            
            # Save assistant response to database with the retrieved context
            assistant_message = schemas.MessageCreate(
                conversation_id=conversation_id,
                role="assistant",
                content=complete_response,
                rag_context=context
            )
            crud.create_message(db, assistant_message)
            
        except Exception as e:
            # Log the exception and re-raise
            print(f"Error in streaming conversation RAG response: {str(e)}")
            raise

    def _get_conversation_history(self, db: Session, conversation_id: str) -> str:
        """
        Get conversation history as a formatted string.
        
        Args:
            db: Database session
            conversation_id: Conversation ID
            
        Returns:
            Formatted conversation history
        """
        try:
            # Get messages for this conversation
            messages = crud.get_conversation_messages(db, conversation_id)
            
            # Format messages as a string
            history = ""
            for msg in messages:
                role = "User" if msg.role == "user" else "Assistant"
                history += f"{role}: {msg.content}\n\n"
                
            return history
        except Exception as e:
            print(f"Error getting conversation history: {str(e)}")
            return ""

    def _extract_doc_text(self, doc):
        label = None
        if hasattr(doc, 'metadata') and isinstance(doc.metadata, dict):
            if 'filename' in doc.metadata:
                label = f"[filename: {doc.metadata['filename']}]"
            elif 'id' in doc.metadata:
                label = f"[doc_id: {doc.metadata['id']}]"
        elif isinstance(doc, dict):
            if 'filename' in doc:
                label = f"[filename: {doc['filename']}]"
            elif 'id' in doc:
                label = f"[doc_id: {doc['id']}]"
        if not label:
            label = "[context chunk]"
        # Get the text content
        if hasattr(doc, "content"):
            text = doc.content
        elif hasattr(doc, "page_content"):
            text = doc.page_content
        elif isinstance(doc, dict):
            if "page_content" in doc:
                text = doc["page_content"]
            elif "text" in doc:
                text = doc["text"]
            else:
                text = str(doc)
        elif isinstance(doc, str):
            text = doc
        else:
            text = str(doc)
        return f"{label} {text}"

    def _get_doc_debug_info(self, doc, index: int) -> str:
        """Extract minimal debug information from a document for logging."""
        try:
            # Try to get primary key or unique identifier
            if hasattr(doc, 'metadata') and doc.metadata:
                # Check for common ID fields
                for id_field in ['pk', 'id', '_id', 'document_id', 'source']:
                    if id_field in doc.metadata:
                        return f"Doc {index}: {id_field}={doc.metadata[id_field]}"
                
                # If no ID found, show source/filename if available  
                if 'source' in doc.metadata:
                    return f"Doc {index}: source={doc.metadata['source']}"
                elif 'filename' in doc.metadata:
                    return f"Doc {index}: file={doc.metadata['filename']}"
                else:
                    # Show first few metadata keys
                    keys = list(doc.metadata.keys())[:3]
                    return f"Doc {index}: metadata_keys={keys}"
            else:
                # Fallback to document type and content preview
                content_preview = ""
                if hasattr(doc, 'page_content'):
                    content_preview = doc.page_content[:50] + "..." if len(doc.page_content) > 50 else doc.page_content
                elif hasattr(doc, 'content'):
                    content_preview = doc.content[:50] + "..." if len(doc.content) > 50 else doc.content
                
                return f"Doc {index}: type={type(doc).__name__}, preview='{content_preview}'"
        except Exception as e:
            return f"Doc {index}: error extracting info - {str(e)}"