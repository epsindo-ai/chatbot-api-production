#!/usr/bin/env python3
"""Test different file formats with minimal content"""

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
logger = logging.getLogger("test_formats")

def test_format_processing():
    """Test processing of different file formats"""
    logger.info("=== TESTING DIFFERENT FILE FORMAT PROCESSING ===")
    
    # Test files with content that should work
    test_cases = [
        ("# Sample Markdown\n\nThis is a sample markdown document with some content to test.", "sample.md", "text/markdown"),
        ("<html><body><h1>HTML Test</h1><p>This is a sample HTML document with some content.</p></body></html>", "sample.html", "text/html"),
        ("col1,col2,col3\nvalue1,value2,value3\ndata1,data2,data3", "sample.csv", "text/csv"),
        ("= AsciiDoc Test\n\nThis is a sample AsciiDoc document with some content.", "sample.adoc", "text/asciidoc")
    ]
    
    ingestion_service = DocumentIngestionService()
    
    for content, filename, expected_mime in test_cases:
        logger.info(f"\n--- Testing: {filename} ({expected_mime}) ---")
        
        # Test MIME type detection
        detected_mime = ingestion_service._guess_mime_type(filename)
        logger.info(f"MIME type detection: expected={expected_mime}, detected={detected_mime}")
        
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix=f'_{filename}', delete=False, encoding='utf-8') as temp_file:
                temp_file.write(content)
                temp_path = temp_file.name
            
            logger.info(f"Created test file: {temp_path} ({len(content)} chars)")
            
            # Try to process the file
            try:
                collection_name = f"test_format_{filename.split('.')[0]}"
                result = ingestion_service.ingest_file(temp_path, collection_name)
                logger.info(f"✓ SUCCESS: {filename} processed, {result} documents created")
                
                # Clean up collection
                try:
                    ingestion_service.delete_collection(collection_name)
                    logger.info(f"✓ Cleaned up collection: {collection_name}")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to clean up collection: {cleanup_error}")
                    
            except Exception as e:
                logger.error(f"✗ FAILED: {filename} - {e}")
            
        except Exception as e:
            logger.error(f"✗ TEST SETUP FAILED for {filename}: {e}")
        
        finally:
            # Clean up temporary file
            try:
                if 'temp_path' in locals() and os.path.exists(temp_path):
                    os.remove(temp_path)
                    logger.info(f"Cleaned up temp file: {temp_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up temp file: {e}")

if __name__ == "__main__":
    test_format_processing()
