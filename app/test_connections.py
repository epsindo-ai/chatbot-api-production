#!/usr/bin/env python3
"""
Connection Test Script

This script tests connectivity to all services used by the RAG-based chatbot:
- PostgreSQL Database
- MinIO Object Storage
- Milvus Vector Database
- vLLM API
- Infinity Embeddings

Run this script to verify that all services are accessible before starting the application.
"""

import sys
import time
import json
from typing import Dict, Any
import os

# Add the app directory to the path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.utils.infinity_embedder import InfinityEmbedder
from app.services.minio_service import MinioService

def print_result(name: str, status: bool, details: Dict[str, Any] = None) -> None:
    """Print a formatted test result."""
    status_str = "\033[92m✓ PASS\033[0m" if status else "\033[91m✗ FAIL\033[0m"
    print(f"{status_str} {name}")
    if details:
        for key, value in details.items():
            print(f"  - {key}: {value}")
    print()

def test_postgres_connection() -> bool:
    """Test connection to PostgreSQL database."""
    print("\n=== Testing PostgreSQL Database Connection ===")
    try:
        # Create engine
        engine = create_engine(settings.DATABASE_URL)
        
        # Try to execute a simple query
        with engine.connect() as connection:
            result = connection.execute(text("SELECT version()"))
            version = result.scalar()
        
        print_result("PostgreSQL Connection", True, {
            "URL": settings.DATABASE_URL.replace(settings.POSTGRES_PASSWORD, "****"),
            "Version": version
        })
        return True
    except SQLAlchemyError as e:
        print_result("PostgreSQL Connection", False, {
            "URL": settings.DATABASE_URL.replace(settings.POSTGRES_PASSWORD, "****"),
            "Error": str(e)
        })
        return False

def test_minio_connection() -> bool:
    """Test connection to MinIO object storage."""
    print("\n=== Testing MinIO Connection ===")
    try:
        # Initialize MinIO service
        minio_service = MinioService()
        
        # Check if bucket exists
        bucket_exists = minio_service.client.bucket_exists(settings.MINIO_DEFAULT_BUCKET)
        
        if not bucket_exists:
            # Create bucket if it doesn't exist
            minio_service.client.make_bucket(settings.MINIO_DEFAULT_BUCKET)
            print(f"  - Created bucket: {settings.MINIO_DEFAULT_BUCKET}")
            
        # List buckets
        buckets = minio_service.client.list_buckets()
        bucket_names = [bucket.name for bucket in buckets]
        
        print_result("MinIO Connection", True, {
            "Endpoint": settings.MINIO_ENDPOINT,
            "Default Bucket": settings.MINIO_DEFAULT_BUCKET,
            "Bucket Exists": bucket_exists,
            "Available Buckets": bucket_names
        })
        return True
    except Exception as e:
        print_result("MinIO Connection", False, {
            "Endpoint": settings.MINIO_ENDPOINT,
            "Error": str(e)
        })
        return False

def test_milvus_connection() -> bool:
    """Test connection to Milvus vector database."""
    print("\n=== Testing Milvus Connection ===")
    try:
        # Import here to avoid import errors if Milvus is not installed
        from pymilvus import connections, utility
        
        # Connect to Milvus
        connections.connect(uri=settings.MILVUS_URI)
        
        # Get Milvus version
        version = utility.get_server_version()
        
        # List collections
        collections = utility.list_collections()
        
        print_result("Milvus Connection", True, {
            "URI": settings.MILVUS_URI,
            "Version": version,
            "Collections": collections if collections else "No collections found"
        })
        return True
    except Exception as e:
        print_result("Milvus Connection", False, {
            "URI": settings.MILVUS_URI,
            "Error": str(e)
        })
        return False

def test_vllm() -> bool:
    """Test connection to vLLM API."""
    print("\n=== Testing vLLM API ===")
    try:
        import requests
        
        # Prepare test prompt
        prompt = {"prompt": "Hello, this is a test. Please respond with a short message.", "max_tokens": 10}
        
        # Make request to LLM API
        start_time = time.time()
        response = requests.post(
            f"{settings.OPENAI_API_BASE}/chat/completions",
            headers={"Content-Type": "application/json"},
            json={
                "model": settings.LLM_MODEL,
                "messages": [{"role": "user", "content": "Say hello for a connection test"}],
                "max_tokens": 10
            },
            timeout=10
        )
        end_time = time.time()
        
        if response.status_code == 200:
            data = response.json()
            print_result("vLLM API", True, {
                "Base URL": settings.OPENAI_API_BASE,
                "Model": settings.LLM_MODEL,
                "Response": data["choices"][0]["message"]["content"] if "choices" in data else "No content",
                "Latency (ms)": round((end_time - start_time) * 1000, 2)
            })
            return True
        else:
            print_result("vLLM API", False, {
                "Base URL": settings.OPENAI_API_BASE,
                "Status Code": response.status_code,
                "Response": response.text
            })
            return False
    except Exception as e:
        print_result("vLLM API", False, {
            "Base URL": settings.OPENAI_API_BASE,
            "Error": str(e)
        })
        return False

def test_infinity_embeddings() -> bool:
    """Test connection to Infinity Embeddings API."""
    print("\n=== Testing Infinity Embeddings ===")
    try:
        # Initialize embedder
        embedder = InfinityEmbedder(
            model=settings.INFINITY_EMBEDDINGS_MODEL,
            infinity_api_url=settings.INFINITY_API_URL
        )
        
        # Get health information
        health_info = embedder.health_check()
        
        if health_info["status"] == "healthy":
            # Try to embed a test string
            test_text = "This is a test sentence for embeddings."
            embedding = embedder.embed_query(test_text)
            
            print_result("Infinity Embeddings", True, {
                "API URL": settings.INFINITY_API_URL,
                "Model": settings.INFINITY_EMBEDDINGS_MODEL,
                "Embedding Dimension": len(embedding),
                "Latency (ms)": health_info["latency_ms"]
            })
            return True
        else:
            print_result("Infinity Embeddings", False, {
                "API URL": settings.INFINITY_API_URL,
                "Error": health_info.get("error", "Unknown error")
            })
            return False
    except Exception as e:
        print_result("Infinity Embeddings", False, {
            "API URL": settings.INFINITY_API_URL,
            "Error": str(e)
        })
        return False

def run_all_tests():
    """Run all connection tests and summarize results."""
    print("\n========================================")
    print("        CONNECTIVITY TEST SUITE         ")
    print("========================================\n")
    
    results = {}
    
    # Run tests and collect results
    results["PostgreSQL"] = test_postgres_connection()
    results["MinIO"] = test_minio_connection()
    results["Milvus"] = test_milvus_connection()
    results["vLLM"] = test_vllm()
    results["Infinity Embeddings"] = test_infinity_embeddings()
    
    # Print summary
    print("\n========================================")
    print("             TEST SUMMARY               ")
    print("========================================")
    
    all_passed = True
    for service, success in results.items():
        status_str = "\033[92m✓ PASS\033[0m" if success else "\033[91m✗ FAIL\033[0m"
        print(f"{status_str} {service}")
        if not success:
            all_passed = False
    
    print("\n========================================")
    if all_passed:
        print("\033[92mAll tests passed! System is ready.\033[0m")
    else:
        print("\033[91mSome tests failed. Please check the issues above.\033[0m")
    print("========================================\n")

if __name__ == "__main__":
    run_all_tests() 