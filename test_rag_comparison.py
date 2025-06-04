#!/usr/bin/env python3
"""
Test script to compare global collection RAG vs user file RAG implementation
"""

import asyncio
import sys
import os
import json
from sqlalchemy.orm import Session

# Add the app directory to Python path
sys.path.insert(0, '/app')

from app.db.database import SessionLocal
from app.services.rag_service import RagChatService
from app.db import crud
from app.config import settings
from app.services.rag_config_service import RAGConfigService


def print_section(title):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")


async def test_rag_implementations():
    """Test and compare RAG implementations."""
    print_section("RAG Implementation Comparison Test")
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Initialize RAG service
        rag_service = RagChatService(
            embedding_url=settings.REMOTE_EMBEDDER_URL,
            milvus_uri=settings.MILVUS_URI
        )
        
        print_section("1. Testing Global Collection Detection")
        
        # Test collection name detection
        test_collections = [
            "admin_global_knowledge",
            "global_knowledge", 
            "user_files_conversation_123",
            "conversation_456",
            "admin_test_collection"
        ]
        
        for collection_name in test_collections:
            is_global = rag_service._is_global_collection(db, collection_name)
            prompt = rag_service._get_rag_system_prompt(db, collection_name)
            print(f"Collection: {collection_name}")
            print(f"  Is Global: {is_global}")
            print(f"  Prompt Type: {'Global' if 'global' in prompt.lower() or 'knowledge base' in prompt.lower() else 'Default'}")
            print()
        
        print_section("2. Comparing Method Implementations")
        
        # Compare the two main RAG methods
        print("Method: get_streaming_rag_response (for global collections)")
        print("- Used for: Global/admin collections")
        print("- Flow: contextualize_question -> retrieve -> stream response")
        print("- Prompt: Dynamic based on collection type")
        print("- History: CustomMessageHistory")
        print()
        
        print("Method: get_streaming_conversation_rag_response (for user files)")
        print("- Used for: User files/conversation files")
        print("- Flow: direct retrieval -> stream response")
        print("- Prompt: Dynamic based on collection type")
        print("- History: Manual message formatting")
        print()
        
        print_section("3. Testing Vectorstore Access")
        
        # Test if we can access the global collection
        global_collections = rag_service.list_available_collections()
        print(f"Available collections: {global_collections}")
        
        # Check if admin_global_knowledge exists
        admin_global_exists = "admin_global_knowledge" in global_collections
        print(f"Admin global collection exists: {admin_global_exists}")
        
        if admin_global_exists:
            print("✅ Global collection is accessible")
            
            # Test retrieval from global collection
            try:
                retriever = rag_service.vectorstore_manager.get_retriever("admin_global_knowledge", top_k=3)
                print("✅ Can create retriever for global collection")
                
                # Test document retrieval
                test_query = "What is this knowledge base about?"
                docs = await retriever.ainvoke(test_query)
                print(f"✅ Retrieved {len(docs)} documents from global collection")
                
                if docs:
                    print(f"First document type: {type(docs[0])}")
                    if hasattr(docs[0], 'page_content'):
                        print(f"First document preview: {docs[0].page_content[:100]}...")
                    elif hasattr(docs[0], 'content'):
                        print(f"First document preview: {docs[0].content[:100]}...")
                
            except Exception as e:
                print(f"❌ Error accessing global collection: {str(e)}")
        else:
            print("❌ Global collection not found")
        
        print_section("4. Checking RAG Configuration")
        
        # Check RAG configuration
        top_k = RAGConfigService.get_retriever_top_k(db)
        print(f"Configured top_k for retrieval: {top_k}")
        
        # Check admin config for global collection prompt
        try:
            from app.services.admin_config_service import AdminConfigService
            from app.db.models import AdminConfig
            
            global_prompt = AdminConfigService.get_config(
                db, 
                AdminConfig.KEY_GLOBAL_RAG_PROMPT, 
                "Default global RAG prompt not set"
            )
            print(f"Global RAG prompt configured: {len(global_prompt) > 0}")
            if global_prompt and len(global_prompt) > 50:
                print(f"Global prompt preview: {global_prompt[:100]}...")
        except Exception as e:
            print(f"Error checking global prompt config: {str(e)}")
        
        print_section("5. Key Differences Analysis")
        
        print("🔍 ANALYSIS: Key Implementation Differences")
        print()
        print("1. RETRIEVAL APPROACH:")
        print("   - Global Collections: Uses contextualized questions")
        print("   - User Files: Direct query to retriever")
        print()
        print("2. HISTORY HANDLING:")
        print("   - Global Collections: CustomMessageHistory with LangChain")
        print("   - User Files: Manual message formatting")
        print()
        print("3. PROMPT TEMPLATES:")
        print("   - Global Collections: Context in template")
        print("   - User Files: Context in system message")
        print()
        print("4. ERROR HANDLING:")
        print("   - Global Collections: Fallback to regular LLM")
        print("   - User Files: Fallback to regular LLM stream")
        print()
        print("5. COLLECTION ACCESS:")
        print("   - Global Collections: Direct collection name")
        print("   - User Files: Conversation-specific collection name")
        
        print_section("6. Recommendations")
        
        print("🚀 RECOMMENDATIONS for debugging global collection issues:")
        print()
        print("1. Check if global collection actually has documents:")
        print("   - Verify document count in Milvus")
        print("   - Check document ingestion process")
        print()
        print("2. Test document retrieval separately:")
        print("   - Use direct retriever.ainvoke() test")
        print("   - Verify embedding function works")
        print()
        print("3. Compare prompt effectiveness:")
        print("   - Test with same prompt template as user files")
        print("   - Check if global prompt is too restrictive")
        print()
        print("4. Debug streaming vs non-streaming:")
        print("   - Test get_rag_response() vs get_streaming_rag_response()")
        print("   - Check if issue is in streaming logic")
        
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(test_rag_implementations())
