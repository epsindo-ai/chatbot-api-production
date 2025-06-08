#!/usr/bin/env python3
"""
Test script to verify that prompts appear in the general section of /api/config/ endpoint.
"""

import sys
import os
sys.path.insert(0, "/app")

import json
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.database import SessionLocal
from app.services.admin_config_service import AdminConfigService
from app.services.rag_config_service import RAGConfigService
from app.models.admin_config import AdminConfig
from app.db import crud, models

def test_category_organization():
    """Test that prompts appear in the general section, not rag section."""
    print("Testing Category Organization in /api/config/ Endpoint")
    print("=" * 60)
    
    client = TestClient(app)
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
        
        # Create a test user for authentication
        print("\n2. Creating test user...")
        from app.db.schemas import UserCreate
        user_create = UserCreate(
            username="test_user_category123123",
            email="test_category123123@test.com", 
            password="test123"
        )
        test_user = crud.create_user(db, user_create)
        
        # Login to get token
        login_response = client.post("/auth/token", data={
            "username": test_user.username,
            "password": "test123"
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("✓ Test user authenticated")
        
        # Test the /api/config/ endpoint
        print("\n3. Testing /api/config/ endpoint...")
        response = client.get("/api/config/", headers=headers)
        assert response.status_code == 200, f"Unexpected status code: {response.status_code}"
        
        config_data = response.json()
        print("✓ Successfully retrieved config data")
        
        # Print the structure for debugging
        print(f"\n4. Config structure:")
        print(f"   - Available sections: {list(config_data.keys())}")
        
        if "rag" in config_data:
            rag_keys = list(config_data["rag"].keys())
            print(f"   - RAG section keys: {rag_keys}")
            
        if "general" in config_data:
            general_keys = list(config_data["general"].keys())  
            print(f"   - General section keys: {general_keys}")
        
        # Check that prompts are in general section, not rag section
        print(f"\n5. Checking prompt locations...")
        
        # Check that general section contains all three prompts
        assert "general" in config_data, "General section missing from config"
        general_config = config_data["general"]
        
        # Check for each prompt in general section
        prompt_keys = [
            AdminConfig.KEY_GLOBAL_COLLECTION_RAG_PROMPT,
            AdminConfig.KEY_USER_COLLECTION_RAG_PROMPT, 
            AdminConfig.KEY_REGULAR_CHAT_PROMPT
        ]
        
        for key in prompt_keys:
            assert key in general_config, f"Prompt {key} not found in general section"
            print(f"   ✓ {key} found in general section")
            print(f"     Value: {general_config[key][:50]}...")
        
        # Check that prompts are NOT in rag section (they should have been moved)
        if "rag" in config_data:
            rag_config = config_data["rag"]
            for key in prompt_keys:
                assert key not in rag_config, f"Prompt {key} incorrectly found in rag section"
                print(f"   ✓ {key} correctly NOT in rag section")
        
        print(f"\n6. Verification complete!")
        print(f"   ✓ All three prompts are in the 'general' section")
        print(f"   ✓ No prompts are in the 'rag' section") 
        print(f"   ✓ Category reorganization successful!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = test_category_organization()
    sys.exit(0 if success else 1)
