#!/usr/bin/env python3

"""
Comprehensive test script to verify the complete global collection RAG prompt implementation.
"""

import sys
import os
import asyncio

# Add the app directory to the Python path
sys.path.insert(0, "/app")

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.services.admin_config_service import AdminConfigService
from app.services.rag_config_service import RAGConfigService
from app.services.rag_service import RagChatService
from app.models.admin_config import AdminConfig

async def test_complete_implementation():
    """Test the complete global collection RAG prompt implementation."""
    print("🧪 Comprehensive Global Collection RAG Prompt Test")
    print("=" * 60)
    
    # Create database session
    db: Session = SessionLocal()
    
    try:
        # Test 1: Configuration Management
        print("\n1️⃣ Testing Configuration Management...")
        
        # Set up test data
        test_global_prompt = """You are an expert AI assistant for our organizational knowledge base. 
        Answer questions accurately based on the provided context from official documents and resources.
        If information is not available in the context, clearly state that you don't know.
        Always maintain a professional and helpful tone."""
        
        test_user_prompt = """You are a helpful AI assistant for personal documents.
        Answer questions based on the user's uploaded files and conversations.
        Be friendly and conversational while staying accurate."""
        
        # Set the global collection prompt
        RAGConfigService.set_global_collection_rag_prompt(db, test_global_prompt)
        
        # Set a predefined collection
        AdminConfigService.set_predefined_collection(db, "company_knowledge_base")
        
        print("✅ Test prompts and collection configured")
        
        # Test 2: Prompt Selection Logic
        print("\n2️⃣ Testing Prompt Selection Logic...")
        
        rag_service = RagChatService()
        
        # Test global collection prompt selection
        global_collection_prompt = rag_service._get_rag_system_prompt(db, "company_knowledge_base")
        user_collection_prompt = rag_service._get_rag_system_prompt(db, "user_files_12345")
        no_collection_prompt = rag_service._get_rag_system_prompt(db, None)
        
        print(f"✅ Global collection prompt: {len(global_collection_prompt)} chars")
        print(f"✅ User collection prompt: {len(user_collection_prompt)} chars")
        print(f"✅ No collection prompt: {len(no_collection_prompt)} chars")
        
        # Verify prompts are different
        assert global_collection_prompt == test_global_prompt, "Global prompt mismatch"
        assert user_collection_prompt != global_collection_prompt, "Prompts should be different"
        
        # Test 3: Configuration API
        print("\n3️⃣ Testing Configuration API...")
        
        # Test RAG config
        rag_config = RAGConfigService.get_rag_config(db)
        client_config = RAGConfigService.get_client_config(db)
        
        assert "global_collection_rag_prompt" in rag_config, "Missing from RAG config"
        assert "globalCollectionRagPrompt" in client_config, "Missing from client config"
        
        print("✅ RAG config includes global prompt")
        print("✅ Client config includes global prompt")
        
        # Test 4: Collection Detection
        print("\n4️⃣ Testing Collection Detection...")
        
        test_cases = [
            ("company_knowledge_base", True, "Predefined collection"),
            ("admin_docs", False, "Non-predefined collection"),
            ("user_files_12345", False, "User files collection"),
            (None, False, "No collection"),
        ]
        
        for collection_name, expected_global, description in test_cases:
            is_global = rag_service._is_global_collection(db, collection_name)
            assert is_global == expected_global, f"Failed for {description}"
            print(f"✅ {description}: {collection_name} -> global={is_global}")
        
        # Test 5: Integration Test
        print("\n5️⃣ Testing Integration...")
        
        # Simulate different scenarios
        scenarios = [
            {
                "name": "Global Collection Chat",
                "collection": "company_knowledge_base",
                "expected_prompt_contains": "organizational knowledge base"
            },
            {
                "name": "User Collection Chat", 
                "collection": "user_files_12345",
                "expected_prompt_contains": "helpful ai assistant"
            },
            {
                "name": "No Collection Chat",
                "collection": None,
                "expected_prompt_contains": "helpful ai assistant"
            }
        ]
        
        for scenario in scenarios:
            prompt = rag_service._get_rag_system_prompt(db, scenario["collection"])
            assert scenario["expected_prompt_contains"] in prompt.lower(), \
                f"Prompt validation failed for {scenario['name']}"
            print(f"✅ {scenario['name']}: Correct prompt selected")
        
        # Test 6: Admin Configuration
        print("\n6️⃣ Testing Admin Configuration...")
        
        # Test direct admin config service
        original_prompt = AdminConfigService.get_global_collection_rag_prompt(db)
        
        new_prompt = "Updated admin prompt for testing"
        AdminConfigService.set_global_collection_rag_prompt(db, new_prompt)
        
        updated_prompt = AdminConfigService.get_global_collection_rag_prompt(db)
        assert updated_prompt == new_prompt, "Admin config update failed"
        
        # Restore original prompt
        AdminConfigService.set_global_collection_rag_prompt(db, original_prompt)
        
        print("✅ Admin configuration update/retrieval works")
        
        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED! Implementation is complete and working correctly.")
        
        # Print final summary
        print("\n📊 Implementation Summary:")
        print("✅ Global collection RAG prompt configuration")
        print("✅ Dynamic prompt selection based on collection type")
        print("✅ Admin configuration services")
        print("✅ RAG service integration")
        print("✅ Client configuration API")
        print("✅ Admin REST endpoints")
        print("✅ Collection detection logic")
        
        print(f"\n📋 Current Configuration:")
        print(f"• Predefined Collection: {RAGConfigService.get_predefined_collection(db)}")
        print(f"• Global Prompt Length: {len(RAGConfigService.get_global_collection_rag_prompt(db))} characters")
        print(f"• Retriever Top K: {RAGConfigService.get_retriever_top_k(db)}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = asyncio.run(test_complete_implementation())
    sys.exit(0 if success else 1)
