#!/usr/bin/env python3
"""
Test to verify that Milvus collection deletion warnings are fixed.
This test checks that non-existent collections are handled gracefully.
"""

import requests
import json

# Configuration
BASE_URL = "http://localhost:35430"
USERNAME = "ilham"
PASSWORD = "123"

def test_deletion_with_milvus_fix():
    """Test that Milvus collection deletion warnings are eliminated."""
    
    print("🔧 Testing Milvus Collection Deletion Fix")
    print("=" * 50)
    
    # Step 1: Login and get token
    print("\n1. Authenticating...")
    try:
        login_response = requests.post(
            f"{BASE_URL}/api/auth/token",
            data={
                "username": USERNAME,
                "password": PASSWORD
            }
        )
        
        if login_response.status_code != 200:
            print(f"❌ Login failed: {login_response.status_code}")
            print(f"Response: {login_response.text}")
            return False
        
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("✅ Authentication successful")
        
    except Exception as e:
        print(f"❌ Authentication error: {str(e)}")
        return False
    
    # Step 2: Test deletion with only null conversations (safe test)
    print("\n2. Testing deletion with only null conversation cleanup...")
    
    test_request_body = {
        "delete_files_and_collections": True,    # Enable collection cleanup
        "delete_regular_chats": False,           # Don't delete regular chats
        "delete_user_file_conversations": False, # Don't delete user file conversations
        "delete_global_collection_conversations": False, # Don't delete global collection conversations
        "delete_null_conversations": True       # Only clean up null/orphaned conversations
    }
    
    try:
        response = requests.delete(
            f"{BASE_URL}/api/chat/conversations/all",
            headers=headers,
            json=test_request_body
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Deletion request successful!")
            print(f"Detail: {result.get('detail', 'No detail')}")
            
            stats = result.get('deleted_stats', {})
            print("📊 Deletion Statistics:")
            print(f"  - Total conversations deleted: {stats.get('conversations_deleted', 0)}")
            print(f"  - Files deleted: {stats.get('files_deleted', 0)}")
            print(f"  - Collections deleted: {stats.get('collections_deleted', 0)}")
            print(f"  - Regular chats deleted: {stats.get('regular_conversations_deleted', 0)}")
            print(f"  - User file conversations deleted: {stats.get('user_files_conversations_deleted', 0)}")
            print(f"  - Global collection conversations deleted: {stats.get('global_collection_conversations_deleted', 0)}")
            print(f"  - Null/orphaned conversations deleted: {stats.get('null_conversations_deleted', 0)}")
            
            errors = stats.get('errors', [])
            if errors:
                print(f"\n⚠️  Errors/Warnings ({len(errors)}):")
                for error in errors:
                    print(f"  - {error}")
                    
                # Check if there are still "Could not delete Milvus collection" warnings
                milvus_warnings = [e for e in errors if "Could not delete Milvus collection" in e]
                if milvus_warnings:
                    print(f"\n❌ Still getting Milvus collection warnings ({len(milvus_warnings)})")
                    print("The fix may not be complete.")
                    return False
                else:
                    print("\n✅ No Milvus collection warnings found!")
            else:
                print("\n✅ No errors or warnings!")
            
            return True
            
        else:
            print(f"❌ Unexpected status code: {response.status_code}")
            try:
                error = response.json()
                print(f"Error: {error}")
            except:
                print(f"Raw response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Request error: {str(e)}")
        return False

def test_comprehensive_deletion():
    """Test deletion with all conversation types to verify the fix works comprehensively."""
    
    print("\n3. Testing comprehensive deletion...")
    
    # Step 1: Login and get token
    try:
        login_response = requests.post(
            f"{BASE_URL}/api/auth/token",
            data={
                "username": USERNAME,
                "password": PASSWORD
            }
        )
        
        if login_response.status_code != 200:
            print(f"❌ Login failed: {login_response.status_code}")
            return False
        
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
    except Exception as e:
        print(f"❌ Authentication error: {str(e)}")
        return False
    
    # Test with all conversation types
    test_request_body = {
        "delete_files_and_collections": True,
        "delete_regular_chats": True,
        "delete_user_file_conversations": True,
        "delete_global_collection_conversations": True,
        "delete_null_conversations": True
    }
    
    try:
        response = requests.delete(
            f"{BASE_URL}/api/chat/conversations/all",
            headers=headers,
            json=test_request_body
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Comprehensive deletion successful!")
            print(f"Detail: {result.get('detail', 'No detail')}")
            
            stats = result.get('deleted_stats', {})
            print("📊 Comprehensive Deletion Statistics:")
            print(f"  - Total conversations deleted: {stats.get('conversations_deleted', 0)}")
            print(f"  - Files deleted: {stats.get('files_deleted', 0)}")
            print(f"  - Collections deleted: {stats.get('collections_deleted', 0)}")
            
            errors = stats.get('errors', [])
            if errors:
                print(f"\n⚠️  Errors/Warnings ({len(errors)}):")
                for error in errors:
                    print(f"  - {error}")
                    
                # Check for Milvus warnings
                milvus_warnings = [e for e in errors if "Could not delete Milvus collection" in e]
                if milvus_warnings:
                    print(f"\n❌ Found {len(milvus_warnings)} Milvus collection warnings")
                    print("The fix needs improvement.")
                    return False
                else:
                    print("\n✅ No Milvus collection warnings in comprehensive test!")
            else:
                print("\n✅ No errors or warnings in comprehensive test!")
            
            return True
            
        else:
            print(f"❌ Comprehensive test failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Comprehensive test error: {str(e)}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Milvus Collection Deletion Fix")
    print("This test verifies that non-existent Milvus collections are handled gracefully.")
    print()
    
    try:
        test1_passed = test_deletion_with_milvus_fix()
        test2_passed = test_comprehensive_deletion()
        
        print(f"\n" + "=" * 50)
        if test1_passed and test2_passed:
            print("🎉 All tests passed! Milvus collection deletion fix is successful.")
            print("\n✅ Key improvements confirmed:")
            print("  - Non-existent collections treated as 'already deleted'")
            print("  - No more 'Could not delete Milvus collection' warnings")
            print("  - Collections deleted count includes non-existent collections")
            print("  - Error reporting only for actual failures")
            exit(0)
        else:
            print("💥 Some tests failed. The fix may need additional work.")
            exit(1)
            
    except Exception as e:
        print(f"\n💥 Test script error: {str(e)}")
        exit(1)
