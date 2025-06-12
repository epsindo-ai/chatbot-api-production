#!/usr/bin/env python3
"""
Test script for the new user endpoint to delete all conversations
"""

import requests
import json
from typing import Dict, Any

def test_delete_all_user_conversations():
    """Test the new endpoint for users to delete all their conversations"""
    
    # Configuration - adjust these values as needed
    BASE_URL = "http://localhost:8000"  # Adjust to your API URL
    USERNAME = "ilham"  # Adjust to your username
    PASSWORD = "123"  # Adjust to your password
    
    # First, authenticate to get a token
    auth_response = requests.post(
        f"{BASE_URL}/api/auth/token",
        data={
            "username": USERNAME,
            "password": PASSWORD
        }
    )
    
    if auth_response.status_code != 200:
        print(f"Authentication failed: {auth_response.status_code}")
        print(auth_response.text)
        return
    
    token = auth_response.json().get("access_token")
    if not token:
        print("No access token received")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    print("=== Testing Delete All User Conversations Endpoint ===")
    
    # First, let's check what conversations the user currently has
    print("\n1. Checking current user conversations...")
    conversations_response = requests.get(
        f"{BASE_URL}/api/collections/",
        headers=headers
    )
    
    if conversations_response.status_code == 200:
        conversations = conversations_response.json()
        print(f"User currently has {len(conversations)} conversations with files")
        
        for conv in conversations[:3]:  # Show first 3
            print(f"  - Conversation ID: {conv.get('conversation_id')}")
            print(f"    Headline: {conv.get('headline', 'No headline')}")
            print(f"    Files: {conv.get('file_count', 0)}")
    else:
        print(f"Failed to get conversations: {conversations_response.status_code}")
        print(conversations_response.text)
    
    # Ask for confirmation before deletion
    print(f"\n2. This will delete ALL conversations and their files for user '{USERNAME}'")
    confirm = input("Are you sure you want to proceed? (yes/no): ").lower().strip()
    
    if confirm != 'yes':
        print("Operation cancelled.")
        return
    
    # Test the delete all conversations endpoint
    print("\n3. Deleting all user conversations...")
    delete_response = requests.delete(
        f"{BASE_URL}/api/collections/all",
        headers=headers,
        params={
            "delete_collections": "true"  # Also delete collections and files
        }
    )
    
    if delete_response.status_code == 200:
        result = delete_response.json()
        print("✅ Successfully deleted all conversations!")
        print(f"Response: {result.get('detail', 'No detail')}")
        
        if 'deleted_stats' in result:
            stats = result['deleted_stats']
            print(f"\nDeletion Statistics:")
            print(f"  - Conversations deleted: {stats.get('conversations_deleted', 0)}")
            print(f"  - Files deleted: {stats.get('files_deleted', 0)}")
            print(f"  - Collections deleted: {stats.get('collections_deleted', 0)}")
            
            if stats.get('errors'):
                print(f"  - Errors encountered: {len(stats['errors'])}")
                for i, error in enumerate(stats['errors'][:3]):  # Show first 3 errors
                    print(f"    {i+1}. {error}")
                if len(stats['errors']) > 3:
                    print(f"    ... and {len(stats['errors'])-3} more errors")
        
        print(f"\nFull response:")
        print(json.dumps(result, indent=2, default=str))
        
    else:
        print(f"❌ Failed to delete conversations: {delete_response.status_code}")
        print(delete_response.text)
        return
    
    # Verify that conversations are deleted
    print("\n4. Verifying deletion...")
    verify_response = requests.get(
        f"{BASE_URL}/api/collections/",
        headers=headers
    )
    
    if verify_response.status_code == 200:
        remaining_conversations = verify_response.json()
        print(f"User now has {len(remaining_conversations)} conversations with files")
        
        if len(remaining_conversations) == 0:
            print("✅ All conversations successfully deleted!")
        else:
            print("⚠️  Some conversations still remain:")
            for conv in remaining_conversations:
                print(f"  - Conversation ID: {conv.get('conversation_id')}")
                print(f"    Headline: {conv.get('headline', 'No headline')}")
    else:
        print(f"Failed to verify deletion: {verify_response.status_code}")
        print(verify_response.text)
    
    print("\n=== Test completed ===")

def test_delete_all_without_collections():
    """Test deleting conversations but keeping collections/files"""
    
    # Configuration - adjust these values as needed
    BASE_URL = "http://localhost:8000"  # Adjust to your API URL
    USERNAME = "ilham"  # Adjust to your username
    PASSWORD = "123"  # Adjust to your password
    
    # First, authenticate to get a token
    auth_response = requests.post(
        f"{BASE_URL}/api/auth/token",
        data={
            "username": USERNAME,
            "password": PASSWORD
        }
    )
    
    if auth_response.status_code != 200:
        print(f"Authentication failed: {auth_response.status_code}")
        return
    
    token = auth_response.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    
    print("=== Testing Delete Conversations Only (Keep Files/Collections) ===")
    
    # Test the delete all conversations endpoint without deleting collections
    delete_response = requests.delete(
        f"{BASE_URL}/api/collections/all",
        headers=headers,
        params={
            "delete_collections": "false"  # Keep collections and files
        }
    )
    
    if delete_response.status_code == 200:
        result = delete_response.json()
        print("✅ Successfully deleted conversations (kept files/collections)!")
        print(f"Response: {result.get('detail', 'No detail')}")
        print(f"\nFull response:")
        print(json.dumps(result, indent=2, default=str))
    else:
        print(f"❌ Failed to delete conversations: {delete_response.status_code}")
        print(delete_response.text)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--no-collections":
        test_delete_all_without_collections()
    else:
        test_delete_all_user_conversations()
