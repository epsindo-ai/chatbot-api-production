#!/usr/bin/env python3
"""
Final test of the complete document processor with GPU
"""
import sys
import os
sys.path.append('/app')

from app.services.document_processor import DoclingProcessor
import logging

# Set up logging to catch accelerator messages
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s'
)

print("=== FINAL GPU TEST WITH CORRECTED PROCESSOR ===")

pdf_file = "/app/DGX-H200.pdf"

try:
    print("\n1. Initializing processor with GPU enabled...")
    processor = DoclingProcessor(use_gpu=True)
    
    print(f"\n2. Processing document (this will show GPU usage)...")
    docs = processor.process_files([pdf_file])
    
    print(f"\n3. Results:")
    print(f"   Documents created: {len(docs)}")
    if docs:
        print(f"   First document length: {len(docs[0].page_content)} chars")
        print(f"   Sample content: {docs[0].page_content[:150]}...")
        print(f"   Metadata keys: {list(docs[0].metadata.keys())}")
    
    print("\n✓ GPU processing completed successfully!")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n=== TEST COMPLETE ===")
