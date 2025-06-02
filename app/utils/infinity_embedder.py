from typing import List, Any, Optional, Dict, Union
from langchain_community.embeddings import InfinityEmbeddings
from langchain_core.embeddings import Embeddings
import requests
import time
import json
import logging
import numpy as np

logger = logging.getLogger(__name__)

class InfinityEmbedder(Embeddings):
    """
    Service for generating embeddings using Infinity model.
    Implements the langchain_core.embeddings.Embeddings interface.
    """
    
    def __init__(self, 
                 model: str = "stella-en-1.5B", 
                 infinity_api_url: str = "http://192.168.1.10:33325",
                 batch_size: int = 32,
                 retry_count: int = 3,
                 timeout: int = 60):
        """
        Initialize the Infinity Embedder.
        
        Args:
            model: Model name to use for embeddings
            infinity_api_url: URL of the Infinity API server
            batch_size: Number of texts to embed in a single request
            retry_count: Number of retries for failed requests
            timeout: Request timeout in seconds
        """
        self.model = model
        self.api_url = infinity_api_url
        self.batch_size = batch_size
        self.retry_count = retry_count
        self.timeout = timeout
        
        self.client = InfinityEmbeddings(
            model=self.model,
            infinity_api_url=self.api_url
        )
        
        logger.info(f"Initialized InfinityEmbedder with model {model} at {infinity_api_url}")
        
    def embed_query(self, query: str) -> List[float]:
        """
        Generate embeddings for a single query text.
        
        Args:
            query: Text to embed
            
        Returns:
            List of floats representing the embedding
        """
        # Handle empty input
        if not query or not query.strip():
            logger.warning("Received empty text for embedding")
            # Return a zero vector of appropriate size (get size from a dummy embedding)
            dummy = "This is a placeholder text for embedding"
            dummy_embedding = self.client.embed_query(dummy)
            return [0.0] * len(dummy_embedding)
        
        for attempt in range(self.retry_count):
            try:
                return self.client.embed_query(query)
            except Exception as e:
                logger.error(f"Error embedding query (attempt {attempt+1}/{self.retry_count}): {str(e)}")
                if attempt == self.retry_count - 1:
                    raise
                time.sleep(1)
    
    def embed_documents(self, documents: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of documents.
        
        Args:
            documents: List of documents to embed
            
        Returns:
            List of embeddings (each embedding is a list of floats)
        """
        # Handle empty input
        if not documents:
            logger.warning("Received empty document list for embedding")
            return []
        
        # Filter out empty strings and log warnings
        filtered_docs = []
        empty_indices = []
        for i, doc in enumerate(documents):
            if doc and doc.strip():
                filtered_docs.append(doc)
            else:
                logger.warning(f"Empty document at index {i} will be replaced with zero vector")
                empty_indices.append(i)
        
        # Process in batches for better performance and stability
        all_embeddings = []
        for i in range(0, len(filtered_docs), self.batch_size):
            batch = filtered_docs[i:i+self.batch_size]
            for attempt in range(self.retry_count):
                try:
                    batch_embeddings = self.client.embed_documents(batch)
                    all_embeddings.extend(batch_embeddings)
                    break
                except Exception as e:
                    logger.error(f"Error embedding batch {i//self.batch_size} (attempt {attempt+1}/{self.retry_count}): {str(e)}")
                    if attempt == self.retry_count - 1:
                        raise
                    time.sleep(1)
        
        # If we had empty texts, insert zero vectors at the appropriate positions
        if empty_indices:
            # Get the dimension size from the first embedding
            vec_size = len(all_embeddings[0]) if all_embeddings else 1536  # Default to 1536 if no embeddings
            zero_vector = [0.0] * vec_size
            
            # Insert zero vectors at the saved indices
            for idx in empty_indices:
                all_embeddings.insert(idx, zero_vector)
        
        return all_embeddings
    
    # Add async methods required by the Embeddings interface
    async def aembed_query(self, query: str) -> List[float]:
        """
        Asynchronously generate embeddings for a single query text.
        
        Args:
            query: Text to embed
            
        Returns:
            List of floats representing the embedding
        """
        # Simple implementation using the synchronous version
        return self.embed_query(query)
    
    async def aembed_documents(self, documents: List[str]) -> List[List[float]]:
        """
        Asynchronously generate embeddings for a list of documents.
        
        Args:
            documents: List of documents to embed
            
        Returns:
            List of embeddings (each embedding is a list of floats)
        """
        # Simple implementation using the synchronous version
        return self.embed_documents(documents)
    
    def __call__(self, text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """
        Call method to make the class callable.
        
        Args:
            text: Text or list of texts to embed
            
        Returns:
            Embeddings for the input text(s)
        """
        if isinstance(text, str):
            return self.embed_query(text)
        elif isinstance(text, list):
            return self.embed_documents(text)
        else:
            raise ValueError(f"Input must be str or List[str], got {type(text)}")

    @property
    def embedding_dimension(self) -> int:
        """
        Get the dimension of the embeddings.
        
        Returns:
            Dimension size of embeddings
        """
        # Get dimension by embedding a test string
        test_text = "This is a test sentence to get embedding dimension"
        embedding = self.embed_query(test_text)
        return len(embedding)

    def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the embedding service.
        
        Returns:
            Dictionary with health information
        """
        try:
            start_time = time.time()
            sample = "Health check test"
            _ = self.embed_query(sample)
            end_time = time.time()
            
            return {
                "status": "healthy",
                "model": self.model,
                "latency_ms": round((end_time - start_time) * 1000, 2),
                "embedding_dimension": self.embedding_dimension,
                "infinity_api_url": self.api_url
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "model": self.model,
                "infinity_api_url": self.api_url
            } 