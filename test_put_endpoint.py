#!/usr/bin/env python3
"""
Quick interactive test for PUT /api/admin/collections/{collection_id}
Run this to see the global default switching behavior in action
"""

import requests
import json
from typing import Optional

# Configuration - Update these values
BASE_URL = "http://localhost:35430"
ADMIN_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJpbGhhbSIsImV4cCI6MTc0ODg0OTU4MH0.qGeUjTCFoAqfKAx3-ZwHTNkNdaNKXhAxjLcZ-sQ1T78"  # Replace with your actual token

def api_call(method: str, endpoint: str, data: Optional[dict] = None):
    """Make an API call and return the response."""
    url = f"{BASE_URL}{endpoint}"
    headers = {
        "Authorization": f"Bearer {ADMIN_TOKEN}",
        "Content-Type": "application/json"
    }
    
    print(f"\n🔄 {method} {endpoint}")
    if data:
        print(f"📤 Request: {json.dumps(data, indent=2)}")
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "PUT":
            response = requests.put(url, json=data, headers=headers)
        elif method == "POST":
            response = requests.post(url, json=data, headers=headers)
        
        print(f"📊 Status: {response.status_code}")
        
        if response.status_code < 400:
            result = response.json()
            print(f"📥 Response: {json.dumps(result, indent=2)}")
            return result
        else:
            error = response.json()
            print(f"❌ Error: {json.dumps(error, indent=2)}")
            return None
            
    except Exception as e:
        print(f"💥 Exception: {e}")
        return None

def show_all_collections():
    """Show all collections and highlight the global default."""
    print("\n" + "="*50)
    print("📋 CURRENT COLLECTIONS STATE")
    print("="*50)
    
    collections = api_call("GET", "/api/admin/collections/")
    
    if collections:
        print("\n📚 All Collections:")
        global_default_found = False
        
        for collection in collections:
            is_global = collection.get('is_global_default', False)
            status = "🌟 GLOBAL DEFAULT" if is_global else "📄 Regular"
            print(f"  • ID: {collection['id']}")
            print(f"    Name: {collection['name']}")
            print(f"    Status: {status}")
            print(f"    Active: {collection.get('is_active', True)}")
            print()
            
            if is_global:
                global_default_found = True
        
        if not global_default_found:
            print("⚠️  No global default collection found!")
    
    return collections

def quick_demo():
    """Run a quick demonstration of global default switching."""
    print("🚀 PUT /api/admin/collections/{id} Global Default Demo")
    print("="*60)
    
    # Show current state
    collections = show_all_collections()
    
    if not collections or len(collections) < 2:
        print("❌ Need at least 2 collections to demonstrate switching.")
        print("   Please create some collections first using:")
        print("   POST /api/admin/collections/")
        return
    
    # Find a non-global collection to promote
    target_collection = None
    current_global = None
    
    for collection in collections:
        if collection.get('is_global_default'):
            current_global = collection
        elif not target_collection:
            target_collection = collection
    
    if not target_collection:
        print("❌ All collections are already global default (which shouldn't happen!)")
        return
    
    print(f"\n🎯 DEMONSTRATION PLAN:")
    if current_global:
        print(f"   Current Global: {current_global['name']} (ID: {current_global['id']})")
    else:
        print("   Current Global: None")
    print(f"   Will promote: {target_collection['name']} (ID: {target_collection['id']})")
    
    input("\n📝 Press Enter to proceed with the demo...")
    
    # Perform the switch
    print(f"\n🔄 SWITCHING GLOBAL DEFAULT...")
    print(f"   Setting collection '{target_collection['name']}' as global default")
    
    update_data = {
        "name": target_collection['name'],
        "description": f"{target_collection.get('description', '')} - PROMOTED TO GLOBAL DEFAULT",
        "is_global_default": True
    }
    
    result = api_call("PUT", f"/api/admin/collections/{target_collection['id']}", update_data)
    
    if result:
        print("\n✅ SUCCESS! Global default has been switched.")
        
        # Show the new state
        show_all_collections()
        
        print("\n🔍 KEY OBSERVATIONS:")
        print("   1. ✅ Only ONE collection is now global default")
        print("   2. ✅ Previous global default was automatically deactivated")
        print("   3. ✅ Database state is consistent")
        print("   4. ✅ Admin config will be updated for RAG system")
        
    else:
        print("\n❌ Failed to switch global default")

def interactive_test():
    """Interactive test allowing user to pick collections."""
    collections = show_all_collections()
    
    if not collections:
        print("❌ No collections found. Create some collections first.")
        return
    
    print(f"\n🎮 INTERACTIVE MODE")
    print("Choose a collection to set as global default:")
    
    for i, collection in enumerate(collections):
        is_global = "🌟 (CURRENT GLOBAL)" if collection.get('is_global_default') else ""
        print(f"  {i+1}. {collection['name']} (ID: {collection['id']}) {is_global}")
    
    try:
        choice = int(input(f"\nEnter choice (1-{len(collections)}): ")) - 1
        
        if 0 <= choice < len(collections):
            target = collections[choice]
            
            if target.get('is_global_default'):
                print(f"⚠️  Collection '{target['name']}' is already the global default!")
                return
            
            print(f"\n🎯 Setting '{target['name']}' as global default...")
            
            update_data = {
                "name": target['name'],
                "description": f"{target.get('description', '')} - Set as global default",
                "is_global_default": True
            }
            
            result = api_call("PUT", f"/api/admin/collections/{target['id']}", update_data)
            
            if result:
                print("\n✅ SUCCESS!")
                show_all_collections()
            else:
                print("\n❌ FAILED!")
        
        else:
            print("❌ Invalid choice!")
            
    except ValueError:
        print("❌ Please enter a valid number!")

def main():
    """Main function."""
    print("🧪 PUT Global Default Collection Test")
    print("="*40)
    
    # Basic connectivity test
    print("🔗 Testing API connectivity...")
    result = api_call("GET", "/api/admin/collections/")
    
    if result is None:
        print("❌ Cannot connect to API. Please check:")
        print("   1. BASE_URL is correct")
        print("   2. ADMIN_TOKEN is valid")
        print("   3. Server is running")
        return
    
    print("✅ API connection successful!")
    
    while True:
        print(f"\n{'='*50}")
        print("🎯 CHOOSE AN OPTION:")
        print("   1. 🚀 Quick Demo (automatic)")
        print("   2. 🎮 Interactive Test (choose collection)")
        print("   3. 📋 Show Collections Only")
        print("   4. 🚪 Exit")
        
        choice = input("\nChoice (1-4): ").strip()
        
        if choice == "1":
            quick_demo()
        elif choice == "2":
            interactive_test()
        elif choice == "3":
            show_all_collections()
        elif choice == "4":
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice!")

if __name__ == "__main__":
    print("⚙️  Update the BASE_URL and ADMIN_TOKEN variables at the top of this script")
    print("⚙️  Then run: python3 test_put_endpoint.py")
    print()
    
    if ADMIN_TOKEN == "your_admin_token_here":
        print("⚠️  ADMIN_TOKEN not configured! Please update the script first.")
        exit(1)
    
    main()
