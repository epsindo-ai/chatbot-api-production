#!/usr/bin/env python3
"""
Test script to verify that all configuration issues have been fixed.
This script tests:
1. LLM config CRUD operations with dict serialization
2. Admin config presence for 'general' and 'rag' categories  
3. Database state consistency
"""

import json
import sys
from app.db.database import get_db
from app.db import crud, schemas
from sqlalchemy import text

def test_database_state():
    """Test basic database state."""
    print("=== TESTING DATABASE STATE ===")
    db = next(get_db())
    try:
        # Check if unified_config table exists (should not exist)
        try:
            db.execute(text('SELECT COUNT(*) FROM unified_config'))
            print("❌ unified_config table still exists (should be removed)")
            db.rollback()  # Rollback transaction on error
            return False
        except Exception:
            print("✅ unified_config table does not exist (correct)")
            db.rollback()  # Rollback to clear the failed transaction
        
        # Start fresh connection for next tests
        db.close()
        db = next(get_db())
        
        # Check llm_config table
        result = db.execute(text('SELECT COUNT(*) FROM llm_config'))
        llm_count = result.scalar()
        print(f"✅ llm_config table has {llm_count} rows")
        
        # Check admin_config table
        result = db.execute(text('SELECT category, COUNT(*) FROM admin_config GROUP BY category'))
        categories = result.fetchall()
        print(f"✅ admin_config categories: {dict(categories)}")
        
        # Verify general and rag categories exist
        has_general = any(cat[0] == 'general' for cat in categories)
        has_rag = any(cat[0] == 'rag' for cat in categories)
        
        if not has_general:
            print("❌ Missing 'general' category in admin_config")
            return False
        if not has_rag:
            print("❌ Missing 'rag' category in admin_config")
            return False
            
        print("✅ Both 'general' and 'rag' categories exist in admin_config")
        return True
        
    except Exception as e:
        print(f"❌ Database state test failed: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def test_llm_config_crud():
    """Test LLM config CRUD operations with dict serialization."""
    print("\n=== TESTING LLM CONFIG CRUD ===")
    db = next(get_db())
    try:
        # Test creating config with dict extra_params
        test_config = schemas.LLMConfigCreate(
            name='Test Config 2025',
            model_name='test-model-v2',
            temperature=0.5,
            top_p=0.95,
            max_tokens=4000,
            description='Test config for dict serialization',
            extra_params={
                'test_param': 'success',
                'number_param': 42,
                'bool_param': True,
                'nested_object': {'key': 'value'}
            },
            enable_thinking=True
        )
        
        print("Testing create_llm_config with dict extra_params...")
        result = crud.create_llm_config(db, test_config)
        if not result:
            print("❌ create_llm_config returned None")
            return False
            
        print(f"✅ Created config: {result.name}")
        print(f"✅ Extra params type: {type(result.extra_params)}")
        print(f"✅ Extra params: {result.extra_params}")
        
        # Test updating config with dict extra_params
        update_config = schemas.LLMConfigUpdate(
            description='Updated via test script',
            extra_params={
                'updated_test': 'new_value',
                'timestamp': '2025-06-25',
                'complex_data': {'list': [1, 2, 3], 'dict': {'nested': True}}
            },
            temperature=0.6
        )
        
        print("\nTesting update_llm_config with dict extra_params...")
        updated_result = crud.update_llm_config(db, update_config)
        if not updated_result:
            print("❌ update_llm_config returned None")
            return False
            
        print(f"✅ Updated config: {updated_result.name}")
        print(f"✅ Updated description: {updated_result.description}")
        print(f"✅ Updated temperature: {updated_result.temperature}")
        print(f"✅ Updated extra params: {updated_result.extra_params}")
        
        return True
        
    except Exception as e:
        print(f"❌ LLM config CRUD test failed: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def test_admin_config():
    """Test admin config presence and content."""
    print("\n=== TESTING ADMIN CONFIG ===")
    db = next(get_db())
    try:
        # Check general category configs
        result = db.execute(text("SELECT key, value FROM admin_config WHERE category = 'general'"))
        general_configs = {row[0]: row[1] for row in result.fetchall()}
        
        required_general = ['system_prompt', 'thinking_prompt', 'regular_chat_prompt']
        missing_general = [key for key in required_general if key not in general_configs]
        
        if missing_general:
            print(f"❌ Missing general configs: {missing_general}")
            return False
        
        print(f"✅ General configs present ({len(general_configs)}): {list(general_configs.keys())}")
        
        # Check rag category configs  
        result = db.execute(text("SELECT key, value FROM admin_config WHERE category = 'rag'"))
        rag_configs = {row[0]: row[1] for row in result.fetchall()}
        
        required_rag = ['retrieval_prompt', 'retriever_top_k', 'allow_user_uploads']
        missing_rag = [key for key in required_rag if key not in rag_configs]
        
        if missing_rag:
            print(f"❌ Missing rag configs: {missing_rag}")
            return False
            
        print(f"✅ RAG configs present ({len(rag_configs)}): {list(rag_configs.keys())}")
        
        return True
        
    except Exception as e:
        print(f"❌ Admin config test failed: {e}")
        return False
    finally:
        db.close()

def main():
    """Run all tests."""
    print("🧪 STARTING CONFIGURATION FIX VERIFICATION TESTS")
    print("=" * 60)
    
    tests = [
        test_database_state,
        test_llm_config_crud,
        test_admin_config
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_func.__name__} PASSED")
            else:
                failed += 1
                print(f"❌ {test_func.__name__} FAILED")
        except Exception as e:
            failed += 1
            print(f"❌ {test_func.__name__} FAILED with exception: {e}")
        
        print("-" * 40)
    
    print(f"\n🎯 TEST SUMMARY: {passed} PASSED, {failed} FAILED")
    
    if failed == 0:
        print("🎉 ALL TESTS PASSED! Configuration is working correctly.")
        print("\n✅ Fixed Issues:")
        print("  • Removed unified_config table")
        print("  • Fixed LLM config dict serialization to JSON")
        print("  • Ensured admin_config has general and rag categories")
        print("  • All CRUD operations working with proper JSON handling")
        return True
    else:
        print("💥 SOME TESTS FAILED! Please check the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
