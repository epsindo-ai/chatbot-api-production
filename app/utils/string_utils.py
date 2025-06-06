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

def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename while preserving the file extension.
    Removes unsafe characters but keeps the extension intact.
    
    Args:
        filename: The original filename
        
    Returns:
        A sanitized filename with preserved extension
    """
    if not filename:
        return "file"
    
    # Split filename and extension
    if '.' in filename:
        name_part, extension = filename.rsplit('.', 1)
        # Keep the extension with dot
        extension = f".{extension}"
    else:
        name_part = filename
        extension = ""
    
    # Sanitize the name part (allow letters, numbers, hyphens, underscores)
    sanitized_name = re.sub(r'[^a-zA-Z0-9_-]', '_', name_part)
    
    # Remove multiple consecutive underscores
    sanitized_name = re.sub(r'_+', '_', sanitized_name)
    
    # Remove leading/trailing underscores
    sanitized_name = sanitized_name.strip('_')
    
    # Ensure we have at least something
    if not sanitized_name:
        sanitized_name = "file"
    
    # Combine name and extension
    return sanitized_name + extension

def conversation_collection_name(conversation_id: str) -> str:
    """
    Generate a valid Milvus collection name from a conversation ID.
    
    Args:
        conversation_id: The conversation ID
        
    Returns:
        A valid collection name
    """
    return sanitize_collection_name(f"conversation_{conversation_id}")