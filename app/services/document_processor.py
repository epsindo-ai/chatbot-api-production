import os
import logging
import time
import traceback
from typing import List, Optional, Tuple
from langchain_core.documents import Document

from langchain_docling.loader import ExportType
from langchain_docling import DoclingLoader
from docling.document_converter import DocumentConverter, PdfFormatOption, WordFormatOption, MarkdownFormatOption, CsvFormatOption, HTMLFormatOption, PowerpointFormatOption, ExcelFormatOption, AsciiDocFormatOption
from docling.datamodel.base_models import InputFormat
from docling.chunking import HybridChunker
from docling.datamodel.pipeline_options import (
    AcceleratorDevice,
    AcceleratorOptions,
    PdfPipelineOptions,
    TableStructureOptions,
    TableFormerMode,
    EasyOcrOptions,
)

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
                   handlers=[logging.StreamHandler()])
logger = logging.getLogger("docling_processor")

class DoclingProcessor:
    """Service for processing documents using Docling."""
    
    def __init__(self, 
                 parser_artifact_path: str = "/root/.cache/docling/models",
                 embed_model_id: str = "/app/stella-embed-tokenizer",  # Use local path
                 use_gpu: bool = True):
        """
        Initialize the Docling processor.
        
        Args:
            parser_artifact_path: Path to Docling parser artifacts
            embed_model_id: Embedding model ID for chunking
            use_gpu: Whether to use GPU acceleration
        """
        logger.info("=== INITIALIZING DOCUMENT PROCESSOR ===")
        self.parser_artifact_path = parser_artifact_path
        self.embed_model_id = embed_model_id
        
        # Prioritize GPU usage with fallback to CPU
        self.use_gpu = use_gpu
        
        # Set environment variables for GPU usage before any model loading
        if self.use_gpu:
            os.environ['CUDA_VISIBLE_DEVICES'] = '0'  # Make sure GPU 0 is visible
            os.environ['TORCH_USE_CUDA_DSA'] = '1'    # Enable CUDA device-side assertions
        
        # Check GPU availability with detailed logging
        gpu_available = False
        if self.use_gpu:
            logger.info("Checking GPU availability...")
            try:
                import torch
                logger.info(f"PyTorch version: {torch.__version__}")
                gpu_available = torch.cuda.is_available()
                logger.info(f"torch.cuda.is_available(): {gpu_available}")
                
                if gpu_available:
                    # Set default GPU device
                    torch.cuda.set_device(0)
                    gpu_count = torch.cuda.device_count()
                    current_device = torch.cuda.current_device()
                    gpu_name = torch.cuda.get_device_name(current_device)
                    logger.info(f"GPU detected: {gpu_name} (Device {current_device}/{gpu_count})")
                    logger.info(f"CUDA version: {torch.version.cuda}")
                    
                    # Test GPU memory
                    gpu_memory = torch.cuda.get_device_properties(current_device).total_memory
                    logger.info(f"GPU memory: {gpu_memory / 1024**3:.1f} GB")
                    
                    # Test basic GPU operation
                    test_tensor = torch.tensor([1.0]).cuda()
                    logger.info(f"GPU test tensor device: {test_tensor.device}")
                else:
                    logger.warning("CUDA not available, falling back to CPU")
            except ImportError as e:
                logger.warning(f"PyTorch not available: {e}, falling back to CPU")
            except Exception as e:
                logger.warning(f"GPU check failed: {e}, falling back to CPU")
        else:
            logger.info("GPU usage disabled by parameter")
        
        # Set device based on availability and preference
        if self.use_gpu and gpu_available:
            # Use AUTO to let Docling automatically select the best device
            self.device = AcceleratorDevice.AUTO
            logger.info("✓ CONFIGURED TO USE AUTO DEVICE SELECTION (GPU PREFERRED)")
        else:
            self.device = AcceleratorDevice.CPU
            logger.info("✓ CONFIGURED TO USE CPU PROCESSING")
            
        logger.info(f"Parser artifact path: {parser_artifact_path}")
        logger.info(f"Embedding model ID: {embed_model_id}")
        
        # Check if models directory exists
        if not os.path.exists(self.parser_artifact_path):
            logger.warning(f"Parser artifact path does not exist: {self.parser_artifact_path}")
            try:
                os.makedirs(self.parser_artifact_path, exist_ok=True)
                logger.info(f"Created parser artifact directory: {self.parser_artifact_path}")
            except Exception as e:
                logger.error(f"Failed to create parser artifact directory: {e}")
        
        # Set up PDF pipeline options with GPU/CPU settings based on availability
        logger.info("Setting up PDF pipeline options")
        logger.info(f"Device configuration: {self.device}")
        logger.info(f"Device value: {self.device.value}")
        
        self.pdf_pipeline_options = PdfPipelineOptions(
            artifacts_path=self.parser_artifact_path,
            do_ocr=True,
            do_table_structure=True,
            ocr_options=EasyOcrOptions(lang=["en", "id"]),
            table_structure_options=TableStructureOptions(
                do_cell_matching=True,
                mode=TableFormerMode.ACCURATE
            ),
            accelerator_options=AcceleratorOptions(
                device=self.device,
            )
        )
        
        logger.info(f"✓ PDF Pipeline configured with accelerator device: {self.device.value}")
        
        # Log the accelerator options to verify
        logger.info(f"Accelerator options device: {self.pdf_pipeline_options.accelerator_options.device}")
        logger.info(f"Accelerator options device value: {self.pdf_pipeline_options.accelerator_options.device.value}")
        
        # Create document converter with format options
        logger.info("Creating document converter")
        try:
            self.doc_converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(pipeline_options=self.pdf_pipeline_options),
                    InputFormat.DOCX: WordFormatOption(),
                    InputFormat.XLSX: ExcelFormatOption(),
                    InputFormat.PPTX: PowerpointFormatOption(),
                    InputFormat.MD: MarkdownFormatOption(),
                    InputFormat.CSV: CsvFormatOption(),
                    InputFormat.HTML: HTMLFormatOption(),
                    InputFormat.ASCIIDOC: AsciiDocFormatOption()
                }
            )
            logger.info("Document converter created successfully")
            logger.info("✓ Supported formats: PDF, DOCX, XLSX, PPTX, Markdown, CSV, HTML, AsciiDoc")
        except Exception as e:
            logger.error(f"Failed to create document converter: {e}", exc_info=True)
            raise
        
        logger.info("=== DOCUMENT PROCESSOR INITIALIZED ===")
    
    def process_files(self, file_paths: List[str], metadata: Optional[dict] = None) -> List[Document]:
        """
        Process files using Docling.
        
        Args:
            file_paths: List of file paths to process
            metadata: Optional metadata to add to documents
            
        Returns:
            List of processed documents
        """
        logger.info(f"=== STARTING DOCUMENT PROCESSING FOR {len(file_paths)} FILES ===")
        start_time = time.time()
        
        # Check if files exist
        valid_paths = [path for path in file_paths if os.path.exists(path)]
        if not valid_paths:
            logger.warning(f"No valid file paths found in: {file_paths}")
            return []
        
        logger.info(f"Processing {len(valid_paths)} files with Docling")
        for path in valid_paths:
            logger.info(f"File to process: {path} (size: {os.path.getsize(path)} bytes)")
        
        try:
            # STEP 1: Create DoclingLoader
            logger.info("STEP 1: Creating DoclingLoader")
            loader_start = time.time()
            try:
                # Use dynamic device configuration
                loader = DoclingLoader(
                    file_path=valid_paths,
                    converter=self.doc_converter,
                    export_type=ExportType.DOC_CHUNKS,
                    chunker=HybridChunker(tokenizer=self.embed_model_id),
                )
                logger.info(f"DoclingLoader created in {time.time() - loader_start:.2f} seconds")
            except Exception as e:
                logger.error(f"Failed to create DoclingLoader: {e}", exc_info=True)
                logger.error("Docling processing failed - no fallback mechanism will be used")
                return []
            
            # STEP 2: Parse documents
            logger.info("STEP 2: Parsing documents")
            parse_start = time.time()
            try:
                logger.info("Starting document loading and parsing")
                docs = loader.load()
                parse_time = time.time() - parse_start
                logger.info(f"Document parsing completed in {parse_time:.2f} seconds")
                
                if docs:
                    logger.info(f"Successfully processed {len(docs)} document chunks")
                    # Log some info about the chunks
                    logger.info(f"First chunk content length: {len(docs[0].page_content)} chars")
                    logger.info(f"Metadata keys: {list(docs[0].metadata.keys())}")
                else:
                    logger.warning("No document chunks were produced by Docling")
                    
                    # Try to extract raw text as fallback for minimal content files
                    logger.info("Attempting fallback: extracting raw text from document")
                    try:
                        # Get the document conversion result to extract text
                        conv_result = self.doc_converter.convert(valid_paths[0])
                        raw_text = conv_result.document.export_to_markdown().strip()
                        
                        if raw_text and len(raw_text) > 10:  # Minimum content threshold
                            logger.info(f"Fallback successful: extracted {len(raw_text)} characters of raw text")
                            # Create a basic document with the raw text
                            fallback_doc = Document(
                                page_content=raw_text,
                                metadata=metadata or {}
                            )
                            docs = [fallback_doc]
                            logger.info("Created fallback document from raw text")
                        else:
                            logger.warning(f"Fallback failed: raw text too short ({len(raw_text)} chars)")
                            return []
                    except Exception as fallback_error:
                        logger.error(f"Fallback text extraction failed: {fallback_error}")
                        return []
            except Exception as e:
                logger.error(f"Failed during document parsing: {e}", exc_info=True)
                logger.error("Docling parsing failed - no fallback mechanism will be used")
                return []
            
            # STEP 3: Add metadata if provided
            if metadata:
                logger.info("STEP 3: Adding metadata to documents")
                try:
                    for doc in docs:
                        doc.metadata.update(metadata)
                    logger.info(f"Added metadata: {metadata}")
                except Exception as e:
                    logger.error(f"Failed to add metadata: {e}", exc_info=True)
            
            total_time = time.time() - start_time
            logger.info(f"=== DOCUMENT PROCESSING COMPLETED IN {total_time:.2f} SECONDS ===")
            return docs
        
        except Exception as e:
            logger.error(f"Error processing files with Docling: {e}", exc_info=True)
            logger.error("Docling processing failed - no fallback mechanism will be used")
            return []
    
    def process_file_objects(self, file_objects: List[tuple], metadata: Optional[dict] = None) -> List[Document]:
        """
        Process file objects (in-memory files) using Docling.
        
        Args:
            file_objects: List of tuples containing (file_content, file_name, mime_type)
            metadata: Optional metadata to add to documents
            
        Returns:
            List of processed documents
        """
        if not file_objects:
            return []
        
        logger.info(f"=== STARTING FILE OBJECT PROCESSING FOR {len(file_objects)} FILES ===")
        start_time = time.time()
        
        try:
            # STEP 1: Save files to temporary location
            logger.info("STEP 1: Saving files to temporary location")
            temp_dir = "/tmp/docling_temp"
            os.makedirs(temp_dir, exist_ok=True)
            
            file_paths = []
            for idx, (file_content, file_name, mime_type) in enumerate(file_objects):
                logger.info(f"Processing file {idx+1}/{len(file_objects)}: {file_name} ({mime_type})")
                
                # Preserve the original filename with extension for Docling format detection
                file_path = os.path.join(temp_dir, file_name)
                logger.info(f"Saving file with original filename: {file_path}")
                
                try:
                    with open(file_path, "wb") as f:
                        f.write(file_content)
                    file_size = len(file_content)
                    logger.info(f"Saved file to {file_path} (size: {file_size} bytes)")
                    file_paths.append(file_path)
                except Exception as e:
                    logger.error(f"Failed to save file {file_name}: {e}", exc_info=True)
            
            # STEP 2: Process files
            logger.info("STEP 2: Processing saved files")
            docs = self.process_files(file_paths, metadata)
            
            # STEP 3: Clean up temporary files
            logger.info("STEP 3: Cleaning up temporary files")
            for path in file_paths:
                if os.path.exists(path):
                    try:
                        os.remove(path)
                        logger.info(f"Removed temporary file: {path}")
                    except Exception as e:
                        logger.error(f"Failed to remove temporary file {path}: {e}")
            
            total_time = time.time() - start_time
            logger.info(f"=== FILE OBJECT PROCESSING COMPLETED IN {total_time:.2f} SECONDS ===")
            return docs
        
        except Exception as e:
            logger.error(f"Error processing file objects with Docling: {e}", exc_info=True)
            return [] 