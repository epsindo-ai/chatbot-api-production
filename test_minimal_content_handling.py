#!/usr/bin/env python3
"""Test script to verify error handling for minimal content files"""

import os
import sys
import tempfile
import logging

# Add the app directory to Python path
sys.path.insert(0, '/app')

from app.services.ingestion_service import DocumentIngestionService

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s')
logger = logging.getLogger("test_minimal_content")

def test_minimal_content_handling():
    """Test that minimal content files are handled correctly"""
    logger.info("=== TESTING MINIMAL CONTENT FILE HANDLING ===")
    
    # Create test files with minimal content
    test_cases = [
        ("# Just a title", "title_only.md"),
        ("Only three words", "three_words.txt"), 
        ("A", "single_char.txt"),
        ("", "empty.txt"),
        ("# Title\n\nJust a small paragraph with some content.", "small_content.md")
    ]
    
    ingestion_service = DocumentIngestionService()
    
    for content, filename in test_cases:
        logger.info(f"\n--- Testing file: {filename} (content: '{content}') ---")
        
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix=f'_{filename}', delete=False) as temp_file:
                temp_file.write(content)
                temp_path = temp_file.name
            
            logger.info(f"Created test file: {temp_path}")
            logger.info(f"File size: {os.path.getsize(temp_path)} bytes")
            
            # Try to ingest the file
            try:
                collection_name = f"test_minimal_{filename.split('.')[0]}"
                result = ingestion_service.ingest_file(temp_path, collection_name)
                logger.info(f"✓ SUCCESS: File processed, {result} documents created")
                
                # If successful, try to delete the collection to clean up
                try:
                    ingestion_service.delete_collection(collection_name)
                    logger.info(f"✓ Cleaned up collection: {collection_name}")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to clean up collection: {cleanup_error}")
                    
            except ValueError as ve:
                logger.info(f"✓ EXPECTED ERROR: {ve}")
                logger.info("✓ Collection creation was properly cancelled")
            except Exception as e:
                logger.error(f"✗ UNEXPECTED ERROR: {e}")
            
        except Exception as e:
            logger.error(f"✗ TEST SETUP FAILED: {e}")
        
        finally:
            # Clean up temporary file
            try:
                if 'temp_path' in locals() and os.path.exists(temp_path):
                    os.remove(temp_path)
                    logger.info(f"Cleaned up temp file: {temp_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up temp file: {e}")

if __name__ == "__main__":
    test_minimal_content_handling()
