#!/usr/bin/env python3
"""
Test script for global collection behavior functionality.
This script tests the new features for handling global collection changes.
"""

import requests
import json
import sys
import time

# Configuration
BASE_URL = "http://localhost:8000"
USERNAME = "admin"
PASSWORD = "admin"

def login():
    """Login and get access token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "username": USERNAME,
        "password": PASSWORD
    })
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"Login failed: {response.text}")
        return None

def test_global_collection_behavior(token):
    """Test the global collection behavior functionality"""
    headers = {"Authorization": f"Bearer {token}"}
    
    print("=== Testing Global Collection Behavior ===\n")
    
    # 1. Get current behavior
    print("1. Getting current global collection behavior...")
    response = requests.get(f"{BASE_URL}/api/config/global-collection-behavior", headers=headers)
    if response.status_code == 200:
        current_behavior = response.json()
        print(f"   Current behavior: {current_behavior['behavior']}")
        print(f"   Description: {current_behavior['description']}")
    else:
        print(f"   Failed to get behavior: {response.text}")
        return False
    
    # 2. Test setting behavior to readonly_on_change
    print("\n2. Setting behavior to 'readonly_on_change'...")
    response = requests.put(f"{BASE_URL}/api/config/global-collection-behavior", 
                          params={"behavior": "readonly_on_change"}, headers=headers)
    if response.status_code == 200:
        result = response.json()
        print(f"   Success: {result['message']}")
    else:
        print(f"   Failed to set behavior: {response.text}")
        return False
    
    # 3. Test setting behavior to auto_update
    print("\n3. Setting behavior to 'auto_update'...")
    response = requests.put(f"{BASE_URL}/api/config/global-collection-behavior", 
                          params={"behavior": "auto_update"}, headers=headers)
    if response.status_code == 200:
        result = response.json()
        print(f"   Success: {result['message']}")
    else:
        print(f"   Failed to set behavior: {response.text}")
        return False
    
    # 4. Test invalid behavior
    print("\n4. Testing invalid behavior...")
    response = requests.put(f"{BASE_URL}/api/config/global-collection-behavior", 
                          params={"behavior": "invalid_behavior"}, headers=headers)
    if response.status_code == 400:
        print("   Correctly rejected invalid behavior")
    else:
        print(f"   Unexpected response: {response.status_code} - {response.text}")
    
    # 5. Test conversation initiation with global collection
    print("\n5. Testing conversation initiation with global collection...")
    response = requests.post(f"{BASE_URL}/api/chat/initiate-with-global-collection", headers=headers)
    if response.status_code == 201:
        conversation_data = response.json()
        conversation_id = conversation_data["conversation_id"]
        print(f"   Created conversation: {conversation_id}")
        
        # 6. Test getting global collection status
        print("\n6. Testing global collection status...")
        response = requests.get(f"{BASE_URL}/api/chat/conversations/{conversation_id}/global-collection-status", 
                              headers=headers)
        if response.status_code == 200:
            status_data = response.json()
            print(f"   Conversation type: {status_data['conversation_type']}")
            print(f"   Is global collection: {status_data['is_global_collection']}")
            print(f"   Behavior: {status_data['behavior']}")
            print(f"   Is outdated: {status_data['is_outdated']}")
            print(f"   Original collection: {status_data['original_collection_name']}")
            print(f"   Current collection: {status_data['current_global_collection_name']}")
            print(f"   Message: {status_data['message']}")
        else:
            print(f"   Failed to get status: {response.text}")
    else:
        print(f"   Failed to create conversation: {response.text}")
        return False
    
    print("\n=== All tests completed successfully! ===")
    return True

def test_config_endpoints(token):
    """Test the configuration endpoints"""
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n=== Testing Configuration Endpoints ===\n")
    
    # Test getting unified config
    print("1. Getting unified configuration...")
    response = requests.get(f"{BASE_URL}/api/config/", headers=headers)
    if response.status_code == 200:
        config = response.json()
        if "rag" in config and "global_collection_behavior" in config["rag"]:
            print(f"   Global collection behavior in config: {config['rag']['global_collection_behavior']}")
        else:
            print("   Global collection behavior not found in unified config")
    else:
        print(f"   Failed to get unified config: {response.text}")
    
    # Test getting RAG category config
    print("\n2. Getting RAG category configuration...")
    response = requests.get(f"{BASE_URL}/api/config/rag", headers=headers)
    if response.status_code == 200:
        rag_config = response.json()
        if "rag" in rag_config and "global_collection_behavior" in rag_config["rag"]:
            print(f"   Global collection behavior in RAG config: {rag_config['rag']['global_collection_behavior']}")
        else:
            print("   Global collection behavior not found in RAG config")
    else:
        print(f"   Failed to get RAG config: {response.text}")

def main():
    """Main test function"""
    print("Starting Global Collection Behavior Tests...\n")
    
    # Login
    token = login()
    if not token:
        print("Failed to login. Exiting.")
        sys.exit(1)
    
    print(f"Successfully logged in!\n")
    
    # Run tests
    try:
        success = test_global_collection_behavior(token)
        if success:
            test_config_endpoints(token)
            print("\n🎉 All tests passed!")
        else:
            print("\n❌ Some tests failed!")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 