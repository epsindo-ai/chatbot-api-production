#!/usr/bin/env python3

"""
Debug the global collection detection issue.
This script investigates why global collection detection is failing.
"""

import sys
sys.path.insert(0, "/app")

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.services.admin_config_service import AdminConfigService
from app.services.rag_config_service import RAGConfigService
from app.services.rag_service import RagChatService
from app.db import crud

def debug_global_collection_detection():
    """Debug the global collection detection issue."""
    print("Global Collection Detection Debug")
    print("=" * 50)
    
    # Create database session
    db: Session = SessionLocal()
    
    try:
        # 1. Check what the predefined collection is set to
        print("\n1. Current predefined collection configuration:")
        predefined_collection = RAGConfigService.get_predefined_collection(db)
        print(f"   Predefined collection: '{predefined_collection}'")
        
        # 2. Check admin collections in database
        print("\n2. Admin collections in database:")
        admin_collections = db.query(crud.models.Collection).filter(
            crud.models.Collection.is_admin_only == True,
            crud.models.Collection.is_active == True
        ).all()
        
        for collection in admin_collections:
            print(f"   - ID: {collection.id}, Name: '{collection.name}', Global Default: {collection.is_global_default}")
        
        # 3. Check global default collection
        print("\n3. Global default collection:")
        global_default = crud.get_global_default_collection(db)
        if global_default:
            print(f"   Global default: ID={global_default.id}, Name='{global_default.name}'")
        else:
            print("   No global default collection set")
        
        # 4. Test the detection logic with different collection names
        print("\n4. Testing global collection detection logic:")
        rag_service = RagChatService()
        
        test_collections = [
            predefined_collection if predefined_collection else "None",
            f"admin_{predefined_collection}" if predefined_collection else "admin_None",
            "test_collection",
            "admin_test_collection",
            "company_policies",
            "admin_company_policies"
        ]
        
        for test_name in test_collections:
            if test_name != "None" and test_name != "admin_None":
                is_global = rag_service._is_global_collection(db, test_name)
                print(f"   Collection '{test_name}' -> is_global: {is_global}")
        
        # 5. Check if we can find any collections in Milvus
        print("\n5. Collections in Milvus:")
        try:
            milvus_collections = rag_service.list_available_collections()
            print(f"   Available Milvus collections: {milvus_collections}")
            
            # Check if any admin collections exist in Milvus
            for collection in admin_collections:
                collection_exists = rag_service.vectorstore_manager.collection_exists(collection.name)
                admin_prefixed_exists = rag_service.vectorstore_manager.collection_exists(f"admin_{collection.name}")
                print(f"   Collection '{collection.name}' exists in Milvus: {collection_exists}")
                print(f"   Collection 'admin_{collection.name}' exists in Milvus: {admin_prefixed_exists}")
        except Exception as e:
            print(f"   Error checking Milvus collections: {e}")
        
        # 6. Check RAG prompts
        print("\n6. RAG prompt testing:")
        global_prompt = RAGConfigService.get_global_collection_rag_prompt(db)
        print(f"   Global collection prompt (first 100 chars): {global_prompt[:100]}...")
        
        if predefined_collection:
            selected_prompt = rag_service._get_rag_system_prompt(db, predefined_collection)
            print(f"   Prompt for '{predefined_collection}' (first 100 chars): {selected_prompt[:100]}...")
            
            # Test admin prefixed name
            admin_prompt = rag_service._get_rag_system_prompt(db, f"admin_{predefined_collection}")
            print(f"   Prompt for 'admin_{predefined_collection}' (first 100 chars): {admin_prompt[:100]}...")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    debug_global_collection_detection()
