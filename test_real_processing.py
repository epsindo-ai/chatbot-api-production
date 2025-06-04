#!/usr/bin/env python3
"""
Test document processing with a real PDF to see GPU usage
"""
import sys
import os
sys.path.append('/app')

from app.services.document_processor import DoclingProcessor
import logging

# Set up detailed logging to catch all Docling internal messages
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s'
)

print("=== TESTING DOCUMENT PROCESSING WITH GPU ===")

# Check if we have the DGX-H200.pdf file
pdf_file = "/app/DGX-H200.pdf"
if not os.path.exists(pdf_file):
    print(f"✗ PDF file not found: {pdf_file}")
    exit(1)

print(f"✓ Found PDF file: {pdf_file} ({os.path.getsize(pdf_file)} bytes)")

try:
    print("\n1. Initializing processor...")
    processor = DoclingProcessor(use_gpu=True)
    
    print(f"\n2. Processing document...")
    print("   (Watch for 'Accelerator device' messages in the logs)")
    
    # Process just the first few pages to save time
    docs = processor.process_files([pdf_file])
    
    print(f"\n3. Results:")
    print(f"   Documents created: {len(docs)}")
    if docs:
        print(f"   First doc length: {len(docs[0].page_content)} chars")
        print(f"   Sample content: {docs[0].page_content[:200]}...")
    
except Exception as e:
    print(f"✗ Error during processing: {e}")
    import traceback
    traceback.print_exc()

print("\n=== TEST COMPLETE ===")
