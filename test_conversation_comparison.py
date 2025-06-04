#!/usr/bin/env python3

"""
Compare user file conversations vs global collection conversations.
This test simulates the exact same scenario as reported by the user.
"""

import sys
sys.path.insert(0, "/app")

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.services.rag_service import RagChatService
from app.db import crud
import asyncio

async def test_conversation_comparison():
    """Test and compare user file vs global collection conversations."""
    print("Conversation Comparison Test")
    print("=" * 60)
    
    db: Session = SessionLocal()
    rag_service = RagChatService()
    
    try:
        # Test question
        test_question = "What is A100?"
        
        print(f"Test Question: '{test_question}'\n")
        
        # 1. Test Global Collection Conversation
        print("=" * 60)
        print(" 1. GLOBAL COLLECTION CONVERSATION TEST")
        print("=" * 60)
        
        try:
            # Create a global collection conversation
            global_conversation = crud.create_conversation_with_global_collection(db, user_id=1)
            print(f"Created global conversation ID: {global_conversation.id}")
            print(f"Conversation type: {global_conversation.conversation_type}")
            print(f"Linked global collection ID: {global_conversation.linked_global_collection_id}")
            
            # Get the global collection name 
            global_collection = crud.get_global_default_collection(db)
            collection_name = f"admin_{global_collection.name}" if global_collection else None
            print(f"Using collection: {collection_name}")
            
            if collection_name:
                # Test using streaming conversation RAG response (like unified chat)
                print(f"\nTesting streaming conversation RAG response...")
                response_parts = []
                async for chunk in rag_service.get_streaming_conversation_rag_response(
                    db=db,
                    conversation_id=global_conversation.id,
                    query=test_question,
                    user_id=1,
                    conversation_collection=collection_name
                ):
                    response_parts.append(chunk)
                
                full_response = "".join(response_parts)
                print(f"Global Collection Response ({len(full_response)} chars):")
                print(f"   {full_response[:300]}...")
                
                # Check if response is meaningful
                if len(full_response.strip()) < 10:
                    print(f"   ❌ Response too short, might be an issue")
                elif "I don't know" in full_response or "I don't have" in full_response:
                    print(f"   ⚠️ Response indicates no knowledge")
                else:
                    print(f"   ✅ Response seems informative")
            else:
                print(f"   ❌ No global collection found")
                
        except Exception as e:
            print(f"   ❌ Error in global collection test: {e}")
            import traceback
            traceback.print_exc()
        
        # 2. Test User File Conversation
        print(f"\n{'=' * 60}")
        print(" 2. USER FILE CONVERSATION TEST")
        print("=" * 60)
        
        try:
            # Find a user conversation with files
            user_conversations = db.query(crud.models.Conversation).filter(
                crud.models.Conversation.conversation_type == crud.models.ConversationType.USER_FILES
            ).limit(5).all()
            
            print(f"Found {len(user_conversations)} user file conversations")
            
            for conv in user_conversations[:1]:  # Test first one
                print(f"Testing conversation ID: {conv.id}")
                
                # Get conversation collection name
                conversation_collection = f"conversation_{conv.id}"
                
                # Check if collection exists
                exists = rag_service.vectorstore_manager.collection_exists(conversation_collection)
                print(f"Collection '{conversation_collection}' exists: {exists}")
                
                if exists:
                    print(f"\nTesting user file conversation...")
                    response_parts = []
                    async for chunk in rag_service.get_streaming_conversation_rag_response(
                        db=db,
                        conversation_id=conv.id,
                        query=test_question,
                        user_id=conv.user_id,
                        conversation_collection=conversation_collection
                    ):
                        response_parts.append(chunk)
                    
                    full_response = "".join(response_parts)
                    print(f"User File Response ({len(full_response)} chars):")
                    print(f"   {full_response[:300]}...")
                    
                    # Check if response is meaningful
                    if len(full_response.strip()) < 10:
                        print(f"   ❌ Response too short, might be an issue")
                    elif "I don't know" in full_response or "I don't have" in full_response:
                        print(f"   ⚠️ Response indicates no knowledge")
                    else:
                        print(f"   ✅ Response seems informative")
                    
                    break
                else:
                    print(f"   Skipping conversation {conv.id} - no collection")
                    
        except Exception as e:
            print(f"   ❌ Error in user file test: {e}")
            import traceback
            traceback.print_exc()
        
        # 3. Test Direct Collection Access
        print(f"\n{'=' * 60}")
        print(" 3. DIRECT COLLECTION ACCESS TEST")
        print("=" * 60)
        
        try:
            # Test direct RAG access to global collection
            global_collection = crud.get_global_default_collection(db)
            collection_name = f"admin_{global_collection.name}" if global_collection else None
            
            if collection_name:
                print(f"Testing direct RAG with collection: {collection_name}")
                
                response = await rag_service.get_rag_response(
                    db=db,
                    user_id=1,
                    message=test_question,
                    collection_name=collection_name
                )
                
                print(f"Direct RAG Response ({len(response['response'])} chars):")
                print(f"   {response['response'][:300]}...")
                
                # Check if response is meaningful
                if len(response['response'].strip()) < 10:
                    print(f"   ❌ Response too short, might be an issue")
                elif "I don't know" in response['response'] or "I don't have" in response['response']:
                    print(f"   ⚠️ Response indicates no knowledge")
                else:
                    print(f"   ✅ Response seems informative")
                    
        except Exception as e:
            print(f"   ❌ Error in direct collection test: {e}")
            import traceback
            traceback.print_exc()
            
        # 4. Summary
        print(f"\n{'=' * 60}")
        print(" 4. ANALYSIS SUMMARY")
        print("=" * 60)
        
        print("If global collections can't answer questions while user files can:")
        print("1. Check if the global collection has relevant documents")
        print("2. Check if the global prompt is too restrictive")
        print("3. Check if there are differences in retrieval approaches")
        print("4. Check if the admin prefix is correctly applied")
        print("5. Check if LLM thinking mode affects responses")
        
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_conversation_comparison())
