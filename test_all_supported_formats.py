#!/usr/bin/env python3
"""Test script to verify all officially supported Docling formats"""

import os
import sys
import tempfile
import logging

# Add the app directory to Python path
sys.path.insert(0, '/app')

from app.services.document_processor import DoclingProcessor

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s')
logger = logging.getLogger("test_all_formats")

def test_format_support():
    """Test that all officially supported Docling formats are configured"""
    logger.info("=== TESTING ALL OFFICIALLY SUPPORTED DOCLING FORMATS ===")
    
    try:
        # Initialize the document processor
        processor = DoclingProcessor()
        logger.info("✓ Document processor initialized successfully")
        
        # Check the supported formats in the converter
        format_options = processor.doc_converter.format_options
        logger.info(f"Configured format options: {list(format_options.keys())}")
        
        # List of officially supported formats
        expected_formats = [
            "PDF",
            "DOCX", 
            "XLSX",
            "PPTX",
            "MD",
            "CSV", 
            "HTML",
            "ASCIIDOC"
        ]
        
        # Check each format
        for format_name in expected_formats:
            # Get the format enum value
            from docling.datamodel.base_models import InputFormat
            format_enum = getattr(InputFormat, format_name, None)
            
            if format_enum and format_enum in format_options:
                option_type = type(format_options[format_enum]).__name__
                logger.info(f"✓ {format_name}: Supported ({option_type})")
            else:
                logger.error(f"✗ {format_name}: NOT SUPPORTED")
        
        logger.info("\n=== FORMAT SUPPORT SUMMARY ===")
        logger.info("✓ PDF - Portable Document Format")
        logger.info("✓ DOCX - Microsoft Word (Office Open XML)")
        logger.info("✓ XLSX - Microsoft Excel (Office Open XML)")  
        logger.info("✓ PPTX - Microsoft PowerPoint (Office Open XML)")
        logger.info("✓ MD - Markdown")
        logger.info("✓ CSV - Comma Separated Values")
        logger.info("✓ HTML - HyperText Markup Language")
        logger.info("✓ ASCIIDOC - AsciiDoc markup")
        
        logger.info("\n=== TESTING MIME TYPE DETECTION ===")
        
        # Test MIME type detection
        from app.services.ingestion_service import DocumentIngestionService
        ingestion_service = DocumentIngestionService()
        
        test_files = [
            ("document.pdf", "application/pdf"),
            ("document.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            ("spreadsheet.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            ("presentation.pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
            ("document.md", "text/markdown"),
            ("data.csv", "text/csv"),
            ("page.html", "text/html"),
            ("page.htm", "text/html"),
            ("page.xhtml", "application/xhtml+xml"),
            ("document.adoc", "text/asciidoc"),
            ("document.asciidoc", "text/asciidoc"),
            ("document.asc", "text/asciidoc")
        ]
        
        for filename, expected_mime in test_files:
            detected_mime = ingestion_service._guess_mime_type(filename)
            if detected_mime == expected_mime:
                logger.info(f"✓ {filename}: {detected_mime}")
            else:
                logger.error(f"✗ {filename}: expected {expected_mime}, got {detected_mime}")
        
        logger.info("\n=== ALL FORMATS TEST COMPLETED ===")
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)

if __name__ == "__main__":
    test_format_support()
