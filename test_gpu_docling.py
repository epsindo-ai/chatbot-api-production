#!/usr/bin/env python3
"""
Test script to debug GPU usage in Docling
"""
import os
import logging
import sys

# Set up logging to see Docling internal messages
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    handlers=[logging.StreamHandler()]
)

print("=== GPU DOCLING TEST ===")

# Test 1: Check PyTorch
print("\n1. PyTorch Check:")
try:
    import torch
    print(f"✓ PyTorch version: {torch.__version__}")
    print(f"✓ CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"✓ GPU count: {torch.cuda.device_count()}")
        print(f"✓ Current device: {torch.cuda.current_device()}")
        print(f"✓ GPU name: {torch.cuda.get_device_name(0)}")
except Exception as e:
    print(f"✗ PyTorch error: {e}")

# Test 2: Check Docling AcceleratorDevice options
print("\n2. Docling AcceleratorDevice:")
try:
    from docling.datamodel.pipeline_options import AcceleratorDevice, AcceleratorOptions
    print(f"✓ Available devices: {list(AcceleratorDevice)}")
    print(f"✓ AUTO: {AcceleratorDevice.AUTO}")
    print(f"✓ CUDA: {AcceleratorDevice.CUDA}")
    print(f"✓ CPU: {AcceleratorDevice.CPU}")
except Exception as e:
    print(f"✗ AcceleratorDevice error: {e}")

# Test 3: Test different accelerator configurations
print("\n3. Testing AcceleratorOptions:")
test_devices = [AcceleratorDevice.AUTO, AcceleratorDevice.CUDA, AcceleratorDevice.CPU]

for device in test_devices:
    try:
        accel_options = AcceleratorOptions(device=device)
        print(f"✓ {device.value}: Created AcceleratorOptions successfully")
        print(f"  Device: {accel_options.device}")
        print(f"  Device value: {accel_options.device.value}")
    except Exception as e:
        print(f"✗ {device.value}: Error creating AcceleratorOptions: {e}")

# Test 4: Test PdfPipelineOptions with different devices
print("\n4. Testing PdfPipelineOptions:")
try:
    from docling.datamodel.pipeline_options import PdfPipelineOptions, EasyOcrOptions, TableStructureOptions, TableFormerMode
    
    for device in [AcceleratorDevice.AUTO, AcceleratorDevice.CUDA]:
        try:
            pipeline_options = PdfPipelineOptions(
                artifacts_path="/root/.cache/docling/models",
                do_ocr=True,
                do_table_structure=True,
                ocr_options=EasyOcrOptions(lang=["en"]),
                table_structure_options=TableStructureOptions(
                    do_cell_matching=True,
                    mode=TableFormerMode.ACCURATE
                ),
                accelerator_options=AcceleratorOptions(device=device)
            )
            print(f"✓ {device.value}: PdfPipelineOptions created successfully")
            print(f"  Accelerator device: {pipeline_options.accelerator_options.device.value}")
        except Exception as e:
            print(f"✗ {device.value}: PdfPipelineOptions error: {e}")
            
except Exception as e:
    print(f"✗ PdfPipelineOptions import error: {e}")

print("\n=== TEST COMPLETE ===")
