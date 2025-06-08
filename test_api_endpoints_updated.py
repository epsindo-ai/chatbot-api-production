#!/usr/bin/env python3
"""
Test script for the configurable prompt API endpoints using unified config approach
"""

import sys
import os
sys.path.append('/app')

import json
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.routes.admin import (
    get_unified_config,
    update_unified_config
)
from app.services.rag_config_service import RAGConfigService
from app.models.user import User, UserRole

class MockAdminUser:
    """Mock admin user for testing"""
    def __init__(self):
        self.id = 1
        self.username = "admin"
        self.role = UserRole.ADMIN

def test_prompt_management_via_services():
    """Test prompt management via RAGConfigService (backend functionality)"""
    print("\n=== Testing Prompt Management via Services ===")
    
    db = next(get_db())
    
    try:
        # Test setting prompts via service
        test_prompts = {
            "global": "Test global collection RAG prompt for service testing.",
            "user": "Test user collection RAG prompt for service testing.",
            "regular": "Test regular chat prompt for service testing."
        }
        
        # Set via service
        RAGConfigService.set_global_collection_rag_prompt(db, test_prompts["global"])
        RAGConfigService.set_user_collection_rag_prompt(db, test_prompts["user"])
        RAGConfigService.set_regular_chat_prompt(db, test_prompts["regular"])
        print("✓ Set all prompts via service")
        
        # Get via service
        retrieved_global = RAGConfigService.get_global_collection_rag_prompt(db)
        retrieved_user = RAGConfigService.get_user_collection_rag_prompt(db)
        retrieved_regular = RAGConfigService.get_regular_chat_prompt(db)
        
        # Verify
        assert retrieved_global == test_prompts["global"], "Global prompt mismatch"
        assert retrieved_user == test_prompts["user"], "User prompt mismatch" 
        assert retrieved_regular == test_prompts["regular"], "Regular prompt mismatch"
        print("✓ Retrieved all prompts correctly via service")
        
        print("✓ Prompt management via services works correctly")
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False
    finally:
        db.close()

def test_unified_config_endpoints():
    """Test the unified config endpoints with all prompt types"""
    print("\n=== Testing Unified Config Endpoints ===")
    
    db = next(get_db())
    mock_admin = MockAdminUser()
    
    try:
        # Test getting unified config
        config = get_unified_config(
            db=db,
            current_user=mock_admin
        )
        print("✓ Retrieved unified config")
        
        # Check that all prompt types are included
        rag_config = config["rag"]
        expected_fields = [
            "globalCollectionRagPrompt",
            "userCollectionRagPrompt", 
            "regularChatPrompt"
        ]
        
        for field in expected_fields:
            if field in rag_config:
                print(f"✓ Found {field} in unified config")
                print(f"   Value: {str(rag_config[field])[:50]}...")
            else:
                print(f"❌ Missing {field} in unified config")
                return False
        
        # Test updating unified config with all prompt types
        test_prompts = {
            "globalCollectionRagPrompt": "Updated global collection prompt via unified config",
            "userCollectionRagPrompt": "Updated user collection prompt via unified config",
            "regularChatPrompt": "Updated regular chat prompt via unified config"
        }
        
        update_data = {
            "rag": test_prompts
        }
        
        result = update_unified_config(
            config=update_data,
            db=db,
            current_user=mock_admin
        )
        print("✓ Updated unified config with all prompt types")
        
        # Verify the updates were applied
        updated_rag = result["rag"]
        for field, expected_value in test_prompts.items():
            if field in updated_rag and updated_rag[field] == expected_value:
                print(f"✓ {field} updated correctly")
            else:
                print(f"❌ {field} not updated correctly")
                return False
        
        print("✓ Unified config endpoints work correctly with all prompt types")
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

def main():
    """Run all endpoint tests"""
    print("Starting Updated API Endpoints Test Suite")
    print("=" * 50)
    
    tests = [
        ("Prompt Management via Services", test_prompt_management_via_services),
        ("Unified Config Endpoints", test_unified_config_endpoints),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            
            if result:
                print(f"\n✓ {test_name} PASSED")
                passed += 1
            else:
                print(f"\n❌ {test_name} FAILED")
                failed += 1
        except Exception as e:
            print(f"\n❌ {test_name} FAILED with exception: {str(e)}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All updated API endpoint tests passed!")
    else:
        print("⚠️  Some API endpoint tests failed.")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
