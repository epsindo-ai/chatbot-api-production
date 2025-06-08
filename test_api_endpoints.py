#!/usr/bin/env python3
"""
Test script for the new configurable prompt API endpoints
"""

import sys
import os
sys.path.append('/app')

import asyncio
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

def test_user_collection_prompt_endpoints():
    """Test the user collection RAG prompt endpoints"""
    print("=== Testing User Collection RAG Prompt Endpoints ===")
    
    db = next(get_db())
    mock_admin = MockAdminUser()
    
    try:
        # Test setting user collection prompt
        test_prompt = "This is a test user collection RAG prompt for testing endpoints."
        result = set_user_collection_rag_prompt(
            prompt=test_prompt,
            db=db,
            current_user=mock_admin
        )
        print(f"✓ Set user collection prompt: {result['key']}")
        assert result["success"] == True
        assert result["value"] == test_prompt
        
        # Test getting user collection prompt
        result = get_user_collection_rag_prompt(
            db=db,
            current_user=mock_admin
        )
        print(f"✓ Retrieved user collection prompt: {result['prompt'][:50]}...")
        assert result["prompt"] == test_prompt
        
        print("✓ User collection RAG prompt endpoints work correctly")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False
    finally:
        db.close()
    
    return True

def test_regular_chat_prompt_endpoints():
    """Test the regular chat prompt endpoints"""
    print("\n=== Testing Regular Chat Prompt Endpoints ===")
    
    db = next(get_db())
    mock_admin = MockAdminUser()
    
    try:
        # Test setting regular chat prompt
        test_prompt = "This is a test regular chat prompt for testing endpoints."
        result = set_regular_chat_prompt(
            prompt=test_prompt,
            db=db,
            current_user=mock_admin
        )
        print(f"✓ Set regular chat prompt: {result['key']}")
        assert result["success"] == True
        assert result["value"] == test_prompt
        
        # Test getting regular chat prompt
        result = get_regular_chat_prompt(
            db=db,
            current_user=mock_admin
        )
        print(f"✓ Retrieved regular chat prompt: {result['prompt'][:50]}...")
        assert result["prompt"] == test_prompt
        
        print("✓ Regular chat prompt endpoints work correctly")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False
    finally:
        db.close()
    
    return True

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
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()
    
    return True

def main():
    """Run all endpoint tests"""
    print("Starting API Endpoints Test Suite")
    print("=" * 50)
    
    tests = [
        ("User Collection Prompt Endpoints", test_user_collection_prompt_endpoints),
        ("Regular Chat Prompt Endpoints", test_regular_chat_prompt_endpoints),
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
        print("🎉 All API endpoint tests passed!")
    else:
        print("⚠️  Some API endpoint tests failed.")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
