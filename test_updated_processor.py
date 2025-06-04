#!/usr/bin/env python3
"""
Test the updated document processor with GPU configuration
"""
import sys
import os
sys.path.append('/app')

from app.services.document_processor import DoclingProcessor
import logging

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s'
)

print("=== TESTING UPDATED DOCUMENT PROCESSOR ===")

try:
    print("\n1. Initializing DoclingProcessor with GPU enabled...")
    processor = DoclingProcessor(use_gpu=True)
    print("✓ Processor initialized successfully")
    
    print(f"\n2. Processor configuration:")
    print(f"   use_gpu: {processor.use_gpu}")
    print(f"   device: {processor.device}")
    print(f"   device value: {processor.device.value}")
    
    # Check the actual pipeline options
    print(f"\n3. Pipeline options:")
    accel_opts = processor.pdf_pipeline_options.accelerator_options
    print(f"   accelerator_options.device: {accel_opts.device}")
    print(f"   accelerator_options.device.value: {accel_opts.device.value}")
    
    print("\n4. Testing device decision function:")
    from docling.utils.accelerator_utils import decide_device
    decided = decide_device(processor.device.value)
    print(f"   decide_device('{processor.device.value}') -> '{decided}'")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n=== TEST COMPLETE ===")
