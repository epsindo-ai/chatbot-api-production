from typing import List, Dict, Any, Optional, Union
import io
import json
import uuid
from pathlib import Path

from app.utils.parser import (
    clean_text, 
    split_text_into_chunks, 
    extract_metadata_from_text,
    prepare_text_for_embedding
)

# Supported document types
TEXT_EXTENSIONS = ['.txt', '.md', '.csv', '.json']

class Document:
    """Represents a document with content and metadata."""
    
    def __init__(self, 
                 content: str, 
                 metadata: Optional[Dict[str, Any]] = None,
                 doc_id: Optional[str] = None):
        """
        Initialize a document.
        
        Args:
            content: The document content
            metadata: Optional metadata for the document
            doc_id: Optional document ID (will generate UUID if not provided)
        """
        self.content = content
        self.metadata = metadata or {}
        self.doc_id = doc_id or str(uuid.uuid4())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert document to dictionary."""
        return {
            "id": self.doc_id,
            "content": self.content,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Document':
        """Create document from dictionary."""
        return cls(
            content=data.get("content", ""),
            metadata=data.get("metadata", {}),
            doc_id=data.get("id")
        )

class DocumentProcessor:
    """Processes documents for the RAG system."""
    
    def __init__(self, 
                 chunk_size: int = 1000, 
                 chunk_overlap: int = 200):
        """
        Initialize the document processor.
        
        Args:
            chunk_size: Size of text chunks for processing
            chunk_overlap: Overlap between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def process_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Document]:
        """
        Process raw text into document chunks.
        
        Args:
            text: Raw text to process
            metadata: Optional metadata to include
            
        Returns:
            List of Document objects
        """
        # Clean the text
        text = clean_text(text)
        
        # Extract metadata if not provided
        if metadata is None:
            extracted_metadata = extract_metadata_from_text(text)
            metadata = extracted_metadata
        
        # Split into chunks
        chunks = split_text_into_chunks(
            text, 
            chunk_size=self.chunk_size, 
            overlap=self.chunk_overlap
        )
        
        # Create documents from chunks
        documents = []
        for i, chunk in enumerate(chunks):
            # Prepare the text for embedding
            processed_text = prepare_text_for_embedding(chunk)
            
            # Create a document with metadata
            chunk_metadata = metadata.copy()
            chunk_metadata["chunk"] = i
            chunk_metadata["chunk_total"] = len(chunks)
            
            doc = Document(
                content=processed_text,
                metadata=chunk_metadata
            )
            documents.append(doc)
        
        return documents
    
    def process_file(self, 
                     file_path: Union[str, Path], 
                     metadata: Optional[Dict[str, Any]] = None) -> List[Document]:
        """
        Process a file into document chunks.
        
        Args:
            file_path: Path to the file
            metadata: Optional metadata to include
            
        Returns:
            List of Document objects
        """
        file_path = Path(file_path) if isinstance(file_path, str) else file_path
        
        # Create basic metadata if not provided
        if metadata is None:
            metadata = {
                "source": file_path.name,
                "file_type": file_path.suffix.lower(),
            }
        else:
            # Add source and file_type if not already in metadata
            if "source" not in metadata:
                metadata["source"] = file_path.name
            if "file_type" not in metadata:
                metadata["file_type"] = file_path.suffix.lower()
        
        # Process based on file type
        if file_path.suffix.lower() in TEXT_EXTENSIONS:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            return self.process_text(text, metadata)
        else:
            raise ValueError(f"Unsupported file type: {file_path.suffix}")
    
    def process_file_object(self, 
                           file_obj: io.BytesIO,
                           filename: str,
                           metadata: Optional[Dict[str, Any]] = None) -> List[Document]:
        """
        Process a file object into document chunks.
        
        Args:
            file_obj: File-like object
            filename: Name of the file
            metadata: Optional metadata to include
            
        Returns:
            List of Document objects
        """
        file_path = Path(filename)
        
        # Create basic metadata if not provided
        if metadata is None:
            metadata = {
                "source": filename,
                "file_type": file_path.suffix.lower(),
            }
        else:
            # Add source and file_type if not already in metadata
            if "source" not in metadata:
                metadata["source"] = filename
            if "file_type" not in metadata:
                metadata["file_type"] = file_path.suffix.lower()
        
        # Process based on file type
        if file_path.suffix.lower() in TEXT_EXTENSIONS:
            content = file_obj.read().decode('utf-8')
            return self.process_text(content, metadata)
        else:
            raise ValueError(f"Unsupported file type: {file_path.suffix}")
    
    def prepare_documents_for_vectorstore(self, documents: List[Document]) -> List[Dict[str, Any]]:
        """
        Prepare documents for insertion into a vector store.
        
        Args:
            documents: List of Document objects
            
        Returns:
            List of dictionaries with text and metadata
        """
        return [
            {
                "text": doc.content,
                "metadata": doc.metadata
            }
            for doc in documents
        ] 