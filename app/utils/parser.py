import re
from typing import List, Dict, Any, Optional
import json

def clean_text(text: str) -> str:
    """
    Clean text by removing extra whitespace and normalizing.
    
    Args:
        text: Input text to clean
        
    Returns:
        Cleaned text
    """
    # Replace multiple spaces with a single space
    text = re.sub(r'\s+', ' ', text)
    # Remove leading/trailing whitespace
    text = text.strip()
    # Normalize quotes
    text = text.replace('"', '"').replace('"', '"')
    return text

def split_text_into_chunks(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """
    Split text into overlapping chunks of specified size.
    
    Args:
        text: Input text to split
        chunk_size: Maximum size of each chunk
        overlap: Number of characters to overlap between chunks
        
    Returns:
        List of text chunks
    """
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        # Get chunk of size chunk_size
        end = start + chunk_size
        
        # If we're not at the end of the text, try to find a good breaking point
        if end < len(text):
            # Try to find a period, question mark, or exclamation point followed by a space
            match = re.search(r'[.!?]\s', text[end-100:end])
            if match:
                end = end - 100 + match.end()
            else:
                # Try to find a newline
                match = re.search(r'\n', text[end-100:end])
                if match:
                    end = end - 100 + match.end()
                else:
                    # Try to find a space
                    match = re.search(r'\s', text[end-50:end])
                    if match:
                        end = end - 50 + match.end()
        
        # Add the chunk to our list
        chunks.append(text[start:end])
        
        # Move start pointer, accounting for overlap
        start = end - overlap
    
    return chunks

def extract_metadata_from_text(text: str) -> Dict[str, Any]:
    """
    Attempt to extract metadata from text (like source, author, date, etc.)
    
    Args:
        text: Input text to analyze
        
    Returns:
        Dictionary of metadata fields and values
    """
    metadata = {}
    
    # Try to extract a title (first non-empty line or first heading)
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#') and len(line) < 100:
            metadata['title'] = line
            break
    
    # Try to extract a date (simple regex pattern)
    date_pattern = r'\b\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4}\b|\b\d{4}[-/\.]\d{1,2}[-/\.]\d{1,2}\b'
    date_match = re.search(date_pattern, text)
    if date_match:
        metadata['date'] = date_match.group(0)
    
    # Try to extract an author (looking for "by" or "author" patterns)
    author_pattern = r'(?:by|author[s]?[\s:]+)([A-Z][a-z]+ [A-Z][a-z]+)'
    author_match = re.search(author_pattern, text, re.IGNORECASE)
    if author_match:
        metadata['author'] = author_match.group(1)
    
    return metadata

def parse_json_if_possible(text: str) -> Optional[Dict[str, Any]]:
    """
    Attempt to parse text as JSON.
    
    Args:
        text: Input text to parse
        
    Returns:
        Parsed JSON as dictionary or None if parsing fails
    """
    try:
        # Try to find JSON-like content (between curly braces)
        json_pattern = r'\{.*\}'
        json_match = re.search(json_pattern, text, re.DOTALL)
        
        if json_match:
            json_text = json_match.group(0)
            return json.loads(json_text)
        
        # If no JSON-like content found, try parsing the whole text
        return json.loads(text)
    except:
        return None

def extract_structured_data(text: str) -> Dict[str, Any]:
    """
    Extract structured data from text.
    
    Args:
        text: Input text to analyze
        
    Returns:
        Dictionary of extracted structured data
    """
    data = {}
    
    # Try to extract key-value pairs (format: Key: Value)
    kv_pattern = r'([A-Za-z0-9\s]+):\s*([^\n]+)'
    kv_matches = re.findall(kv_pattern, text)
    
    for key, value in kv_matches:
        key = key.strip().lower().replace(' ', '_')
        value = value.strip()
        if key and value and len(key) < 50:  # Avoid bogus matches
            data[key] = value
    
    return data

def prepare_text_for_embedding(text: str) -> str:
    """
    Prepare text specifically for embedding by cleaning and normalizing.
    
    Args:
        text: Input text to prepare
        
    Returns:
        Processed text ready for embedding
    """
    # Clean the text
    text = clean_text(text)
    
    # Remove URLs (they often don't add meaning but take up tokens)
    text = re.sub(r'https?://\S+', '', text)
    
    # Remove email addresses
    text = re.sub(r'\S+@\S+', '', text)
    
    # Remove special characters that don't add meaning
    text = re.sub(r'[^\w\s.,!?;:()\[\]{}"\'-]', ' ', text)
    
    # Remove multiple spaces again (might have been introduced by previous replacements)
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip() 