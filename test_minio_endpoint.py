#!/usr/bin/env python3
"""
Test script for the enhanced /api/admin/files/minio endpoint
"""

import requests
import json
from typing import Dict, Any

def test_minio_endpoint():
    """Test the enhanced minio endpoint"""
    
    # Configuration - adjust these values as needed
    BASE_URL = "http://localhost:8000"  # Adjust to your API URL
    USERNAME = "admin"  # Adjust to your admin username
    PASSWORD = "admin"  # Adjust to your admin password
    
    # First, authenticate to get a token
    auth_response = requests.post(
        f"{BASE_URL}/api/auth/login",
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
    
    print("=== Testing /api/admin/files/minio endpoint ===")
    
    # Test the minio endpoint
    minio_response = requests.get(
        f"{BASE_URL}/api/admin/files/minio?prefix=admin",
        headers=headers
    )
    
    if minio_response.status_code != 200:
        print(f"Minio endpoint failed: {minio_response.status_code}")
        print(minio_response.text)
        return
    
    minio_files = minio_response.json()
    print(f"Found {len(minio_files)} files in MinIO")
    
    # Test the regular files endpoint for comparison
    files_response = requests.get(
        f"{BASE_URL}/api/admin/files/",
        headers=headers
    )
    
    if files_response.status_code != 200:
        print(f"Files endpoint failed: {files_response.status_code}")
        print(files_response.text)
        return
    
    regular_files = files_response.json()
    print(f"Found {len(regular_files)} files in database")
    
    print("\n=== Comparison ===")
    
    # Compare the structures
    if minio_files:
        print("\nSample MinIO endpoint response:")
        print(json.dumps(minio_files[0], indent=2, default=str))
    
    if regular_files:
        print("\nSample regular files endpoint response:")
        print(json.dumps(regular_files[0], indent=2, default=str))
    
    # Check for orphaned files
    orphaned_files = [f for f in minio_files if f.get("is_orphaned")]
    if orphaned_files:
        print(f"\nFound {len(orphaned_files)} orphaned files (exist in MinIO but not in database)")
        for orphaned in orphaned_files:
            print(f"  - {orphaned.get('name', 'Unknown')}")
    else:
        print("\nNo orphaned files found")
    
    # Check for files with rich information
    rich_files = [f for f in minio_files if not f.get("is_orphaned")]
    print(f"\nFound {len(rich_files)} files with rich database information")
    
    print("\n=== Test completed successfully! ===")

if __name__ == "__main__":
    test_minio_endpoint() 