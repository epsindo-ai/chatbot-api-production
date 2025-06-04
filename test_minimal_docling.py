#!/usr/bin/env python3
"""
Minimal test to see actual GPU usage in DocumentConverter
"""
import os
import logging
import tempfile

# Enable all logging to see what's happening
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s'
)

print("=== MINIMAL DOCLING GPU TEST ===")

try:
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import (
        AcceleratorDevice,
        AcceleratorOptions,
        PdfPipelineOptions,
        EasyOcrOptions,
        TableStructureOptions,
        TableFormerMode
    )
    
    print("\n1. Creating PdfPipelineOptions with AUTO device...")
    pdf_options = PdfPipelineOptions(
        artifacts_path="/root/.cache/docling/models",
        do_ocr=False,  # Disable OCR for faster testing
        do_table_structure=False,  # Disable table structure for faster testing
        accelerator_options=AcceleratorOptions(device=AcceleratorDevice.AUTO)
    )
    print(f"✓ Created with device: {pdf_options.accelerator_options.device.value}")
    
    print("\n2. Creating DocumentConverter...")
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_options)
        }
    )
    print("✓ DocumentConverter created successfully")
    
    print("\n3. Check what device is actually being used...")
    # The logs should show which device Docling actually selects
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n=== TEST COMPLETE ===")
