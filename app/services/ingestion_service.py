import io
import os
import time
import logging
from typing import List, Dict, Any, Optional, Union, Tuple, BinaryIO
from pathlib import Path
import tempfile

from langchain_core.documents import Document
from langchain_milvus.vectorstores import Milvus

from app.config import settings
from app.utils.infinity_embedder import InfinityEmbedder
from app.services.document_processor import DoclingProcessor
from app.services.rag_service import RemoteVectorStoreManager
from app.utils.string_utils import sanitize_collection_name

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
                   handlers=[logging.StreamHandler()])
logger = logging.getLogger("ingestion_service")

class DocumentIngestionService:
    """Service for ingesting documents into the vector store."""
    
    def __init__(self):
        """Initialize the document ingestion service."""
        logger.info("=== INITIALIZING DOCUMENT INGESTION SERVICE ===")
        
        # STEP 1: Initialize embeddings
        logger.info("STEP 1: Initializing Infinity embedder")
        try:
            self.embeddings = InfinityEmbedder(
                model=settings.INFINITY_EMBEDDINGS_MODEL,
                infinity_api_url=settings.INFINITY_API_URL
            )
            logger.info(f"Embedder initialized with model: {settings.INFINITY_EMBEDDINGS_MODEL}")
        except Exception as e:
            logger.error(f"Failed to initialize embedder: {e}", exc_info=True)
            raise
        
        # STEP 2: Initialize document processor
        logger.info("STEP 2: Initializing document processor")
        try:
            self.document_processor = DoclingProcessor(
                parser_artifact_path=settings.DOCLING_PARSER_PATH,
                embed_model_id=settings.DOCLING_EMBED_MODEL,
                use_gpu=False  # Force CPU mode
            )
            logger.info("Document processor initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize document processor: {e}", exc_info=True)
            raise
        
        # STEP 3: Initialize vector store manager
        logger.info("STEP 3: Initializing vector store manager")
        try:
            self.vectorstore_manager = RemoteVectorStoreManager(
                settings.REMOTE_EMBEDDER_URL,
                settings.MILVUS_URI
            )
            logger.info(f"Vector store manager initialized with URI: {settings.MILVUS_URI}")
        except Exception as e:
            logger.error(f"Failed to initialize vector store manager: {e}", exc_info=True)
            raise
        
        logger.info("=== DOCUMENT INGESTION SERVICE INITIALIZED ===")
    
    def get_vector_store(self, collection_name: str) -> Milvus:
        """
        Get or create a Milvus vector store.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            Milvus vector store
        """
        logger.info(f"Getting vector store for collection: {collection_name}")
        
        # Sanitize collection name for Milvus
        safe_collection_name = sanitize_collection_name(collection_name)
        logger.info(f"Sanitized collection name: {safe_collection_name}")
        
        try:
            vector_store = Milvus(
                embedding_function=self.embeddings,
                collection_name=safe_collection_name,
                connection_args={"uri": settings.MILVUS_URI},
                auto_id=True
            )
            logger.info(f"Successfully got/created vector store for collection: {safe_collection_name}")
            return vector_store
        except Exception as e:
            logger.error(f"Failed to get/create vector store: {e}", exc_info=True)
            raise
    
    def ingest_file(self, file_path: str, collection_name: str, metadata: Optional[Dict[str, Any]] = None) -> int:
        """
        Ingest a file into the vector store.
        
        Args:
            file_path: Path to the file
            collection_name: Name of the collection
            metadata: Additional metadata to add to documents
            
        Returns:
            Number of documents processed
        """
        logger.info(f"=== STARTING FILE INGESTION: {file_path} ===")
        start_time = time.time()
        
        # STEP 1: Process file with Docling
        logger.info("STEP 1: Processing file with Docling")
        process_start = time.time()
        docs = self.document_processor.process_files([file_path], metadata)
        process_time = time.time() - process_start
        
        if not docs:
            logger.warning("No documents were produced by the document processor")
            return 0
        
        logger.info(f"Document processing completed in {process_time:.2f} seconds, produced {len(docs)} chunks")
        
        # STEP 2: Add to vector store
        logger.info(f"STEP 2: Adding {len(docs)} chunks to vector store")
        vector_start = time.time()
        try:
            vector_store = self.get_vector_store(collection_name)
            logger.info(f"Starting vectorization of {len(docs)} chunks")
            vector_store.add_documents(docs)
            vector_time = time.time() - vector_start
            logger.info(f"Vectorization completed in {vector_time:.2f} seconds")
        except Exception as e:
            logger.error(f"Failed to add documents to vector store: {e}", exc_info=True)
            return 0
        
        total_time = time.time() - start_time
        logger.info(f"=== FILE INGESTION COMPLETED IN {total_time:.2f} SECONDS ===")
        return len(docs)
    
    def ingest_file_object(self, file_obj: BinaryIO, filename: str, collection_name: str, metadata: Optional[Dict[str, Any]] = None) -> int:
        """
        Ingest a file object into the vector store.
        
        Args:
            file_obj: File-like object
            filename: Name of the file
            collection_name: Name of the collection
            metadata: Additional metadata to add to documents
            
        Returns:
            Number of documents processed
        """
        logger.info(f"=== STARTING FILE OBJECT INGESTION: {filename} ===")
        start_time = time.time()
        
        # STEP 1: Get file content and determine mime type
        logger.info("STEP 1: Reading file content and determining MIME type")
        try:
            content = file_obj.read()
            file_size = len(content)
            mime_type = self._guess_mime_type(filename)
            logger.info(f"Read file content: {file_size} bytes, MIME type: {mime_type}")
        except Exception as e:
            logger.error(f"Failed to read file content: {e}", exc_info=True)
            return 0
        
        # STEP 2: Process with Docling
        logger.info("STEP 2: Processing with Docling")
        process_start = time.time()
        try:
            docs = self.document_processor.process_file_objects([(content, filename, mime_type)], metadata)
            process_time = time.time() - process_start
            
            if not docs:
                logger.warning("No documents were produced by the document processor")
                return 0
                
            logger.info(f"Document processing completed in {process_time:.2f} seconds, produced {len(docs)} chunks")
        except Exception as e:
            logger.error(f"Failed to process file with Docling: {e}", exc_info=True)
            return 0
        
        # STEP 3: Add to vector store
        logger.info(f"STEP 3: Adding {len(docs)} chunks to vector store")
        vector_start = time.time()
        try:
            # Add to vector store using sanitized collection name
            vector_store = self.get_vector_store(collection_name)
            logger.info(f"Starting vectorization of {len(docs)} chunks")
            vector_store.add_documents(docs)
            vector_time = time.time() - vector_start
            logger.info(f"Vectorization completed in {vector_time:.2f} seconds")
        except Exception as e:
            logger.error(f"Failed to add documents to vector store: {e}", exc_info=True)
            return 0
        
        total_time = time.time() - start_time
        logger.info(f"=== FILE OBJECT INGESTION COMPLETED IN {total_time:.2f} SECONDS ===")
        return len(docs)
    
    def ingest_text(self, text: str, collection_name: str, metadata: Optional[Dict[str, Any]] = None) -> int:
        """
        Ingest text directly into the vector store.
        
        Args:
            text: Text to ingest
            collection_name: Name of the collection
            metadata: Additional metadata to add to documents
            
        Returns:
            Number of documents processed
        """
        logger.info(f"=== STARTING TEXT INGESTION FOR COLLECTION: {collection_name} ===")
        start_time = time.time()
        
        # Create document
        if metadata is None:
            metadata = {}
        
        logger.info(f"Text length: {len(text)} characters")
        
        # STEP 1: Save text to temporary file and process with Docling
        logger.info("STEP 1: Saving text to temporary file")
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as temp_file:
                temp_file.write(text.encode('utf-8'))
                temp_path = temp_file.name
                logger.info(f"Text saved to temporary file: {temp_path}")
        except Exception as e:
            logger.error(f"Failed to save text to temporary file: {e}", exc_info=True)
            return 0
        
        try:
            # STEP 2: Process with Docling
            logger.info("STEP 2: Processing with Docling")
            process_start = time.time()
            docs = self.document_processor.process_files([temp_path], metadata)
            process_time = time.time() - process_start
            
            # If Docling fails, create a basic document without chunking
            if not docs:
                logger.warning("Docling processing failed, creating basic document without chunking")
                docs = [Document(page_content=text, metadata=metadata)]
            
            logger.info(f"Document processing completed in {process_time:.2f} seconds, produced {len(docs)} chunks")
            
            # STEP 3: Add to vector store
            logger.info(f"STEP 3: Adding {len(docs)} chunks to vector store")
            vector_start = time.time()
            try:
                # Add to vector store
                vector_store = self.get_vector_store(collection_name)
                logger.info(f"Starting vectorization of {len(docs)} chunks")
                vector_store.add_documents(docs)
                vector_time = time.time() - vector_start
                logger.info(f"Vectorization completed in {vector_time:.2f} seconds")
            except Exception as e:
                logger.error(f"Failed to add documents to vector store: {e}", exc_info=True)
                return 0
            
            total_time = time.time() - start_time
            logger.info(f"=== TEXT INGESTION COMPLETED IN {total_time:.2f} SECONDS ===")
            return len(docs)
        
        finally:
            # Clean up temporary file
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                    logger.info(f"Removed temporary file: {temp_path}")
                except Exception as e:
                    logger.error(f"Failed to remove temporary file: {e}")
    
    def _guess_mime_type(self, filename: str) -> str:
        """
        Guess the MIME type of a file based on its extension.
        
        Args:
            filename: Name of the file
            
        Returns:
            MIME type string
        """
        ext = os.path.splitext(filename.lower())[1]
        
        mime_types = {
            '.pdf': 'application/pdf',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.doc': 'application/msword',
            '.txt': 'text/plain',
            '.csv': 'text/csv',
            '.md': 'text/markdown',
            '.json': 'application/json',
            '.html': 'text/html',
            '.htm': 'text/html',
            '.xml': 'application/xml'
        }
        
        mime_type = mime_types.get(ext, 'application/octet-stream')
        logger.info(f"Guessed MIME type for {filename}: {mime_type}")
        return mime_type
    
    def create_new_collection(self, collection_name: str, description: str = "") -> bool:
        """
        Create a new collection in the vector store.
        
        Args:
            collection_name: Name of the collection to create
            description: Optional description for the collection
            
        Returns:
            True if collection was created, False if it already exists
        """
        logger.info(f"=== CREATING NEW COLLECTION: {collection_name} ===")
        
        try:
            # Sanitize collection name for Milvus
            safe_collection_name = sanitize_collection_name(collection_name)
            logger.info(f"Sanitized collection name: {safe_collection_name}")
            
            # Check if collection exists
            collections = self.vectorstore_manager.list_collections()
            logger.info(f"Existing collections: {collections}")
            
            if safe_collection_name in collections:
                logger.info(f"Collection '{safe_collection_name}' already exists")
                return False
            
            # Create a new empty vectorstore with the collection name
            # This will initialize the collection in Milvus
            logger.info(f"Creating new collection in Milvus: {safe_collection_name}")
            try:
                Milvus(
                    embedding_function=self.embeddings,
                    collection_name=safe_collection_name,
                    connection_args={"uri": settings.MILVUS_URI}
                )
                logger.info(f"Successfully created collection: {safe_collection_name}")
                return True
            except Exception as e:
                logger.error(f"Failed to create Milvus collection: {e}", exc_info=True)
                return False
        except Exception as e:
            logger.error(f"Error creating collection {collection_name}: {e}", exc_info=True)
            return False
    
    def delete_collection(self, collection_name: str) -> bool:
        """
        Delete a collection from the vector store.
        
        Args:
            collection_name: Name of the collection to delete
            
        Returns:
            True if collection was deleted, False otherwise
        """
        logger.info(f"=== DELETING COLLECTION: {collection_name} ===")
        
        try:
            from pymilvus import connections, utility
            
            # Connect to Milvus
            logger.info(f"Connecting to Milvus: {settings.MILVUS_URI}")
            connections.connect(uri=settings.MILVUS_URI)
            
            # Check if collection exists
            if utility.has_collection(collection_name):
                logger.info(f"Found collection, dropping: {collection_name}")
                utility.drop_collection(collection_name)
                logger.info(f"Successfully deleted collection: {collection_name}")
                return True
            
            logger.info(f"Collection does not exist: {collection_name}")
            return False
        except Exception as e:
            logger.error(f"Error deleting collection: {e}", exc_info=True)
            return False 