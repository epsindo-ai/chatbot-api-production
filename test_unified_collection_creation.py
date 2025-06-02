#!/usr/bin/env python3
"""
Test script for the new unified collection creation approach.
This demonstrates how admins can now create collections and process files in one operation.
"""

import requests
import json
import sys
import os

# Configuration
BASE_URL = "http://localhost:8000"
USERNAME = "admin"
PASSWORD = "admin"

def login():
    """Login and get access token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "username": USERNAME,
        "password": PASSWORD
    })
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"Login failed: {response.text}")
        return None

def test_unified_collection_creation(token):
    """Test the new unified collection creation endpoints"""
    headers = {"Authorization": f"Bearer {token}"}
    
    print("=== Testing Unified Collection Creation ===\n")
    
    # 1. Test creating collection with existing files
    print("1. Testing collection creation with existing file IDs...")
    
    # First, let's get available files
    response = requests.get(f"{BASE_URL}/api/admin/files/", headers=headers)
    if response.status_code == 200:
        files = response.json()
        if files:
            file_ids = [str(f["id"]) for f in files[:2]]  # Take first 2 files
            print(f"   Using file IDs: {file_ids}")
            
            # Create collection with files
            collection_data = {
                "name": "test_unified_collection",
                "description": "Test collection created with unified approach",
                "file_ids": file_ids,
                "is_global_default": False
            }
            
            response = requests.post(
                f"{BASE_URL}/api/admin/collections/with-files",
                data=collection_data,
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ Collection created successfully!")
                print(f"   Collection ID: {result['collection']['id']}")
                print(f"   Collection Name: {result['collection']['name']}")
                print(f"   Files processed: {result['processing_summary']['processed_successfully']}")
                print(f"   Total chunks: {result['processing_summary']['total_chunks_created']}")
                print(f"   Milvus collection: {result['milvus_collection_name']}")
            else:
                print(f"   ❌ Failed to create collection: {response.text}")
        else:
            print("   ⚠️  No files available for testing")
    else:
        print(f"   ❌ Failed to get files: {response.text}")
    
    # 2. Test creating collection with file upload
    print("\n2. Testing collection creation with file upload...")
    
    # Create a test file
    test_content = """
    This is a test document for the unified collection creation.
    
    The new approach allows admins to:
    1. Create collections and process files in one operation
    2. Upload files and create collections simultaneously
    3. Avoid the inefficient two-step process
    
    Benefits:
    - Atomic operations
    - Better error handling
    - Immediate feedback on processing status
    - Reduced API calls
    """
    
    # Save test file
    test_file_path = "test_unified_document.txt"
    with open(test_file_path, "w") as f:
        f.write(test_content)
    
    try:
        # Upload and create collection
        with open(test_file_path, "rb") as f:
            files = {"files": ("test_document.txt", f, "text/plain")}
            data = {
                "name": "test_upload_collection",
                "description": "Test collection with uploaded files",
                "is_global_default": False
            }
            
            response = requests.post(
                f"{BASE_URL}/api/admin/collections/upload-and-create",
                files=files,
                data=data,
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ Collection created with upload!")
                print(f"   Collection ID: {result['collection']['id']}")
                print(f"   Collection Name: {result['collection']['name']}")
                print(f"   Files processed: {result['processing_summary']['processed_successfully']}")
                print(f"   Total chunks: {result['processing_summary']['total_chunks_created']}")
                print(f"   Milvus collection: {result['milvus_collection_name']}")
            else:
                print(f"   ❌ Failed to create collection with upload: {response.text}")
    
    finally:
        # Clean up test file
        if os.path.exists(test_file_path):
            os.remove(test_file_path)
    
    # 3. Compare with old approach
    print("\n3. Comparing with old approach...")
    print("   Old approach:")
    print("   1. POST /api/admin/collections/ (create empty collection)")
    print("   2. POST /api/admin/files/upload (upload files)")
    print("   3. POST /api/admin/collections/{id}/add-file/{file_id} (add files)")
    print("   4. POST /api/admin/collections/{id}/process (process files)")
    print("   = 4+ API calls, potential for partial failures")
    
    print("\n   New approach:")
    print("   1. POST /api/admin/collections/with-files (create + process existing files)")
    print("   OR")
    print("   1. POST /api/admin/collections/upload-and-create (upload + create + process)")
    print("   = 1 API call, atomic operation, immediate feedback")
    
    print("\n=== Unified Collection Creation Test Complete! ===")
    return True

def test_error_handling(token):
    """Test error handling in unified approach"""
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n=== Testing Error Handling ===\n")
    
    # 1. Test duplicate collection name
    print("1. Testing duplicate collection name...")
    collection_data = {
        "name": "test_unified_collection",  # Should already exist from previous test
        "description": "Duplicate test",
        "file_ids": ["1"],
        "is_global_default": False
    }
    
    response = requests.post(
        f"{BASE_URL}/api/admin/collections/with-files",
        data=collection_data,
        headers=headers
    )
    
    if response.status_code == 400:
        print("   ✅ Correctly rejected duplicate collection name")
    else:
        print(f"   ⚠️  Unexpected response: {response.status_code}")
    
    # 2. Test invalid file IDs
    print("\n2. Testing invalid file IDs...")
    collection_data = {
        "name": "test_invalid_files",
        "description": "Test with invalid files",
        "file_ids": ["99999"],  # Non-existent file ID
        "is_global_default": False
    }
    
    response = requests.post(
        f"{BASE_URL}/api/admin/collections/with-files",
        data=collection_data,
        headers=headers
    )
    
    if response.status_code == 404:
        print("   ✅ Correctly rejected invalid file ID")
    else:
        print(f"   ⚠️  Unexpected response: {response.status_code}")
    
    print("\n=== Error Handling Test Complete! ===")

def main():
    """Main test function"""
    print("Starting Unified Collection Creation Tests...\n")
    
    # Login
    token = login()
    if not token:
        print("Failed to login. Exiting.")
        sys.exit(1)
    
    print(f"Successfully logged in!\n")
    
    # Run tests
    try:
        success = test_unified_collection_creation(token)
        if success:
            test_error_handling(token)
            print("\n🎉 All tests completed!")
        else:
            print("\n❌ Some tests failed!")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 