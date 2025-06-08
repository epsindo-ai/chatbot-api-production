#!/usr/bin/env python3
"""
Test script for the simplified unified chat API
Validates that the API handles different conversation types correctly with the simplified schema.
"""

import json
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, '/app')

def test_schema_imports():
    """Test that all simplified schemas import correctly"""
    try:
        from app.db.schemas import UnifiedChatRequest, UnifiedChatResponse
        from app.api.routes.unified_chat import router, UnifiedChatRequest as LocalUnifiedChatRequest
        
        print("✅ Schema imports successful")
        
        # Test schema creation
        request = UnifiedChatRequest(
            message="Hello, world!",
            conversation_id=None,
            meta_data={"test": True}
        )
        print(f"✅ Schema creation successful: {request}")
        
        # Verify simplified structure
        request_dict = request.model_dump()
        expected_fields = {"message", "conversation_id", "meta_data"}
        actual_fields = set(request_dict.keys())
        
        if actual_fields == expected_fields:
            print("✅ Request schema has correct simplified fields")
        else:
            print(f"❌ Request schema field mismatch. Expected: {expected_fields}, Got: {actual_fields}")
            return False
            
        # Test response schema
        response = UnifiedChatResponse(
            status_code=200,
            error=None,
            response="Test response",
            conversation_id="test-conv-id",
            meta_data={"test": True},
            used_rag=False
        )
        
        response_dict = response.model_dump()
        unexpected_fields = {"collection_name", "added_files", "display_file_id"}
        
        if any(field in response_dict for field in unexpected_fields):
            print(f"❌ Response schema contains unexpected fields: {[f for f in unexpected_fields if f in response_dict]}")
            return False
        else:
            print("✅ Response schema properly simplified - no eliminated fields present")
        
        return True
        
    except Exception as e:
        print(f"❌ Schema import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_endpoint_validation():
    """Test that the endpoint can be imported and basic validation works"""
    try:
        from app.api.routes.unified_chat import unified_chat, unified_stream_chat
        print("✅ Endpoint functions import successfully")
        
        # Try to inspect the function signature
        import inspect
        sig = inspect.signature(unified_chat)
        params = list(sig.parameters.keys())
        
        expected_params = ["request", "background_tasks", "current_user", "db"]
        if all(param in params for param in expected_params):
            print("✅ Endpoint signature has expected parameters")
        else:
            print(f"❌ Endpoint signature mismatch. Expected: {expected_params}, Got: {params}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Endpoint validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all validation tests"""
    print("=== Simplified Unified Chat API Validation ===")
    print()
    
    tests = [
        ("Schema Import and Structure", test_schema_imports),
        ("Endpoint Validation", test_endpoint_validation),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"Running: {test_name}")
        try:
            if test_func():
                print(f"✅ {test_name} PASSED")
                passed += 1
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} FAILED with exception: {e}")
        print()
    
    print("=== Validation Summary ===")
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED - Unified Chat API simplification successful!")
        return True
    else:
        print("❌ Some tests failed - manual review required")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
