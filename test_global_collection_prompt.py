#!/usr/bin/env python3

"""
Test script to verify the global collection RAG prompt implementation.
"""

import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, "/app")

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.services.admin_config_service import AdminConfigService
from app.services.rag_config_service import RAGConfigService
from app.services.rag_service import RagChatService
from app.models.admin_config import AdminConfig

def test_global_collection_prompt():
    """Test the global collection RAG prompt functionality."""
    print("Testing Global Collection RAG Prompt Implementation")
    print("=" * 50)
    
    # Create database session
    db: Session = SessionLocal()
    
    try:
        # Test 1: Test default prompt retrieval
        print("\n1. Testing default prompt retrieval...")
        default_prompt = RAGConfigService.get_global_collection_rag_prompt(db)
        print(f"Default prompt: {default_prompt[:100]}...")
        
        # Test 2: Test setting a custom prompt
        print("\n2. Testing custom prompt setting...")
        custom_prompt = """
You are an AI assistant for a global knowledge base. Answer questions based on the provided context from administrative collections.
If the information is not in the context, say you don't know. Be professional and helpful.
"""
        config = RAGConfigService.set_global_collection_rag_prompt(db, custom_prompt)
        print(f"Set custom prompt: {config.key} = {config.value[:50]}...")
        
        # Test 3: Test prompt retrieval after setting
        print("\n3. Testing prompt retrieval after setting...")
        retrieved_prompt = RAGConfigService.get_global_collection_rag_prompt(db)
        print(f"Retrieved prompt: {retrieved_prompt[:100]}...")
        assert retrieved_prompt == custom_prompt, "Prompt retrieval failed"
        
        # Test 4: Test RAG service prompt selection
        print("\n4. Testing RAG service prompt selection...")
        rag_service = RagChatService()
        
        # Test global collection detection
        print("Testing global collection detection...")
        is_global = rag_service._is_global_collection(db, "test_global_collection")
        print(f"Collection 'test_global_collection' is global: {is_global}")
        
        # Test prompt selection for global collection
        print("Testing prompt selection for global collection...")
        # First set a predefined collection to test with
        AdminConfigService.set_predefined_collection(db, "test_global_collection")
        
        global_prompt = rag_service._get_rag_system_prompt(db, "test_global_collection")
        print(f"Global collection prompt: {global_prompt[:100]}...")
        
        # Test prompt selection for user collection
        print("Testing prompt selection for user collection...")
        user_prompt = rag_service._get_rag_system_prompt(db, "user_collection_12345")
        print(f"User collection prompt: {user_prompt[:100]}...")
        
        # Test 5: Test client config includes prompt
        print("\n5. Testing client config includes prompt...")
        client_config = RAGConfigService.get_client_config(db)
        print(f"Client config keys: {list(client_config.keys())}")
        assert "globalCollectionRagPrompt" in client_config, "Global prompt not in client config"
        print(f"Global prompt in client config: {client_config['globalCollectionRagPrompt'][:50]}...")
        
        print("\n" + "=" * 50)
        print("✅ All tests passed! Global collection RAG prompt implementation is working correctly.")
        
        # Print configuration summary
        print("\n📋 Configuration Summary:")
        print(f"• Predefined Collection: {RAGConfigService.get_predefined_collection(db)}")
        print(f"• Global Collection Prompt: {custom_prompt[:50]}...")
        print(f"• Default Prompt Length: {len(default_prompt)} characters")
        print(f"• Custom Prompt Length: {len(custom_prompt)} characters")
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()
    
    return True

if __name__ == "__main__":
    success = test_global_collection_prompt()
    sys.exit(0 if success else 1)
