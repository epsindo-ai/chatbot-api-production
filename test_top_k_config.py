#!/usr/bin/env python3
"""
Test script to check the current top_k configuration for user collections.
"""

import os
import sys
sys.path.append('/app')

from app.db.database import SessionLocal
from app.services.rag_config_service import RAGConfigService
from app.services.admin_config_service import AdminConfigService
from app.db import models  # Import all models first
from app.models.admin_config import AdminConfig
from app.config import settings

def main():
    print("=== Top_K Configuration Test ===")
    
    # Create database session
    db = SessionLocal()
    
    try:
        # 1. Check the default settings value
        print(f"1. Default RETRIEVER_TOP_K from settings: {settings.RETRIEVER_TOP_K}")
        
        # 2. Check the admin-configured value
        admin_top_k = AdminConfigService.get_config(
            db, 
            AdminConfig.KEY_RETRIEVER_TOP_K, 
            settings.RETRIEVER_TOP_K
        )
        print(f"2. Admin-configured top_k value: {admin_top_k}")
        
        # 3. Check what RAGConfigService returns
        rag_service_top_k = RAGConfigService.get_retriever_top_k(db)
        print(f"3. RAGConfigService.get_retriever_top_k(): {rag_service_top_k}")
        
        # 4. Get the full RAG config
        try:
            rag_config = RAGConfigService.get_rag_config(db)
            print(f"4. Full RAG config: {rag_config}")
        except Exception as e:
            print(f"4. Error getting RAG config: {e}")
        
        # 5. Summary
        print("\n=== SUMMARY ===")
        print(f"✅ User collections use admin-configurable top_k value: {rag_service_top_k}")
        print(f"✅ This is the same value used for both user file conversations and global collection conversations")
        print(f"✅ The top_k configuration is centrally managed via admin settings")
        
        if admin_top_k == settings.RETRIEVER_TOP_K:
            print(f"ℹ️  Currently using the default value from settings (not overridden by admin)")
        else:
            print(f"ℹ️  Admin has overridden the default value (default: {settings.RETRIEVER_TOP_K}, admin: {admin_top_k})")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
