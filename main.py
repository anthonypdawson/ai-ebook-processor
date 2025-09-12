#!/usr/bin/env python3
"""
Ebook Processor with Ollama

Main application that coordinates ebook reading, text processing, and AI analysis
using Ollama models. Processes ebooks in various formats and generates summaries,
analyses, and insights.
"""

import os
import sys
import logging
from pathlib import Path
from typing import List, Dict, Optional
import json
from datetime import datetime

# Local imports
from ebook_reader import EbookReader
from ollama_processor import OllamaProcessor, PROMPT_TEMPLATES, SYSTEM_PROMPTS
from text_pipeline import ProcessingPipeline, ProcessingConfig

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ebook_processor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class EbookProcessorApp:
    """Main application class for processing ebooks with Ollama"""
    
    def __init__(self, 
                 model_name: str = "llama2",
                 ollama_host: str = "http://localhost:11434"):
        """
        Initialize the application
        
        Args:
            model_name (str): Name of the Ollama model to use
            ollama_host (str): Ollama server host URL
        """
        self.model_name = model_name
        self.ollama_host = ollama_host
        
        # Initialize components
        self.ebook_reader = EbookReader()
        self.ollama_processor = None
        self.processing_config = ProcessingConfig()
        self.pipeline = ProcessingPipeline(self.processing_config)
        
        # Initialize Ollama processor
        self._init_ollama_processor()
    
    def _init_ollama_processor(self):
        """Initialize Ollama processor with error handling"""
        try:
            self.ollama_processor = OllamaProcessor(
                model_name=self.model_name,
                host=self.ollama_host
            )
            logger.info(f"Successfully initialized Ollama processor with model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Ollama processor: {e}")
            logger.error("Please ensure Ollama is running and the model is available")
            sys.exit(1)
    
    def list_available_models(self) -> List[str]:
        """List all available Ollama models"""
        if not self.ollama_processor:
            return []
        
        try:
            models = self.ollama_processor.list_available_models()
            return [model['name'] for model in models]
        except Exception as e:
            logger.error(f"Error listing models: {e}")
            return []
    
    def find_ebooks(self, directory: str, recursive: bool = True) -> List[str]:
        """
        Find all supported ebook files in a directory
        
        Args:
            directory (str): Directory to search
            recursive (bool): Whether to search recursively
            
        Returns:
            List[str]: List of ebook file paths
        """
        try:
            ebooks = self.ebook_reader.find_ebooks(directory, recursive)
            logger.info(f"Found {len(ebooks)} ebook files in {directory}")
            return ebooks
        except Exception as e:
            logger.error(f"Error finding ebooks: {e}")
            return []
    
    def get_ebook_info(self, file_path: str) -> Dict:
        """Get basic information about an ebook"""
        try:
            return self.ebook_reader.get_book_info(file_path)
        except Exception as e:
            logger.error(f"Error getting ebook info for {file_path}: {e}")
            return {}
    
    def process_single_ebook(self, 
                           file_path: str, 
                           processing_type: str = 'summary',
                           custom_prompt: Optional[str] = None,
                           output_dir: str = 'output') -> Dict:
        """
        Process a single ebook
        
        Args:
            file_path (str): Path to the ebook file
            processing_type (str): Type of processing ('summary', 'analysis', etc.)
            custom_prompt (str): Custom prompt template
            output_dir (str): Directory to save results
            
        Returns:
            Dict: Processing result
        """
        logger.info(f"Starting to process: {file_path}")
        
        try:
            # Step 1: Read the ebook
            text_content, metadata = self.ebook_reader.read_ebook(file_path)
            
            if not text_content.strip():
                logger.warning(f"No text content extracted from {file_path}")
                return {'error': 'No text content extracted'}
            
            logger.info(f"Extracted {len(text_content)} characters from {metadata.get('title', 'Unknown')}")
            
            # Step 2: Set up processing parameters
            prompt_template = custom_prompt or PROMPT_TEMPLATES.get(processing_type, PROMPT_TEMPLATES['summary'])
            system_prompt = SYSTEM_PROMPTS.get('analyst')
            
            # Step 3: Process through pipeline
            self.processing_config.processing_mode = processing_type
            result = self.pipeline.process_book(
                text_content,
                metadata,
                self.ollama_processor,
                prompt_template,
                system_prompt
            )
            
            # Step 4: Save results
            self.pipeline.save_results([result], output_dir)
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            return {'error': str(e)}
    
    def process_multiple_ebooks(self, 
                              file_paths: List[str],
                              processing_type: str = 'summary',
                              custom_prompt: Optional[str] = None,
                              output_dir: str = 'output',
                              continue_on_error: bool = True) -> List[Dict]:
        """
        Process multiple ebooks
        
        Args:
            file_paths (List[str]): List of ebook file paths
            processing_type (str): Type of processing
            custom_prompt (str): Custom prompt template
            output_dir (str): Directory to save results
            continue_on_error (bool): Whether to continue if one book fails
            
        Returns:
            List[Dict]: Processing results
        """
        logger.info(f"Starting batch processing of {len(file_paths)} ebooks")
        
        # Prepare book data
        book_data = []
        failed_reads = []
        
        for file_path in file_paths:
            try:
                text_content, metadata = self.ebook_reader.read_ebook(file_path)
                if text_content.strip():
                    book_data.append((text_content, metadata))
                else:
                    logger.warning(f"Skipping {file_path} - no text content")
                    failed_reads.append(file_path)
            except Exception as e:
                logger.error(f"Failed to read {file_path}: {e}")
                failed_reads.append(file_path)
                if not continue_on_error:
                    raise
        
        logger.info(f"Successfully read {len(book_data)} books, {len(failed_reads)} failed")
        
        if not book_data:
            logger.error("No books could be read successfully")
            return []
        
        # Set up processing parameters
        prompt_template = custom_prompt or PROMPT_TEMPLATES.get(processing_type, PROMPT_TEMPLATES['summary'])
        system_prompt = SYSTEM_PROMPTS.get('analyst')
        
        # Process through pipeline
        self.processing_config.processing_mode = processing_type
        results = self.pipeline.process_multiple_books(
            book_data,
            self.ollama_processor,
            prompt_template,
            system_prompt
        )
        
        # Save results
        self.pipeline.save_results(results, output_dir)
        
        # Log summary
        stats = self.pipeline.get_stats()
        logger.info(f"Batch processing completed:")
        logger.info(f"  - Total books processed: {stats['successful_books']}/{stats['total_books']}")
        logger.info(f"  - Total chunks processed: {stats['total_chunks']}")
        logger.info(f"  - Total processing time: {stats['total_processing_time']:.2f} seconds")
        
        return results
    
    def process_directory(self, 
                         directory: str,
                         processing_type: str = 'summary',
                         custom_prompt: Optional[str] = None,
                         output_dir: str = 'output',
                         recursive: bool = True,
                         file_extensions: Optional[List[str]] = None) -> List[Dict]:
        """
        Process all ebooks in a directory
        
        Args:
            directory (str): Directory containing ebooks
            processing_type (str): Type of processing
            custom_prompt (str): Custom prompt template
            output_dir (str): Directory to save results
            recursive (bool): Whether to search recursively
            file_extensions (List[str]): Specific file extensions to process
            
        Returns:
            List[Dict]: Processing results
        """
        logger.info(f"Processing directory: {directory}")
        
        # Find ebooks
        ebooks = self.find_ebooks(directory, recursive)
        
        # Filter by extensions if specified
        if file_extensions:
            ebooks = [book for book in ebooks if Path(book).suffix.lower() in file_extensions]
            logger.info(f"Filtered to {len(ebooks)} books with specified extensions")
        
        if not ebooks:
            logger.warning("No ebooks found in the specified directory")
            return []
        
        return self.process_multiple_ebooks(
            ebooks,
            processing_type,
            custom_prompt,
            output_dir
        )
    
    def configure_processing(self, 
                           chunk_size: int = 4000,
                           chunk_overlap: int = 200,
                           output_format: str = 'json',
                           save_chunks: bool = False) -> None:
        """
        Configure processing parameters
        
        Args:
            chunk_size (int): Maximum characters per chunk
            chunk_overlap (int): Overlap between chunks
            output_format (str): Output format ('json', 'txt', 'markdown')
            save_chunks (bool): Whether to save individual chunks
        """
        self.processing_config.chunk_size = chunk_size
        self.processing_config.chunk_overlap = chunk_overlap
        self.processing_config.output_format = output_format
        self.processing_config.save_chunks = save_chunks
        
        # Recreate pipeline with new config
        self.pipeline = ProcessingPipeline(self.processing_config)
        
        logger.info("Processing configuration updated")
    
    def get_processing_stats(self) -> Dict:
        """Get current processing statistics"""
        return self.pipeline.get_stats()
    
    def create_processing_report(self, results: List[Dict], output_path: str) -> None:
        """
        Create a comprehensive processing report
        
        Args:
            results (List[Dict]): Processing results
            output_path (str): Path to save the report
        """
        report = {
            'report_generated': datetime.now().isoformat(),
            'processing_stats': self.get_processing_stats(),
            'model_info': {
                'model_name': self.model_name,
                'ollama_host': self.ollama_host
            },
            'configuration': {
                'chunk_size': self.processing_config.chunk_size,
                'chunk_overlap': self.processing_config.chunk_overlap,
                'output_format': self.processing_config.output_format
            },
            'books_processed': len(results),
            'successful_books': len([r for r in results if 'error' not in r]),
            'failed_books': len([r for r in results if 'error' in r]),
            'book_summaries': []
        }
        
        # Add summary for each book
        for result in results:
            if 'error' not in result:
                book_summary = {
                    'title': result['metadata'].get('title', 'Unknown'),
                    'author': result['metadata'].get('author', 'Unknown'),
                    'format': result['metadata'].get('format', 'Unknown'),
                    'chunks_processed': result['chunk_info']['successful_chunks'],
                    'processing_time': result.get('processing_stats', {}).get('processing_time', 0)
                }
                report['book_summaries'].append(book_summary)
        
        # Save report
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Processing report saved to: {output_path}")


def main():
    """Main function for command-line usage"""
    print("Ebook Processor with Ollama")
    print("=" * 40)
    
    # Initialize the app
    try:
        app = EbookProcessorApp()
    except Exception as e:
        print(f"Failed to initialize application: {e}")
        return 1
    
    # List available models
    models = app.list_available_models()
    print(f"Available Ollama models: {models}")
    
    # Example usage - you can customize this
    print("\nTo use this application, create a script that imports EbookProcessorApp")
    print("and calls the appropriate methods.")
    print("\nExample:")
    print("app = EbookProcessorApp()")
    print("app.process_directory('/path/to/your/ebooks', processing_type='summary')")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())