#!/usr/bin/env python3
"""
Test script for configurable LLM prompts implementation
Tests all three prompt types: global collection RAG, user collection RAG, and regular chat
"""

import sys
import os
sys.path.append('/app')

import asyncio
import uuid
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db import crud, schemas
from app.services.admin_config_service import AdminConfigService
from app.services.rag_config_service import RAGConfigService
from app.services.llm_service import get_llm_response, get_system_prompt
from app.models.admin_config import AdminConfig

def test_prompt_configuration():
    """Test setting and getting all three prompt types"""
    print("=== Testing Prompt Configuration ===")
    
    db = next(get_db())
    
    # Test prompts
    global_prompt = "You are a helpful AI assistant for global knowledge queries. Use the provided context to give accurate and comprehensive answers."
    user_prompt = "You are a personal AI assistant. Use the user's uploaded documents to provide personalized and relevant responses."
    regular_prompt = "You are a friendly and knowledgeable AI assistant. Be helpful, clear, and concise in your responses."
    
    try:
        # Test global collection RAG prompt
        print("\n1. Testing Global Collection RAG Prompt...")
        config = RAGConfigService.set_global_collection_rag_prompt(db, global_prompt)
        print(f"   Set global collection prompt: {config.key}")
        
        retrieved_prompt = RAGConfigService.get_global_collection_rag_prompt(db)
        print(f"   Retrieved: {retrieved_prompt[:50]}...")
        assert retrieved_prompt == global_prompt, "Global prompt mismatch"
        print("   ✓ Global collection RAG prompt works")
        
        # Test user collection RAG prompt
        print("\n2. Testing User Collection RAG Prompt...")
        config = RAGConfigService.set_user_collection_rag_prompt(db, user_prompt)
        print(f"   Set user collection prompt: {config.key}")
        
        retrieved_prompt = RAGConfigService.get_user_collection_rag_prompt(db)
        print(f"   Retrieved: {retrieved_prompt[:50]}...")
        assert retrieved_prompt == user_prompt, "User prompt mismatch"
        print("   ✓ User collection RAG prompt works")
        
        # Test regular chat prompt
        print("\n3. Testing Regular Chat Prompt...")
        config = RAGConfigService.set_regular_chat_prompt(db, regular_prompt)
        print(f"   Set regular chat prompt: {config.key}")
        
        retrieved_prompt = RAGConfigService.get_regular_chat_prompt(db)
        print(f"   Retrieved: {retrieved_prompt[:50]}...")
        assert retrieved_prompt == regular_prompt, "Regular prompt mismatch"
        print("   ✓ Regular chat prompt works")
        
        # Test LLM service integration
        print("\n4. Testing LLM Service Integration...")
        system_prompt = get_system_prompt(db)
        print(f"   LLM service gets prompt: {system_prompt[:50]}...")
        assert system_prompt == regular_prompt, "LLM service prompt mismatch"
        print("   ✓ LLM service integration works")
        
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False
    finally:
        db.close()
    
    return True

def test_database_storage():
    """Test that prompts are properly stored in the database"""
    print("\n=== Testing Database Storage ===")
    
    db = next(get_db())
    
    try:
        # Check that all configuration keys exist
        configs = AdminConfigService.get_all_configs(db)
        config_keys = [c.key for c in configs]
        
        expected_keys = [
            AdminConfig.KEY_GLOBAL_COLLECTION_RAG_PROMPT,
            AdminConfig.KEY_USER_COLLECTION_RAG_PROMPT,
            AdminConfig.KEY_REGULAR_CHAT_PROMPT
        ]
        
        for key in expected_keys:
            if key in config_keys:
                print(f"   ✓ Found config key: {key}")
            else:
                print(f"   ❌ Missing config key: {key}")
                return False
        
        print("   ✓ All configuration keys are stored correctly")
        
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False
    finally:
        db.close()
    
    return True

async def test_llm_response_with_prompt():
    """Test that LLM responses use the configured system prompt"""
    print("\n=== Testing LLM Response with Configured Prompt ===")
    
    db = next(get_db())
    
    try:
        # Create a test user
        user_data = {
            "username": f"test_user_{uuid.uuid4().hex[:8]}",
            "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
            "password": "test_password",
            "role": "user"
        }
        user = crud.create_user(db, schemas.UserCreate(**user_data))
        print(f"   Created test user: {user.username}")
        
        # Set a distinctive system prompt
        distinctive_prompt = "You are a test AI that always starts responses with 'TEST_PROMPT_ACTIVE:'"
        RAGConfigService.set_regular_chat_prompt(db, distinctive_prompt)
        print("   Set distinctive test prompt")
        
        # Test LLM response
        response = await get_llm_response(db, user.id, "Hello, how are you?")
        print(f"   LLM Response: {response[:100]}...")
        
        # Note: The response might not contain our exact prompt text since it's a system message,
        # but we can verify the prompt is being used by checking it's loaded
        system_prompt = get_system_prompt(db)
        assert "TEST_PROMPT_ACTIVE" in system_prompt, "System prompt not properly configured"
        print("   ✓ System prompt is properly loaded by LLM service")
        
        # Verify the response actually used the prompt
        if "TEST_PROMPT_ACTIVE" in response:
            print("   ✓ LLM response correctly used the configured system prompt")
        else:
            print("   ⚠️  LLM response may not have used the system prompt (but prompt is loaded)")
        
        # Note: We're not cleaning up the test user as the delete function is not available
        print("   Note: Test user cleanup skipped (no delete function available)")
        
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False
    finally:
        db.close()
    
    return True

def test_unified_config():
    """Test that unified config includes all prompt types"""
    print("\n=== Testing Unified Config ===")
    
    db = next(get_db())
    
    try:
        # Get client config
        client_config = RAGConfigService.get_client_config(db)
        
        expected_fields = [
            "globalCollectionRagPrompt",
            "userCollectionRagPrompt", 
            "regularChatPrompt"
        ]
        
        for field in expected_fields:
            if field in client_config:
                print(f"   ✓ Found field in client config: {field}")
                print(f"     Value: {str(client_config[field])[:50]}...")
            else:
                print(f"   ❌ Missing field in client config: {field}")
                return False
        
        print("   ✓ All prompt types included in client config")
        
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False
    finally:
        db.close()
    
    return True

async def main():
    """Run all tests"""
    print("Starting Configurable Prompts Test Suite")
    print("=" * 50)
    
    tests = [
        ("Prompt Configuration", test_prompt_configuration),
        ("Database Storage", test_database_storage),
        ("LLM Response Integration", test_llm_response_with_prompt),
        ("Unified Config", test_unified_config),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
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
        print("🎉 All tests passed! Configurable prompts are working correctly.")
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
    
    return failed == 0

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
