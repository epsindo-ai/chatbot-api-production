#!/usr/bin/env python3
"""
Test script to verify the 3 RAG chain flows:
1. Regular Chat (no RAG)
2. User Files RAG  
3. Global Collection RAG

This script tests the prompt selection logic and flow routing.
"""

import sys
import os
sys.path.append('/app')

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.services.rag_service import RagChatService
from app.services.llm_service import get_system_prompt
from app.services.rag_config_service import RAGConfigService
from app.db import crud

def test_prompt_selection():
    """Test which prompts are selected for different collection types."""
    print("🔍 Testing Prompt Selection Logic")
    print("=" * 50)
    
    db = SessionLocal()
    rag_service = RagChatService()
    
    try:
        # Test 1: Regular Chat Prompt
        print("\n1️⃣ REGULAR CHAT FLOW")
        print("-" * 30)
        regular_prompt = get_system_prompt(db)
        print(f"Regular chat prompt: {regular_prompt[:100] if regular_prompt else 'None (not configured)'}...")
        
        # Test 2: User Collection Prompt  
        print("\n2️⃣ USER FILES RAG FLOW")
        print("-" * 30)
        
        # Test with user collection
        user_collection = "user_123_documents"
        is_global = rag_service._is_global_collection(db, user_collection)
        user_prompt = rag_service._get_rag_system_prompt(db, user_collection)
        
        print(f"Collection: {user_collection}")
        print(f"Is global collection: {is_global}")
        print(f"Selected prompt: {user_prompt[:100]}...")
        
        # Test 3: Global Collection Prompt
        print("\n3️⃣ GLOBAL COLLECTION RAG FLOW")
        print("-" * 30)
        
        # Get predefined collection name
        predefined_collection = RAGConfigService.get_predefined_collection(db)
        print(f"Predefined collection name: {predefined_collection}")
        
        # Test with global collection
        global_collection = predefined_collection
        is_global = rag_service._is_global_collection(db, global_collection)
        global_prompt = rag_service._get_rag_system_prompt(db, global_collection)
        
        print(f"Collection: {global_collection}")
        print(f"Is global collection: {is_global}")
        print(f"Selected prompt: {global_prompt[:100]}...")
        
        # Test with admin-prefixed global collection
        admin_global_collection = f"admin_{predefined_collection}"
        is_global_admin = rag_service._is_global_collection(db, admin_global_collection)
        admin_global_prompt = rag_service._get_rag_system_prompt(db, admin_global_collection)
        
        print(f"\nCollection: {admin_global_collection}")
        print(f"Is global collection: {is_global_admin}")
        print(f"Selected prompt: {admin_global_prompt[:100]}...")
        
    except Exception as e:
        print(f"❌ Error testing prompt selection: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

def test_collection_detection():
    """Test the collection type detection logic."""
    print("\n\n🔍 Testing Collection Detection Logic")
    print("=" * 50)
    
    db = SessionLocal()
    rag_service = RagChatService()
    
    try:
        # Get predefined collection
        predefined = RAGConfigService.get_predefined_collection(db)
        print(f"Predefined collection: {predefined}")
        
        # Test cases
        test_cases = [
            ("user_123_documents", False, "User collection"),
            ("user_456_files", False, "User collection"), 
            (predefined, True, "Direct global collection"),
            (f"admin_{predefined}", True, "Admin-prefixed global"),
            ("some_random_collection", False, "Random collection"),
            (None, False, "No collection"),
            ("", False, "Empty collection"),
        ]
        
        print(f"\n{'Collection Name':<25} {'Is Global':<10} {'Description'}")
        print("-" * 55)
        
        for collection_name, expected, description in test_cases:
            try:
                is_global = rag_service._is_global_collection(db, collection_name)
                status = "✅" if is_global == expected else "❌"
                print(f"{str(collection_name):<25} {str(is_global):<10} {description} {status}")
            except Exception as e:
                print(f"{str(collection_name):<25} {'ERROR':<10} {description} ❌ ({str(e)})")
        
    except Exception as e:
        print(f"❌ Error testing collection detection: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

def test_prompt_configuration():
    """Test the prompt configuration system."""
    print("\n\n🔍 Testing Prompt Configuration")
    print("=" * 50)
    
    db = SessionLocal()
    
    try:
        # Test all configurable prompts
        prompts = [
            ("regular_chat_prompt", RAGConfigService.get_regular_chat_prompt),
            ("user_collection_rag_prompt", RAGConfigService.get_user_collection_rag_prompt),
            ("global_collection_rag_prompt", RAGConfigService.get_global_collection_rag_prompt),
        ]
        
        for prompt_name, prompt_getter in prompts:
            try:
                prompt_value = prompt_getter(db)
                status = "✅ Configured" if prompt_value else "⚠️ Not configured"
                length = len(prompt_value) if prompt_value else 0
                print(f"{prompt_name:<30} {status:<15} ({length} chars)")
                if prompt_value:
                    print(f"  Preview: {prompt_value[:80]}...")
                print()
            except Exception as e:
                print(f"{prompt_name:<30} ❌ Error: {str(e)}")
                print()
        
    except Exception as e:
        print(f"❌ Error testing prompt configuration: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

def test_contextualization_prompt():
    """Test the contextualization prompt location."""
    print("\n\n🔍 Testing Contextualization Prompt")
    print("=" * 50)
    
    # Read the actual file to check the prompt
    try:
        with open('/app/app/services/rag_service.py', 'r') as f:
            content = f.read()
            
        # Look for the contextualization prompt
        lines = content.split('\n')
        found_prompts = []
        
        for i, line in enumerate(lines):
            if "Given the chat history and the latest user question" in line:
                # Get context around this line
                start = max(0, i-2)
                end = min(len(lines), i+5)
                context = lines[start:end]
                found_prompts.append((i+1, context))
        
        print(f"Found {len(found_prompts)} contextualization prompt(s):")
        for line_num, context in found_prompts:
            print(f"\n📍 Line {line_num}:")
            for j, ctx_line in enumerate(context):
                marker = "👉 " if "Given the chat history" in ctx_line else "   "
                print(f"{marker}{ctx_line}")
                
    except Exception as e:
        print(f"❌ Error reading contextualization prompt: {str(e)}")

def main():
    """Run all tests."""
    print("🧪 RAG Chain Flow Testing")
    print("Testing the 3 conversation flows and prompt selection")
    print("=" * 60)
    
    test_prompt_selection()
    test_collection_detection() 
    test_prompt_configuration()
    test_contextualization_prompt()
    
    print("\n" + "=" * 60)
    print("✅ Testing completed!")
    print("\n📋 Summary:")
    print("• Regular Chat: Uses regular_chat_prompt (may not be configured)")
    print("• User Files: Uses user_collection_rag_prompt with contextualization")
    print("• Global Collection: Uses global_collection_rag_prompt with contextualization")
    print("• Contextualization: Single English prompt used for both RAG flows")
    print("• Streaming/Non-streaming: Same logic, different output method")

if __name__ == "__main__":
    main()
