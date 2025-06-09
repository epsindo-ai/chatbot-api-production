#!/usr/bin/env python3
"""
Test script to demonstrate the contextualized query debug prints in the RAG pipeline.
This shows exactly what query gets sent to the vectorstore for similarity search.
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.database import SessionLocal
from app.services.rag_service import RagChatService
from app.config import settings
from app.db import crud
from app.db.schemas import MessageCreate

def print_section(title):
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)

async def test_contextualized_query_debug():
    """Test the contextualized query debug prints"""
    print_section("Contextualized Query Debug Test")
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Initialize RAG service
        rag_service = RagChatService(
            embedding_url=settings.REMOTE_EMBEDDER_URL,
            milvus_uri=settings.MILVUS_URI
        )
        
        # Find an existing collection to test with
        collections = rag_service.list_available_collections()
        test_collection = None
        
        # Look for an admin collection first, then any collection
        for col in collections:
            if col.startswith('admin_') and col != 'admin_a100h200h100':
                test_collection = col
                break
        
        if not test_collection:
            # Fall back to any collection
            for col in collections:
                if not col.startswith('conversation_'):
                    test_collection = col
                    break
        
        if not test_collection:
            print("❌ No suitable test collection found")
            return
        
        print(f"🎯 Testing with collection: {test_collection}")
        
        # Create a test conversation
        test_conversation = crud.create_conversation(db, user_id=1)
        conversation_id = test_conversation.id
        
        # Add some previous messages to create context for the contextualization
        prev_msg1 = MessageCreate(
            conversation_id=conversation_id,
            role="user", 
            content="What is a GPU?"
        )
        crud.create_message(db, prev_msg1)
        
        prev_msg2 = MessageCreate(
            conversation_id=conversation_id,
            role="assistant",
            content="A GPU (Graphics Processing Unit) is a specialized electronic circuit designed to rapidly manipulate and alter memory to accelerate the creation of images in a frame buffer intended for output to a display device."
        )
        crud.create_message(db, prev_msg2)
        
        # Test query that should be contextualized
        test_message = "How much memory does it have?"
        
        print_section("Testing Non-Streaming RAG Response")
        print(f"📝 Test message: '{test_message}'")
        print(f"📚 Collection: {test_collection}")
        print(f"💬 Conversation ID: {conversation_id}")
        print(f"📜 Previous context: 2 messages about GPUs")
        print("\n🔍 Watch for DEBUG prints showing original vs contextualized query:")
        
        try:
            # Call the non-streaming RAG method which will show contextualized query
            response = await rag_service.get_rag_response(
                db=db,
                user_id=1,
                message=test_message,
                collection_name=test_collection,
                conversation_id=conversation_id,
                meta_data={"test": "contextualized_debug"}
            )
            
            print(f"\n✅ Response received: {response['response'][:100]}...")
            
        except Exception as e:
            print(f"\n❌ Error in non-streaming test: {str(e)}")
        
        print_section("Testing Streaming RAG Response")
        print(f"📝 Same test message: '{test_message}'")
        print("\n🔍 Watch for DEBUG prints showing original vs contextualized query:")
        
        try:
            # Test the streaming version
            response_tokens = []
            async for token in rag_service.get_streaming_rag_response(
                db=db,
                user_id=1,
                message=test_message,
                collection_name=test_collection,
                conversation_id=conversation_id,
                meta_data={"test": "streaming_contextualized_debug"},
                save_user_message=False  # Don't save again
            ):
                response_tokens.append(token)
            
            full_response = "".join(response_tokens)
            print(f"\n✅ Streaming response received: {full_response[:100]}...")
            
        except Exception as e:
            print(f"\n❌ Error in streaming test: {str(e)}")
        
        print_section("Testing Conversation RAG (User Files)")
        print(f"📝 Test message: '{test_message}'")
        print("\n🔍 Watch for DEBUG STREAMING prints (no contextualization in this method):")
        
        try:
            # Test conversation RAG which uses direct query (no contextualization)
            async for token in rag_service.get_streaming_conversation_rag_response(
                db=db,
                conversation_id=conversation_id,
                query=test_message,
                user_id=1,
                conversation_collection=test_collection,
                save_user_message=False
            ):
                pass  # Just consume the tokens
            
            print(f"\n✅ Conversation RAG completed")
            
        except Exception as e:
            print(f"\n❌ Error in conversation RAG test: {str(e)}")
        
        print_section("Key Observations")
        print("🔍 CONTEXTUALIZATION DIFFERENCES:")
        print("• get_rag_response() & get_streaming_rag_response():")
        print("  - Creates standalone question from chat history + user input")
        print("  - DEBUG: Shows 'Original user message' vs 'Contextualized question'")
        print("  - This contextualized question goes to vectorstore")
        print("")
        print("• get_streaming_conversation_rag_response():")
        print("  - Uses original query directly (no contextualization)")
        print("  - DEBUG STREAMING: Shows query sent directly to vectorstore")
        print("  - No LLM step to create standalone question")
        print("")
        print("🎯 For similarity calculation troubleshooting:")
        print("• Look for 'Contextualized question sent to vectorstore' in logs")
        print("• Compare original vs contextualized - contextualized might be better/worse")
        print("• Check if context from previous messages helps or hurts retrieval")
        
    except Exception as e:
        print(f"❌ Error in test: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_contextualized_query_debug())
