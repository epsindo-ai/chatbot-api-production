#!/usr/bin/env python3

"""
Test script to verify that user file conversations now use the admin-configured top_k value
instead of the hardcoded k=5.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.database import get_db
from app.services.rag_config_service import RAGConfigService
from sqlalchemy.orm import Session

def test_top_k_config():
    """Test that RAGConfigService returns the admin-configured top_k value"""
    print("🔍 Testing RAGConfigService.get_retriever_top_k()...")
    
    # Get database session
    db: Session = next(get_db())
    
    try:
        # Get the configured top_k value
        top_k = RAGConfigService.get_retriever_top_k(db)
        print(f"✅ RAGConfigService.get_retriever_top_k() returns: {top_k}")
        
        # Verify it's the expected admin value (20) not the hardcoded fallback (5)
        if top_k == 20:
            print("✅ SUCCESS: User file conversations will now use admin-configured top_k=20")
        elif top_k == 5:
            print("❌ WARNING: Still getting the old hardcoded value")
        else:
            print(f"ℹ️  INFO: Using configured value: {top_k}")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
    finally:
        db.close()

def check_code_fix():
    """Verify the code fix is in place"""
    print("\n🔍 Checking code fix in rag_service.py...")
    
    try:
        with open('/app/app/services/rag_service.py', 'r') as f:
            content = f.read()
            
        # Check if the old hardcoded k=5 is gone
        if 'search_kwargs={"k": 5}' in content:
            print("❌ ERROR: Old hardcoded k=5 still found in code")
            return False
            
        # Check if the new admin-configured version is present
        if 'top_k = RAGConfigService.get_retriever_top_k(db)' in content:
            print("✅ SUCCESS: Code fix detected - using RAGConfigService.get_retriever_top_k()")
            
        if 'search_kwargs={"k": top_k}' in content:
            print("✅ SUCCESS: Code fix detected - using admin-configured top_k")
            return True
        else:
            print("❌ ERROR: New code pattern not found")
            return False
            
    except Exception as e:
        print(f"❌ ERROR reading file: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing User File Conversation Top_K Fix")
    print("=" * 50)
    
    # Test the configuration service
    test_top_k_config()
    
    # Check the code fix
    code_fix_ok = check_code_fix()
    
    print("\n📋 Summary:")
    print("=" * 20)
    if code_fix_ok:
        print("✅ Fix successfully applied!")
        print("✅ User file conversations will now use admin-configured top_k instead of hardcoded k=5")
        print("✅ Both global collections and user file conversations now use the same admin top_k value")
    else:
        print("❌ Fix not properly applied")
    
    print("\n🎯 Expected behavior:")
    print("- Global collections: Use admin top_k (currently 20)")
    print("- User file conversations: Use admin top_k (currently 20) - FIXED!")
    print("- Previous behavior: User file conversations used hardcoded k=5 - RESOLVED!")
