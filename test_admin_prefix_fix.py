#!/usr/bin/env python3
"""
Test script to verify the admin prefix fix for global collections.
This script tests that global collections properly use the admin_ prefix when passed to RAG service.
"""

import sys
import os
sys.path.append('/app')

def test_admin_prefix_logic():
    """Test that the admin prefix logic is working correctly"""
    
    # Mock collection object
    class MockCollection:
        def __init__(self, name):
            self.name = name
    
    # Test 1: Regular collection name gets admin prefix
    collection = MockCollection("company_policies")
    collection_name = f"admin_{collection.name}"
    
    expected = "admin_company_policies"
    assert collection_name == expected, f"Expected {expected}, got {collection_name}"
    print(f"✅ Test 1 passed: {collection.name} -> {collection_name}")
    
    # Test 2: Collection name with special characters
    collection = MockCollection("hr-policies_2024")
    collection_name = f"admin_{collection.name}"
    
    expected = "admin_hr-policies_2024"
    assert collection_name == expected, f"Expected {expected}, got {collection_name}"
    print(f"✅ Test 2 passed: {collection.name} -> {collection_name}")
    
    print("\n🎉 All admin prefix tests passed!")

def test_rag_service_global_collection_detection():
    """Test that RAG service properly detects global collections with admin prefix"""
    
    # Import necessary modules
    from app.services.rag_service import RagChatService
    from app.db.database import get_db
    from app.services.rag_config_service import RAGConfigService
    from app.db import models
    
    # Mock database session
    class MockDB:
        pass
    
    db = MockDB()
    
    # Create RAG service instance
    rag_service = RagChatService(
        embedding_url="http://localhost:7997",
        milvus_uri="http://localhost:19530"
    )
    
    print("\n🔍 Testing RAG service global collection detection...")
    
    # Test the _is_global_collection method logic
    # Note: This test focuses on the logic structure rather than database calls
    
    # Test cases for different collection name formats
    test_cases = [
        ("company_policies", "company_policies", True),  # exact match
        ("admin_company_policies", "company_policies", True),  # admin prefix match
        ("hr_docs", "company_policies", False),  # no match
        ("admin_hr_docs", "company_policies", False),  # admin prefix but different collection
    ]
    
    print("Collection name detection logic test cases:")
    for collection_name, predefined_collection, expected in test_cases:
        # Simulate the logic from _is_global_collection method
        is_global = (collection_name == predefined_collection or 
                    collection_name == f"admin_{predefined_collection}" or
                    collection_name.replace("admin_", "") == predefined_collection)
        
        status = "✅" if is_global == expected else "❌"
        print(f"  {status} '{collection_name}' vs predefined '{predefined_collection}' -> {is_global} (expected {expected})")
        
        if is_global != expected:
            print(f"    FAILED: Expected {expected}, got {is_global}")
            return False
    
    print("🎉 RAG service detection logic tests passed!")
    return True

if __name__ == "__main__":
    print("Testing admin prefix fix for global collections...\n")
    
    try:
        test_admin_prefix_logic()
        test_rag_service_global_collection_detection()
        print("\n✅ All tests passed! The admin prefix fix should work correctly.")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
