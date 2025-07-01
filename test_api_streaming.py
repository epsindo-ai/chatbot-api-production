#!/usr/bin/env python3
"""
API Endpoint Streaming Test

This script tests the actual streaming chat endpoint to verify if the issue
is in the API layer or truly in the frontend.
"""

import asyncio
import json
import httpx
import time
from typing import AsyncGenerator

async def test_streaming_endpoint():
    """Test the actual streaming chat API endpoint."""
    print("🔍 Testing Streaming Chat API Endpoint")
    print("="*50)
    
    # API endpoint configuration
    base_url = "http://172.23.1.62:35430"  # Update to match your server
    endpoint = f"{base_url}/api/chat/stream"
    
    # Test payload
    payload = {
        "message": "Say hello and count to 3",
        "conversation_id": None,
        "meta_data": {}
    }
    
    # You'll need to replace this with a real token from your system
    # For testing, you might need to create a test user and get their token
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc1MTAxODQ5OX0.GPlNIF8TOSxLcUCDh7mc2AlgFkIpmb4ttGG_rZTfCc0"
    }
    
    print(f"📡 Endpoint: {endpoint}")
    print(f"📦 Payload: {json.dumps(payload, indent=2)}")
    print("🚀 Starting streaming test...\n")
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            start_time = time.time()
            token_count = 0
            
            # Make streaming request
            async with client.stream(
                "POST",
                endpoint,
                json=payload,
                headers=headers
            ) as response:
                
                print(f"📊 HTTP Status: {response.status_code}")
                print(f"📋 Headers: {dict(response.headers)}")
                print("🔄 Streaming response:\n")
                
                if response.status_code != 200:
                    error_text = await response.aread()
                    print(f"❌ Error: {error_text.decode()}")
                    return False
                
                # Read streaming response
                async for chunk in response.aiter_text():
                    if chunk.strip():
                        try:
                            # Parse JSON chunk
                            data = json.loads(chunk.strip())
                            
                            if "status" in data:
                                status = data["status"]
                                
                                if status == "token":
                                    token_count += 1
                                    token = data.get("token", "")
                                    print(f"Token {token_count:3d}: '{token}'", end="", flush=True)
                                    
                                elif status == "info":
                                    print(f"\n📢 Info: {data.get('message', '')}")
                                    
                                elif status == "done":
                                    elapsed = time.time() - start_time
                                    print(f"\n\n✅ Streaming completed!")
                                    print(f"📊 Total tokens: {token_count}")
                                    print(f"⏱️  Time taken: {elapsed:.2f} seconds")
                                    print(f"🔄 Conversation ID: {data.get('conversation_id', 'N/A')}")
                                    print(f"🤖 Used RAG: {data.get('used_rag', False)}")
                                    return True
                                    
                                elif status == "error":
                                    print(f"\n❌ Stream Error: {data.get('message', 'Unknown error')}")
                                    return False
                                    
                        except json.JSONDecodeError as e:
                            print(f"\n⚠️  JSON Parse Error: {e}")
                            print(f"Raw chunk: {repr(chunk)}")
                            
            print("\n⚠️  Stream ended without 'done' status")
            return False
                            
    except httpx.ConnectError:
        print("❌ Connection Error: Cannot connect to the API server")
        print("   Make sure the FastAPI server is running on the correct port")
        return False
        
    except httpx.TimeoutException:
        print("❌ Timeout Error: API server took too long to respond")
        return False
        
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        return False

async def test_non_streaming_endpoint():
    """Test the non-streaming chat endpoint for comparison."""
    print("\n🔍 Testing Non-Streaming Chat API Endpoint")
    print("="*50)
    
    base_url = "http://172.23.1.62:35430"
    endpoint = f"{base_url}/api/chat/"
    
    payload = {
        "message": "Say hello in 2 words",
        "conversation_id": None,
        "meta_data": {}
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc1MTAxODQ5OX0.GPlNIF8TOSxLcUCDh7mc2AlgFkIpmb4ttGG_rZTfCc0"
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            start_time = time.time()
            
            response = await client.post(
                endpoint,
                json=payload,
                headers=headers
            )
            
            elapsed = time.time() - start_time
            
            print(f"📊 HTTP Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Response received in {elapsed:.2f} seconds")
                print(f"📝 Response: {data.get('response', 'N/A')}")
                print(f"🔄 Conversation ID: {data.get('conversation_id', 'N/A')}")
                return True
            else:
                print(f"❌ Error: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def print_troubleshooting_guide():
    """Print troubleshooting suggestions."""
    print("\n" + "="*60)
    print("🔧 TROUBLESHOOTING GUIDE")
    print("="*60)
    
    print("\n📋 If the API tests fail:")
    print("1. Check if FastAPI server is running:")
    print("   uvicorn app.main:app --host 0.0.0.0 --port 8000")
    print()
    print("2. Check server logs for errors:")
    print("   Look for any exceptions in the FastAPI console output")
    print()
    print("3. Test with authentication:")
    print("   - Create a test user via API or admin panel")
    print("   - Get an auth token")
    print("   - Update the headers in this script")
    print()
    print("4. Check network connectivity:")
    print("   curl -X GET http://localhost:8000/health")
    print()
    
    print("📋 If the API tests pass but frontend fails:")
    print("1. Check browser network tab:")
    print("   - Look for failed requests")
    print("   - Check if requests are being made")
    print("   - Verify request format")
    print()
    print("2. Check frontend JavaScript console:")
    print("   - Look for JavaScript errors")
    print("   - Verify fetch/streaming implementation")
    print()
    print("3. Check CORS settings:")
    print("   - Ensure frontend origin is allowed")
    print("   - Check preflight OPTIONS requests")
    print()
    print("4. Test with curl:")
    print('   curl -X POST http://localhost:8000/api/chat/stream \\')
    print('        -H "Content-Type: application/json" \\')
    print('        -d \'{"message":"test","conversation_id":null}\'')

async def main():
    """Run all tests."""
    print("🧪 API Streaming Test Suite")
    print("="*60)
    
    # Test non-streaming first (simpler)
    non_streaming_ok = await test_non_streaming_endpoint()
    
    # Test streaming
    streaming_ok = await test_streaming_endpoint()
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    print(f"Non-streaming API: {'✅ PASS' if non_streaming_ok else '❌ FAIL'}")
    print(f"Streaming API:     {'✅ PASS' if streaming_ok else '❌ FAIL'}")
    
    if non_streaming_ok and streaming_ok:
        print("\n🎉 Backend API is working correctly!")
        print("   If users report streaming issues, the problem is likely:")
        print("   • Frontend implementation")
        print("   • Network connectivity")
        print("   • Browser compatibility")
        print("   • CORS configuration")
    elif non_streaming_ok and not streaming_ok:
        print("\n⚠️  Non-streaming works but streaming fails")
        print("   Check the streaming implementation in unified_chat.py")
    else:
        print("\n❌ API is not responding correctly")
        print("   Check server status and configuration")
    
    print_troubleshooting_guide()

if __name__ == "__main__":
    asyncio.run(main())
