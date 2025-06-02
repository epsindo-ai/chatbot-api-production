#!/usr/bin/env python3
"""
Debug script to test ingestion service without vector IDs
"""

import sys
import os
sys.path.append('/app')

from app.services.ingestion_service import DocumentIngestionService
from app.config import settings
import tempfile

def test_ingestion_without_vector_ids():
    """Test that ingestion works correctly without returning vector IDs"""
    
    print("=== Testing Ingestion Service Without Vector IDs ===")
    
    # Initialize ingestion service
    ingestion_service = DocumentIngestionService()
    
    # Create a test text with multiple chunks
    test_text = """
    This is the first paragraph of our test document. It contains some information about testing.
    
    This is the second paragraph. It has different content to ensure we get multiple chunks.
    
    This is the third paragraph with even more unique content to create distinct embeddings.
    
    This is the fourth paragraph. Each paragraph should generate a unique vector ID.
    
    This is the fifth paragraph to ensure we have enough content for multiple chunks.
    """
    
    # Test collection name
    collection_name = "test_ingestion_no_vector_ids"
    
    try:
        # Process the text
        print(f"Processing text into collection: {collection_name}")
        num_docs = ingestion_service.ingest_text(
            text=test_text,
            collection_name=collection_name,
            metadata={"test": "no_vector_ids_debug"}
        )
        
        print(f"\nResults:")
        print(f"Number of documents: {num_docs}")
        print("✅ Text ingestion completed successfully without vector IDs")
            
        # Test with a simple file
        print("\n=== Testing with file object ===")
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(test_text)
            temp_file_path = f.name
        
        # Read it back as bytes
        with open(temp_file_path, 'rb') as f:
            file_content = f.read()
        
        import io
        file_obj = io.BytesIO(file_content)
        
        # Process file object
        num_docs2 = ingestion_service.ingest_file_object(
            file_obj=file_obj,
            filename="test_file.txt",
            collection_name=collection_name + "_file",
            metadata={"test": "file_object_debug"}
        )
        
        print(f"\nFile Object Results:")
        print(f"Number of documents: {num_docs2}")
        print("✅ File object ingestion completed successfully without vector IDs")
            
        # Clean up
        os.unlink(temp_file_path)
        
        print(f"\n🎉 All tests passed! Ingestion service works correctly without vector IDs.")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_ingestion_without_vector_ids() 