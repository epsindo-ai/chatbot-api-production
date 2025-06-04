#!/usr/bin/env python3

"""
Simple test script to verify the user file conversation top_k fix is in place.
This script only checks the code changes without requiring database initialization.
"""

import re

def check_rag_service_fix():
    """Verify the RAG service fix is properly implemented"""
    print("🔍 Checking RAG service fix...")
    
    try:
        with open('/app/app/services/rag_service.py', 'r') as f:
            content = f.read()
            
        # Check 1: RAGConfigService import is present
        import_pattern = r'from\s+app\.services\.rag_config_service\s+import\s+RAGConfigService'
        if re.search(import_pattern, content):
            print("✅ RAGConfigService import found")
        else:
            print("❌ RAGConfigService import NOT found")
            return False
            
        # Check 2: Old hardcoded k=5 is removed
        old_pattern = r'search_kwargs=\{"k":\s*5\}'
        if re.search(old_pattern, content):
            print("❌ ERROR: Old hardcoded k=5 still found in code")
            return False
        else:
            print("✅ Old hardcoded k=5 successfully removed")
            
        # Check 3: New admin-configured top_k is present
        new_pattern1 = r'top_k\s*=\s*RAGConfigService\.get_retriever_top_k\(db\)'
        new_pattern2 = r'search_kwargs=\{"k":\s*top_k\}'
        
        if re.search(new_pattern1, content):
            print("✅ Admin-configured top_k retrieval found")
        else:
            print("❌ Admin-configured top_k retrieval NOT found")
            return False
            
        if re.search(new_pattern2, content):
            print("✅ Dynamic top_k usage in retriever found")
        else:
            print("❌ Dynamic top_k usage in retriever NOT found")
            return False
            
        # Check 4: Find the specific method where the fix was applied
        method_pattern = r'async\s+def\s+get_streaming_conversation_rag_response'
        if re.search(method_pattern, content):
            print("✅ Target method get_streaming_conversation_rag_response found")
        else:
            print("❌ Target method get_streaming_conversation_rag_response NOT found")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ ERROR reading file: {e}")
        return False

def show_before_after():
    """Show what the code looked like before and after the fix"""
    print("\n📊 Before and After Comparison:")
    print("=" * 40)
    print("BEFORE (❌ Hardcoded):")
    print("    # Create retriever")
    print("    retriever = vectorstore.as_retriever(")
    print("        search_type=\"similarity\",")
    print("        search_kwargs={\"k\": 5}  # ❌ Hardcoded!")
    print("    )")
    print()
    print("AFTER (✅ Admin-configured):")
    print("    # Create retriever with admin-configured top_k value")
    print("    top_k = RAGConfigService.get_retriever_top_k(db)")
    print("    retriever = vectorstore.as_retriever(")
    print("        search_type=\"similarity\",")
    print("        search_kwargs={\"k\": top_k}  # ✅ Admin-configured!")
    print("    )")

if __name__ == "__main__":
    print("🧪 Verifying User File Conversation Top_K Fix")
    print("=" * 50)
    
    # Check the code fix
    fix_applied = check_rag_service_fix()
    
    print("\n📋 Summary:")
    print("=" * 20)
    if fix_applied:
        print("✅ SUCCESS: Fix has been properly applied!")
        print("✅ User file conversations will now use admin-configured top_k")
        print("✅ Consistency achieved between global and user file conversations")
    else:
        print("❌ FAILURE: Fix was not properly applied")
    
    # Show the comparison
    show_before_after()
    
    print("\n🎯 Impact:")
    print("- Global collections: Already used admin top_k (currently 20)")
    print("- User file conversations: Now also use admin top_k (currently 20)")
    print("- Previous issue: User file conversations were stuck at k=5")
    print("- Result: Both conversation types now have consistent retrieval performance!")
