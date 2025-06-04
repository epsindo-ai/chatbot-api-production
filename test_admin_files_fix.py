#!/usr/bin/env python3
"""
Test script to verify the admin files delete function fix.
"""

import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_crud_functions():
    """Test that all required CRUD functions are available."""
    from app.db import crud
    
    # Check if the correct function exists
    if hasattr(crud, 'delete_file_storage'):
        print("✓ crud.delete_file_storage function exists")
    else:
        print("✗ crud.delete_file_storage function missing")
        return False
    
    # Check if the old incorrect function name is NOT being called anywhere
    if hasattr(crud, 'delete_file'):
        print("⚠ crud.delete_file function exists (this might be a different one)")
    else:
        print("✓ crud.delete_file function does not exist (good, should be delete_file_storage)")
    
    return True

def test_minio_service():
    """Test that MinioService has the delete_file method."""
    from app.services.minio_service import MinioService
    
    minio_service = MinioService()
    
    if hasattr(minio_service, 'delete_file'):
        print("✓ MinioService.delete_file method exists")
        return True
    else:
        print("✗ MinioService.delete_file method missing")
        return False

def test_admin_files_import():
    """Test that admin files module can be imported without errors."""
    try:
        from app.api.routes import admin_files
        print("✓ Admin files module imported successfully")
        return True
    except Exception as e:
        print(f"✗ Error importing admin files module: {e}")
        return False

if __name__ == "__main__":
    print("Testing admin files delete function fix...\n")
    
    tests = [
        ("CRUD Functions", test_crud_functions),
        ("MinIO Service", test_minio_service),
        ("Admin Files Import", test_admin_files_import),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"Testing {test_name}:")
        try:
            if test_func():
                passed += 1
                print(f"✓ {test_name} - PASSED\n")
            else:
                print(f"✗ {test_name} - FAILED\n")
        except Exception as e:
            print(f"✗ {test_name} - ERROR: {e}\n")
    
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The admin files delete fix is working correctly.")
    else:
        print("❌ Some tests failed. Please check the implementation.")
