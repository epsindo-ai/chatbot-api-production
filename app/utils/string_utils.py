import re
import uuid

def sanitize_collection_name(name: str) -> str:
    """
    Sanitize a string to be used as a Milvus collection name.
    Milvus only allows letters, numbers, and underscores in collection names.
    
    Args:
        name: The string to sanitize
        
    Returns:
        A sanitized string suitable for use as a Milvus collection name
    """
    # Replace any non-alphanumeric characters with underscores
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    
    # Ensure the name starts with a letter (Milvus requirement)
    if not sanitized or not sanitized[0].isalpha():
        sanitized = f"c_{sanitized}"
    
    # Ensure the name isn't too long (Milvus has a limit)
    if len(sanitized) > 100:
        # If too long, truncate and add a hash to ensure uniqueness
        hash_suffix = uuid.uuid4().hex[:8]
        sanitized = f"{sanitized[:90]}_{hash_suffix}"
    
    return sanitized

def conversation_collection_name(conversation_id: str) -> str:
    """
    Generate a valid Milvus collection name from a conversation ID.
    
    Args:
        conversation_id: The conversation ID
        
    Returns:
        A valid collection name
    """
    return sanitize_collection_name(f"conversation_{conversation_id}") 