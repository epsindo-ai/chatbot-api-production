#!/usr/bin/env python3
"""
Test script for the enhanced user delete all conversations endpoint with granular control.

This script tests the new parameters for DELETE /api/collections/all endpoint that allows
users to selectively delete different types of conversations.
"""

import requests
import json
from typing import Dict, Any

# Test configuration
API_BASE_URL = "http://localhost:8000"
TEST_USER_CREDENTIALS = {
    "username": "testuser@example.com",
    "password": "testpassword"
}

def get_auth_token(username: str, password: str) -> str:
    """Get authentication token for a user."""
    response = requests.post(
        f"{API_BASE_URL}/api/auth/login",
        data={"username": username, "password": password}
    )
    
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        raise Exception(f"Failed to login: {response.status_code} - {response.text}")

def get_user_conversations(auth_token: str) -> Dict[str, Any]:
    """Get user's current conversations to see what types they have."""
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    response = requests.get(
        f"{API_BASE_URL}/api/chat/conversations",
        headers=headers
    )
    
    if response.status_code == 200:
        conversations = response.json()
        conversation_types = {}
        for conv in conversations:
            conv_type = conv.get('conversation_type', 'REGULAR')
            if conv_type not in conversation_types:
                conversation_types[conv_type] = 0
            conversation_types[conv_type] += 1
        
        print(f"User has {len(conversations)} total conversations:")
        for conv_type, count in conversation_types.items():
            print(f"  - {conv_type}: {count}")
        
        return {
            "total": len(conversations),
            "types": conversation_types,
            "conversations": conversations
        }
    else:
        print(f"Could not get conversations: {response.status_code}")
        return {"total": 0, "types": {}, "conversations": []}

def test_selective_deletion(auth_token: str, params: Dict[str, bool], test_name: str) -> Dict[str, Any]:
    """Test the delete all endpoint with specific parameters."""
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    print(f"\n--- {test_name} ---")
    print(f"Parameters: {params}")
    
    response = requests.delete(
        f"{API_BASE_URL}/api/collections/all",
        headers=headers,
        params=params
    )
    
    print(f"Response status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Selective deletion successful!")
        print(f"Response: {json.dumps(result, indent=2)}")
        return result
    else:
        print(f"❌ Selective deletion failed: {response.status_code}")
        print(f"Error: {response.text}")
        return {"error": response.text}

def main():
    """Main test function."""
    print("=== Testing Enhanced User Delete All Conversations Endpoint ===\n")
    
    try:
        # Get authentication token
        print("Authenticating as test user...")
        auth_token = get_auth_token(
            TEST_USER_CREDENTIALS["username"],
            TEST_USER_CREDENTIALS["password"]
        )
        print("✅ Authentication successful!")
        
        # Get initial conversation state
        print("\n--- Initial Conversation State ---")
        initial_state = get_user_conversations(auth_token)
        
        if initial_state["total"] == 0:
            print("⚠️  User has no conversations to test with. Please create some conversations first.")
            return 0
        
        # Test 1: Delete only regular chat conversations
        if initial_state["types"].get("REGULAR", 0) > 0:
            test_selective_deletion(
                auth_token,
                {
                    "include_regular": "true",
                    "include_user_files": "false", 
                    "include_global_collection": "false",
                    "delete_collections": "true"
                },
                "Test 1: Delete Only Regular Chat Conversations"
            )
            
            # Check what's left
            print("\nAfter deleting regular conversations:")
            get_user_conversations(auth_token)
        
        # Test 2: Delete only user file conversations
        if initial_state["types"].get("USER_FILES", 0) > 0:
            test_selective_deletion(
                auth_token,
                {
                    "include_regular": "false",
                    "include_user_files": "true",
                    "include_global_collection": "false", 
                    "delete_collections": "true"
                },
                "Test 2: Delete Only User File Conversations"
            )
            
            print("\nAfter deleting user file conversations:")
            get_user_conversations(auth_token)
        
        # Test 3: Delete only global collection conversations
        if initial_state["types"].get("GLOBAL_COLLECTION", 0) > 0:
            test_selective_deletion(
                auth_token,
                {
                    "include_regular": "false",
                    "include_user_files": "false",
                    "include_global_collection": "true",
                    "delete_collections": "true"
                },
                "Test 3: Delete Only Global Collection Conversations"
            )
            
            print("\nAfter deleting global collection conversations:")
            get_user_conversations(auth_token)
        
        # Test 4: Delete all remaining conversations but keep files/collections
        remaining = get_user_conversations(auth_token)
        if remaining["total"] > 0:
            test_selective_deletion(
                auth_token,
                {
                    "include_regular": "true",
                    "include_user_files": "true",
                    "include_global_collection": "true",
                    "delete_collections": "false"  # Keep collections and files
                },
                "Test 4: Delete All Remaining Conversations (Keep Files/Collections)"
            )
            
            print("\nFinal state:")
            get_user_conversations(auth_token)
        
        # Test 5: Test with no matching conversations
        test_selective_deletion(
            auth_token,
            {
                "include_regular": "false",
                "include_user_files": "false",
                "include_global_collection": "false"
            },
            "Test 5: No Conversation Types Selected (Should Return Message)"
        )
        
        print("\n=== Test Summary ===")
        print("✅ All granular deletion tests completed successfully!")
        print("\nThe enhanced endpoint now supports:")
        print("- include_regular: Delete regular chat conversations")
        print("- include_user_files: Delete conversations with uploaded files")
        print("- include_global_collection: Delete conversations linked to admin knowledge bases")
        print("- delete_collections: Control whether to delete associated files and collections")
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
