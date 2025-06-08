#!/usr/bin/env python3
"""
Simple test to check the /api/config/ endpoint structure and verify prompts are in general section.
"""

import sys
import os
sys.path.insert(0, "/app")

import asyncio
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.services.admin_config_service import AdminConfigService
from app.services.rag_config_service import RAGConfigService
from app.models.admin_config import AdminConfig
from app.api.routes.config import get_unified_config
from app.db.models import User, UserRole

def test_config_structure():
    """Test that prompts appear in the general section of unified config."""
    print("Testing Config Structure - Prompt Category Organization")
    print("=" * 65)
    
    db: Session = SessionLocal()
    
    try:
        # Set up test prompts with known values
        print("\n1. Setting up test prompts...")
        test_prompts = {
            "global": "TEST_GLOBAL_PROMPT - for global collections",
            "user": "TEST_USER_PROMPT - for user collections", 
            "chat": "TEST_CHAT_PROMPT - for regular chat"
        }
        
        RAGConfigService.set_global_collection_rag_prompt(db, test_prompts["global"])
        RAGConfigService.set_user_collection_rag_prompt(db, test_prompts["user"])
        RAGConfigService.set_regular_chat_prompt(db, test_prompts["chat"])
        print("✓ Test prompts configured")
        
        # Create a fake user for the function call
        fake_user = User(id=1, username="test", email="test@test.com", role=UserRole.USER)
        
        # Call the unified config endpoint directly
        print("\n2. Calling get_unified_config function...")
        config_result = asyncio.run(get_unified_config(db, fake_user))
        print("✓ Successfully retrieved unified config")
        
        # Print the structure for debugging
        print(f"\n3. Config structure analysis:")
        print(f"   - Available sections: {list(config_result.keys())}")
        
        if "rag" in config_result:
            rag_keys = list(config_result["rag"].keys())
            print(f"   - RAG section keys ({len(rag_keys)}): {rag_keys}")
            
        if "general" in config_result:
            general_keys = list(config_result["general"].keys())  
            print(f"   - General section keys ({len(general_keys)}): {general_keys}")
        
        # Check that prompts are in general section, not rag section
        print(f"\n4. Checking prompt locations...")
        
        # Check that general section contains all three prompts
        assert "general" in config_result, "General section missing from config"
        general_config = config_result["general"]
        
        # Check for each prompt in general section
        prompt_keys = [
            AdminConfig.KEY_GLOBAL_COLLECTION_RAG_PROMPT,
            AdminConfig.KEY_USER_COLLECTION_RAG_PROMPT, 
            AdminConfig.KEY_REGULAR_CHAT_PROMPT
        ]
        
        found_in_general = 0
        for key in prompt_keys:
            if key in general_config:
                found_in_general += 1
                print(f"   ✓ {key} found in general section")
                print(f"     Value: {general_config[key][:50]}...")
            else:
                print(f"   ❌ {key} NOT found in general section")
        
        # Check that prompts are NOT in rag section 
        found_in_rag = 0
        if "rag" in config_result:
            rag_config = config_result["rag"]
            for key in prompt_keys:
                if key in rag_config:
                    found_in_rag += 1
                    print(f"   ⚠️  {key} incorrectly found in rag section")
                    print(f"     Value: {rag_config[key][:50]}...")
        
        print(f"\n5. Results summary:")
        print(f"   - Prompts found in general section: {found_in_general}/3")
        print(f"   - Prompts found in rag section: {found_in_rag}/3")
        
        if found_in_general == 3 and found_in_rag == 0:
            print(f"   ✅ SUCCESS: All prompts correctly organized in 'general' section!")
            return True
        elif found_in_general == 3 and found_in_rag > 0:
            print(f"   ⚠️  WARNING: Prompts in both general and rag sections (duplicated)")
            return False
        elif found_in_general < 3:
            print(f"   ❌ FAILED: Some prompts missing from general section")
            return False
        else:
            print(f"   ❌ FAILED: Unexpected configuration")
            return False
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = test_config_structure()
    sys.exit(0 if success else 1)
