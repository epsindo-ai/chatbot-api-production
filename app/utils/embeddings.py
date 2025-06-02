import requests
from typing import List, Optional
import numpy as np
from langchain_core.embeddings import Embeddings

class RemoteEmbedder(Embeddings):
    """
    Embeddings implementation that calls a remote API for embeddings.
    
    This class allows integration with remote embedding services that might be
    running specialized embedding models.
    """
    
    def __init__(self, api_url: str):
        """
        Initialize with the API URL for the remote embedding service.
        
        Args:
            api_url: URL of the remote embedding service
        """
        self.api_url = api_url.rstrip("/")
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a list of documents using the remote API.
        
        Args:
            texts: List of document texts to embed
            
        Returns:
            List of embeddings, one for each document
        """
        try:
            response = requests.post(
                f"{self.api_url}/embed_documents",
                json={"texts": texts}
            )
            response.raise_for_status()
            return response.json()["embeddings"]
        except Exception as e:
            # Fallback to individual embedding on failure
            print(f"Batch embedding failed: {e}, trying individual embeddings")
            return [self.embed_query(text) for text in texts]
    
    def embed_query(self, text: str) -> List[float]:
        """
        Embed a query text using the remote API.
        
        Args:
            text: Query text to embed
            
        Returns:
            Embedding for the query
        """
        response = requests.post(
            f"{self.api_url}/embed_query",
            json={"text": text}
        )
        response.raise_for_status()
        return response.json()["embedding"]
        
    def embed_all(self, texts: List[str]) -> List[List[float]]:
        """Alias for embed_documents, for compatibility with some interfaces."""
        return self.embed_documents(texts) 