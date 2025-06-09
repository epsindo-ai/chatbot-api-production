"""
Utility functions for cleaning and processing conversation titles.
"""
import re


def clean_title(title: str) -> str:
    """
    Clean and sanitize generated titles to remove unwanted characters.
    
    Args:
        title: Raw title from LLM
        
    Returns:
        Cleaned title suitable for display
    """
    if not title or not title.strip():
        return "New Conversation"
    
    original_title = title
    
    # Handle transition patterns first (most common issue)
    # Pattern: "Old Title" → "New Title" or similar variations
    transition_patterns = [
        r'["\']?([^"\'→←↑↓➜⟶⟵]+)["\']?\s*[→←↑↓➜⟶⟵]+\s*["\']?([^"\'→←↑↓➜⟶⟵]+)["\']?',
        r'([^→←↑↓➜⟶⟵]+)\s*[→←↑↓➜⟶⟵]+\s*([^→←↑↓➜⟶⟵]+)',
        r'.*\s+to\s+["\']?([^"\']+)["\']?$',
        r'.*\s+from\s+["\']?([^"\']+)["\']?$',
        r'from\s+["\']?([^"\']+)["\']?\s+to\s+["\']?([^"\']+)["\']?'
    ]
    
    for pattern in transition_patterns:
        match = re.search(pattern, title, re.IGNORECASE)
        if match:
            # Take the last captured group (typically the "new" title)
            groups = match.groups()
            if groups:
                # Use the last non-empty group
                for group in reversed(groups):
                    if group and group.strip():
                        title = group.strip()
                        break
            break
    
    # Remove common markdown symbols
    title = re.sub(r'\*+', '', title)  # Remove * and **
    title = re.sub(r'_+', '', title)  # Remove _ and __
    title = re.sub(r'`+', '', title)  # Remove backticks
    title = re.sub(r'~+', '', title)  # Remove tildes
    title = re.sub(r'#+', '', title)  # Remove headers
    
    # Remove arrows and directional symbols
    title = re.sub(r'[→←↑↓➜⟶⟵]', ' ', title)
    
    # Remove brackets but keep content inside
    title = re.sub(r'[\[\](){}<>]', '', title)
    
    # Remove quotes
    title = re.sub(r'[""\'\'"]', '', title)
    
    # Remove transition words that might remain
    title = re.sub(r'\b(to|from|towards|into|onto)\b', ' ', title, flags=re.IGNORECASE)
    
    # Remove excess punctuation (multiple consecutive punctuation marks)
    title = re.sub(r'[!]{2,}', '', title)
    title = re.sub(r'[?]{2,}', '', title)
    title = re.sub(r'[.]{2,}', '', title)
    title = re.sub(r'[,]{2,}', '', title)
    title = re.sub(r'[-]{2,}', ' ', title)  # Replace multiple dashes with space
    
    # Clean up extra whitespace
    title = ' '.join(title.split())
    
    # Limit to 5 words
    words = title.split()
    if len(words) > 5:
        title = ' '.join(words[:5])
    
    # Final cleanup
    title = title.strip()
    if not title:
        return "New Conversation"
    
    # Preserve proper capitalization by extracting clean words from original
    # and matching them with cleaned words while preserving original case
    original_words = re.findall(r'\b[A-Za-z]+\b', original_title)
    cleaned_words = title.split()
    
    result_words = []
    original_idx = 0
    
    for cleaned_word in cleaned_words:
        # Find the next matching word in original (case-insensitive)
        matching_original = None
        for i in range(original_idx, len(original_words)):
            if original_words[i].lower() == cleaned_word.lower():
                matching_original = original_words[i]
                original_idx = i + 1
                break
        
        if matching_original:
            result_words.append(matching_original)
        else:
            # If no match found, use the cleaned word as is
            result_words.append(cleaned_word)
    
    return ' '.join(result_words) if result_words else "New Conversation"
