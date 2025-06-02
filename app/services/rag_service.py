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
from langchain.chains import create_retrieval_chain, create_history_aware_retriever
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
            print(f"DEBUG: Listed Milvus collections: {collections}")
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
    
    def create_rag_chain(self, llm, retriever, db: Session):
        """Create a RAG chain with the specified LLM and retriever, using PostgreSQL for chat history."""
        contextualize_q_system_prompt = (
            "Berdasarkan riwayat chat dan pertanyaan terakhir pengguna "
            "yang mungkin merujuk pada konteks dalam riwayat chat," 
            "bentuk pertanyaan yang dapat dipahami. "
            "Tanpa riwayat chat jangan menjawab pertanyaan,"
            "hanya reformulasi jika diperlukan dan sebaliknya kembalikan seperti semula."
        )
        contextualize_q_prompt = ChatPromptTemplate.from_messages([
            ("system", contextualize_q_system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ])
        history_aware_retriever = create_history_aware_retriever(llm, retriever, contextualize_q_prompt)

        system_prompt = (
            "You are a helpful AI assistant. Answer the user's question based on the provided context. "
            "If the answer isn't in the context, politely say you don't know rather than making up an answer. "
            "Be concise, accurate, and helpful in your response."
            "\n\n"
            "Context: {context}"
        )

        qa_prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ])
        question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)
        rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)

        # Use CustomMessageHistory for PostgreSQL
        conversational_rag_chain = RunnableWithMessageHistory(
            rag_chain,
            lambda session_id: CustomMessageHistory(session_id, db),
            input_messages_key="input",
            history_messages_key="chat_history",
            output_messages_key="answer",
        )
        return conversational_rag_chain
    
    def get_conversation_chain(self, db: Session, user_id: int, collection_name: str, conversation_id: Optional[str] = None):
        """Get or create a conversation with RAG chain for the user."""
        print(f"DEBUG: Starting get_conversation_chain, user_id={user_id}, collection_name={collection_name}, conversation_id={conversation_id}")
        
        # Get or create conversation
        is_new_conversation = False
        if conversation_id:
            db_conversation = crud.get_conversation(db, conversation_id)
            if not db_conversation:
                print(f"DEBUG: Conversation with ID {conversation_id} not found")
                raise ValueError(f"Conversation with ID {conversation_id} not found")
            print(f"DEBUG: Found existing conversation with ID {conversation_id}")
        else:
            db_conversation = crud.create_conversation(db, user_id)
            is_new_conversation = True
            conversation_id = db_conversation.id
            print(f"DEBUG: Created new conversation with ID {conversation_id}")
        
        # Sanitize collection name for Milvus
        from app.utils.string_utils import sanitize_collection_name
        safe_collection_name = sanitize_collection_name(collection_name)
        print(f"DEBUG: Sanitized collection name: {collection_name} -> {safe_collection_name}")
        
        # Check if collection exists in Milvus
        collection_exists = self.vectorstore_manager.collection_exists(safe_collection_name)
        print(f"DEBUG: Collection exists in Milvus: {collection_exists}")
        
        try:
            # Create LLM and retriever
            print(f"DEBUG: Creating LLM")
            llm = self.get_llm(db)
            print(f"DEBUG: Created LLM with model {llm.model_name}")
            
            print(f"DEBUG: Creating retriever for collection {collection_name}")
            retriever = self.vectorstore_manager.get_retriever(collection_name)
            print(f"DEBUG: Successfully created retriever")
            
            # Create the RAG chain
            print(f"DEBUG: Creating RAG chain")
            rag_chain = self.create_rag_chain(llm, retriever, db)
            print(f"DEBUG: Successfully created RAG chain")
            
            # Add message history integration
            def get_session_history(session_id):
                print(f"DEBUG: Getting session history for {session_id}")
                return CustomMessageHistory(session_id, db)
            
            print(f"DEBUG: Creating RunnableWithMessageHistory")
            conversational_rag_chain = RunnableWithMessageHistory(
                rag_chain,
                get_session_history,
                input_messages_key="input",
                history_messages_key="chat_history",
                output_messages_key="answer",
            )
            print(f"DEBUG: Successfully created RAG chain with message history")
            
            return conversational_rag_chain, conversation_id, is_new_conversation
        
        except Exception as e:
            print(f"DEBUG: ERROR in get_conversation_chain: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
    
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
            
            # Create retriever
            retriever = self.vectorstore_manager.get_retriever(collection_name)
            
            # Create the contextualize question chain
            contextualize_q_system_prompt = (
                "Given the chat history and the latest user question, "
                "create a standalone question that captures all relevant context. "
                "If there's no relevant context, return the original question unchanged."
            )
            
            contextualize_q_prompt = ChatPromptTemplate.from_messages([
                ("system", contextualize_q_system_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
            ])
            
            # Use a non-streaming LLM for context
            context_llm = self.get_llm(db, streaming=False)
            contextualizer = contextualize_q_prompt | context_llm | StrOutputParser()
            
            # Get chat history
            chat_history = history.messages
            
            # Get contextualized question using LangChain's native async method
            contextualized_question = await contextualizer.ainvoke({
                "chat_history": chat_history,
                "input": message
            })
            
            # Retrieve relevant documents using LangChain's native async method
            relevant_docs = await retriever.ainvoke(contextualized_question)
            
            # Format context from documents
            context_texts = []
            for i, doc in enumerate(relevant_docs):
                print(f"DEBUG: Doc {i} type: {type(doc)}, value: {repr(doc)[:200]}")
                context_texts.append(self._extract_doc_text(doc))
            context = "\n\n".join(context_texts)
            print(f"DEBUG: Created context with {len(context)} characters from {len(relevant_docs)} documents")
            
            # Create streaming QA chain
            qa_system_prompt = (
                "You are a helpful AI assistant. Answer the user's question based on the provided context. "
                "If the answer isn't in the context, politely say you don't know rather than making up an answer. "
                "Be concise, accurate, and helpful in your response."
                "\n\n"
                "Context: {context}"
            )
            
            qa_prompt = ChatPromptTemplate.from_messages([
                ("system", qa_system_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
            ])
            
            # Prepare to collect the full response
            full_response = []
            
            # Generate streaming response using LangChain's native async streaming
            chain = qa_prompt | llm
            
            # Use LangChain's native async streaming method
            async for chunk in chain.astream({
                "context": context,
                "chat_history": chat_history,
                "input": message
            }):
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

            # Create retriever
            retriever = self.vectorstore_manager.get_retriever(collection_name)

            # Create the contextualize question chain
            contextualize_q_system_prompt = (
                "Given the chat history and the latest user question, "
                "create a standalone question that captures all relevant context. "
                "If there's no relevant context, return the original question unchanged."
            )
            contextualize_q_prompt = ChatPromptTemplate.from_messages([
                ("system", contextualize_q_system_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
            ])
            # Use a non-streaming LLM for context
            context_llm = self.get_llm(db, streaming=False)
            contextualizer = contextualize_q_prompt | context_llm | StrOutputParser()

            # Get chat history
            chat_history = history.messages

            # Get contextualized question using LangChain's native async method
            contextualized_question = await contextualizer.ainvoke({
                "chat_history": chat_history,
                "input": message
            })

            # Retrieve relevant documents using LangChain's native async method
            relevant_docs = await retriever.ainvoke(contextualized_question)

            # Format context from documents
            context_texts = []
            for i, doc in enumerate(relevant_docs):
                print(f"DEBUG: Doc {i} type: {type(doc)}, value: {repr(doc)[:200]}")
                context_texts.append(self._extract_doc_text(doc))
            context = "\n\n".join(context_texts)
            print(f"DEBUG: Created context with {len(context)} characters from {len(relevant_docs)} documents")

            # Create QA chain (non-streaming)
            qa_system_prompt = (
                "You are a helpful AI assistant. Answer the user's question based on the provided context. "
                "If the answer isn't in the context, politely say you don't know rather than making up an answer. "
                "Be concise, accurate, and helpful in your response."
                "\n\n"
                "Context: {context}"
            )
            qa_prompt = ChatPromptTemplate.from_messages([
                ("system", qa_system_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
            ])
            chain = qa_prompt | llm

            # Run the chain and collect the full response using LangChain's native async method
            result = await chain.ainvoke({
                "context": context,
                "chat_history": chat_history,
                "input": message
            })
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
            
            # Create LLM using the get_llm method
            llm = self.get_llm(db)
            print(f"DEBUG: Created LLM with model {llm.model_name}")
            
            # Get system prompt from settings or use default
            system_prompt = getattr(settings, 'RAG_SYSTEM_PROMPT', DEFAULT_RAG_SYSTEM_PROMPT)
            
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
                    # Get retriever for this collection - use a safe top_k value (4 is typically safe with Milvus)
                    top_k = 4  # Use a fixed safe value instead of admin_config to avoid the limit error
                    retriever = self.vectorstore_manager.get_retriever(
                        collection_name=conversation_collection,
                        top_k=top_k
                    )
                    print(f"DEBUG: Created retriever for collection: {conversation_collection}")
                    
                    # Retrieve relevant documents using LangChain's native async method
                    retrieved_docs = await retriever.ainvoke(query)
                    print(f"DEBUG: Retrieved {len(retrieved_docs)} documents from collection")
                    if retrieved_docs:
                        first_doc = retrieved_docs[0]
                        print(f"DEBUG: Type of first retrieved doc: {type(first_doc)}")
                        if isinstance(first_doc, dict):
                            print(f"DEBUG: First doc keys: {list(first_doc.keys())}")
                            print(f"DEBUG: First doc values: {first_doc}")
                        elif hasattr(first_doc, '__dict__'):
                            print(f"DEBUG: First doc __dict__: {first_doc.__dict__}")
                            if hasattr(first_doc, 'page_content'):
                                print(f"DEBUG: first_doc.page_content: {getattr(first_doc, 'page_content', None)}")
                            else:
                                print("DEBUG: first_doc does not have page_content attribute")
                        else:
                            print(f"DEBUG: First doc value: {repr(first_doc)}")
                    else:
                        print("DEBUG: No documents retrieved.")
                    # Join the text of the retrieved documents
                    context_texts = []
                    for i, doc in enumerate(retrieved_docs):
                        print(f"DEBUG: Doc {i} type: {type(doc)}, value: {repr(doc)[:200]}")
                        context_texts.append(self._extract_doc_text(doc))
                    context = "\n\n".join(context_texts)
                    print(f"DEBUG: Created context with {len(context)} characters from {len(retrieved_docs)} documents")
                    
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
            
            # Create retriever
            retriever = vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 5}
            )
            
            # Get relevant documents using LangChain's native async method
            docs = await retriever.ainvoke(query)
            
            # Format context from documents
            context_parts = [self._extract_doc_text(doc) for doc in docs]
            context = "\n\n".join(context_parts)
            
            # Create prompt
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are a helpful assistant that answers questions based on the provided context. "
                           "If you don't know the answer based on the context, say you don't know. "
                           "Do not make up information. Always cite the document source when referring to specific information."),
                ("system", "Context information is below.\n{context}"),
                ("system", "Previous conversation history:\n{chat_history}"),
                ("human", "{input}")
            ])
            
            # Create chat model
            chat = ChatOpenAI(
                model=settings.LLM_MODEL,
                api_key=settings.OPENAI_API_KEY,
                temperature=0.7,
                streaming=True
            )
            
            # Create chain
            chain = prompt | chat
            
            # Stream the response
            full_response = []
            
            # Use LangChain's native async streaming method
            async for chunk in chain.astream({
                "context": context,
                "chat_history": history_text,
                "input": query
            }):
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
        print(f"_extract_doc_text: type={type(doc)}, value={repr(doc)[:200]}")
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