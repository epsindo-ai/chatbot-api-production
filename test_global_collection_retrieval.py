#!/usr/bin/env python3

"""
Test actual document retrieval from the global collection.
"""

import sys
sys.path.insert(0, "/app")

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.services.rag_service import RagChatService
import asyncio

async def test_global_collection_retrieval():
    """Test document retrieval from the actual global collection."""
    print("Testing Global Collection Document Retrieval")
    print("=" * 50)
    
    db: Session = SessionLocal()
    rag_service = RagChatService()
    
    try:
        # Test with the actual global collection
        global_collection = "admin_a100h200h100"
        
        print(f"\n1. Testing collection: {global_collection}")
        
        # Check if collection exists
        exists = rag_service.vectorstore_manager.collection_exists(global_collection)
        print(f"   Collection exists in Milvus: {exists}")
        
        if not exists:
            print(f"   ❌ Collection doesn't exist, cannot test retrieval")
            return
        
        # Get retriever
        try:
            retriever = rag_service.vectorstore_manager.get_retriever(global_collection, top_k=5)
            print(f"   ✅ Created retriever successfully")
        except Exception as e:
            print(f"   ❌ Failed to create retriever: {e}")
            return
        
        # Test simple queries
        test_queries = [
            "What is this?",
            "Tell me about the content",
            "What information do you have?",
            "Explain the main topic",
            "What is A100?"
        ]
        
        for query in test_queries:
            print(f"\n   Testing query: '{query}'")
            try:
                docs = await retriever.ainvoke(query)
                print(f"   Retrieved {len(docs)} documents")
                
                if docs:
                    # Show first document
                    doc = docs[0]
                    if hasattr(doc, 'page_content'):
                        content = doc.page_content[:200]
                        print(f"   First doc content: {content}...")
                    elif isinstance(doc, dict):
                        content = str(doc)[:200]
                        print(f"   First doc (dict): {content}...")
                    else:
                        print(f"   First doc type: {type(doc)}")
                else:
                    print(f"   ❌ No documents retrieved")
                    
            except Exception as e:
                print(f"   ❌ Error retrieving docs: {e}")
        
        # Test with the actual RAG flow
        print(f"\n2. Testing full RAG response")
        try:
            response = await rag_service.get_rag_response(
                db=db,
                user_id=1,  # Admin user ID
                message="What is A100?",
                collection_name=global_collection
            )
            print(f"   RAG Response: {response['response'][:200]}...")
        except Exception as e:
            print(f"   ❌ Error in RAG response: {e}")
            import traceback
            traceback.print_exc()
            
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_global_collection_retrieval())
