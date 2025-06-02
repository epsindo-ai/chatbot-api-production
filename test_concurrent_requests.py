#!/usr/bin/env python3
"""
Test script to verify that the chatbot API can handle concurrent requests without blocking.
This script sends multiple requests simultaneously to test for blocking issues.
"""

import asyncio
import aiohttp
import time
import json
from typing import List, Dict, Any

# Configuration
API_BASE_URL = "http://localhost:35430"
TEST_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJpbGhhbSIsImV4cCI6MTc0ODI0Mzg1N30.Efxck_Ijpr-PtGOFG7Fwv4bea65eEAYZ89cyAowm9Ow"  # Replace with actual JWT token

async def make_request(session: aiohttp.ClientSession, endpoint: str, method: str = "GET", data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Make an async HTTP request."""
    headers = {
        "Authorization": f"Bearer {TEST_TOKEN}",
        "Content-Type": "application/json"
    }
    
    url = f"{API_BASE_URL}{endpoint}"
    start_time = time.time()
    
    try:
        if method == "GET":
            async with session.get(url, headers=headers) as response:
                result = await response.json()
        elif method == "POST":
            async with session.post(url, headers=headers, json=data) as response:
                result = await response.json()
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        end_time = time.time()
        return {
            "endpoint": endpoint,
            "method": method,
            "status": response.status,
            "duration": end_time - start_time,
            "success": True,
            "response": result
        }
    except Exception as e:
        end_time = time.time()
        return {
            "endpoint": endpoint,
            "method": method,
            "status": None,
            "duration": end_time - start_time,
            "success": False,
            "error": str(e)
        }

async def test_concurrent_requests():
    """Test multiple concurrent requests to verify no blocking occurs."""
    print("Testing concurrent requests to verify no blocking...")
    
    # Define test requests
    test_requests = [
        # Health checks (should be fast)
        ("/health", "GET", None),
        ("/api/chat/system/health", "GET", None),
        ("/api/chat/embeddings/health", "GET", None),
        
        # Chat requests (potentially slower)
        ("/api/chat/", "POST", {
            "message": "Hello, this is a test message",
            "conversation_id": "test-conversation-1",
            "meta_data": {}
        }),
        ("/api/chat/", "POST", {
            "message": "Another test message",
            "conversation_id": "test-conversation-2", 
            "meta_data": {}
        }),
        
        # File status checks
        ("/api/chat/file-status/test-conversation-1", "GET", None),
        ("/api/chat/file-status/test-conversation-2", "GET", None),
        
        # Conversation lists
        ("/api/chat/conversations", "GET", None),
    ]
    
    async with aiohttp.ClientSession() as session:
        # Send all requests concurrently
        start_time = time.time()
        tasks = [
            make_request(session, endpoint, method, data)
            for endpoint, method, data in test_requests
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        print(f"\nCompleted {len(test_requests)} concurrent requests in {total_time:.2f} seconds")
        print("\nResults:")
        print("-" * 80)
        
        successful_requests = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"{i+1}. ERROR: {result}")
            else:
                status_indicator = "✓" if result["success"] else "✗"
                print(f"{i+1}. {status_indicator} {result['method']} {result['endpoint']}")
                print(f"   Status: {result['status']}, Duration: {result['duration']:.2f}s")
                if not result["success"]:
                    print(f"   Error: {result['error']}")
                else:
                    successful_requests += 1
                print()
        
        print(f"Success rate: {successful_requests}/{len(test_requests)} ({successful_requests/len(test_requests)*100:.1f}%)")
        
        # Check if any request took unusually long (indicating potential blocking)
        max_duration = max(r["duration"] for r in results if isinstance(r, dict) and r["success"])
        min_duration = min(r["duration"] for r in results if isinstance(r, dict) and r["success"])
        
        print(f"Duration range: {min_duration:.2f}s - {max_duration:.2f}s")
        
        if max_duration > 10:  # If any request takes more than 10 seconds
            print("⚠️  WARNING: Some requests took unusually long, which may indicate blocking issues")
        else:
            print("✓ All requests completed in reasonable time - no obvious blocking detected")

async def test_file_upload_concurrency():
    """Test file upload endpoint with concurrent requests."""
    print("\nTesting file upload concurrency...")
    
    # Create test file content
    test_file_content = "This is a test file for concurrent upload testing.\n" * 100
    
    async with aiohttp.ClientSession() as session:
        # Simulate multiple file uploads
        upload_tasks = []
        for i in range(3):
            # Create form data
            data = aiohttp.FormData()
            data.add_field('conversation_id', f'test-upload-conversation-{i}')
            data.add_field('files', test_file_content.encode(), 
                          filename=f'test_file_{i}.txt', 
                          content_type='text/plain')
            
            headers = {"Authorization": f"Bearer {TEST_TOKEN}"}
            
            task = session.post(
                f"{API_BASE_URL}/api/chat/upload-file",
                headers=headers,
                data=data
            )
            upload_tasks.append(task)
        
        start_time = time.time()
        try:
            responses = await asyncio.gather(*upload_tasks, return_exceptions=True)
            total_time = time.time() - start_time
            
            print(f"Completed {len(upload_tasks)} concurrent file uploads in {total_time:.2f} seconds")
            
            for i, response in enumerate(responses):
                if isinstance(response, Exception):
                    print(f"Upload {i+1}: ERROR - {response}")
                else:
                    print(f"Upload {i+1}: Status {response.status}")
                    if response.status == 200:
                        result = await response.json()
                        print(f"  Files processed: {len(result)}")
                    response.close()
                    
        except Exception as e:
            print(f"Error during concurrent uploads: {e}")

if __name__ == "__main__":
    print("Chatbot API Concurrency Test")
    print("=" * 50)
    print("This script tests whether the API can handle concurrent requests without blocking.")
    print("Make sure the API server is running on http://localhost:35430")
    print("You may need to update the TEST_TOKEN variable with a valid JWT token.")
    print()
    
    try:
        asyncio.run(test_concurrent_requests())
        asyncio.run(test_file_upload_concurrency())
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"\nTest failed with error: {e}") 