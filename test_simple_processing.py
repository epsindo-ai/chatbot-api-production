#!/usr/bin/env python3
"""
Test document processing without chunking to focus on GPU usage
"""
import sys
import os
sys.path.append('/app')

import logging
from langchain_docling.loader import ExportType
from langchain_docling import DoclingLoader
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

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s'
)

print("=== TESTING DOCUMENT PROCESSING WITHOUT CHUNKING ===")

pdf_file = "/app/DGX-H200.pdf"
if not os.path.exists(pdf_file):
    print(f"✗ PDF file not found: {pdf_file}")
    exit(1)

try:
    print("\n1. Setting up GPU-enabled pipeline...")
    
    # Create pipeline options with AUTO device
    pdf_options = PdfPipelineOptions(
        artifacts_path="/root/.cache/docling/models",
        do_ocr=False,  # Disable OCR to focus on core parsing
        do_table_structure=False,  # Disable table structure for now
        accelerator_options=AcceleratorOptions(device=AcceleratorDevice.AUTO)
    )
    
    print(f"   Pipeline device: {pdf_options.accelerator_options.device.value}")
    
    # Check what device is decided
    from docling.utils.accelerator_utils import decide_device
    decided = decide_device(pdf_options.accelerator_options.device.value)
    print(f"   Decided device: {decided}")
    
    print("\n2. Creating DocumentConverter...")
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_options)
        }
    )
    
    print("\n3. Creating DoclingLoader without chunking...")
    loader = DoclingLoader(
        file_path=[pdf_file],
        converter=converter,
        export_type=ExportType.MARKDOWN,  # No chunking
    )
    
    print("\n4. Processing document...")
    print("   (Watch for GPU/CPU device messages)")
    docs = loader.load()
    
    print(f"\n5. Results:")
    print(f"   Documents: {len(docs)}")
    if docs:
        print(f"   Content length: {len(docs[0].page_content)} chars")
        print(f"   Sample: {docs[0].page_content[:100]}...")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n=== TEST COMPLETE ===")
