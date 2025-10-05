"""
Text Processing Pipeline Module

This module provides functionality for chunking large text content,
managing processing workflows, and coordinating text analysis tasks.
Supports both synchronous and asynchronous processing.
"""

import re
from ai_ebook_processor.utils.logger import get_logger
import asyncio
from typing import List, Dict, Optional, Tuple, Any, Callable, Union
from pathlib import Path
import math
import logging
from dataclasses import dataclass
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from tqdm import tqdm

logger = get_logger(__name__)


@dataclass
class ProcessingConfig:
    """Configuration for text processing"""
    chunk_size: int = 4000  # Maximum characters per chunk
    chunk_overlap: int = 200  # Overlap between chunks
    min_chunk_size: int = 100  # Minimum characters for a valid chunk
    processing_mode: str = 'summary'  # default processing mode
    output_format: str = 'json'  # json, txt, markdown
    save_chunks: bool = False  # Whether to save individual chunks
    parallel_processing: bool = False  # Future feature
    

@dataclass
class ChunkInfo:
    """Information about a text chunk"""
    index: int
    start_pos: int
    end_pos: int
    length: int
    text: str
    metadata: Dict = None
    page_start: int = None  # First page this chunk appears on
    page_end: int = None    # Last page this chunk appears on
    page_type: str = None   # 'actual' for PDFs, 'estimated' for others
    

class TextChunker:
    """Handles intelligent text chunking for processing"""
    
    def __init__(self, config: ProcessingConfig):
        self.config = config
    
    def chunk_text_with_pages(self, text: str, page_info: List[Dict], preserve_paragraphs: bool = True) -> List[ChunkInfo]:
        """
        Split text into manageable chunks while preserving page information
        
        Args:
            text (str): Text content to chunk
            page_info (List[Dict]): Page information from ebook reader
            preserve_paragraphs (bool): Try to keep paragraphs intact
            
        Returns:
            List[ChunkInfo]: List of text chunks with page metadata
        """
        if not text or len(text) < self.config.min_chunk_size:
            return []
        
        if not page_info:
            # Fall back to regular chunking if no page info
            return self.chunk_text(text, preserve_paragraphs)
        
        chunks = []
        
        if preserve_paragraphs:
            chunks = self._chunk_by_paragraphs_with_pages(text, page_info)
        else:
            chunks = self._chunk_by_size_with_pages(text, page_info)
        
        # Create ChunkInfo objects with page information
        chunk_infos = []
        for i, (start, end, chunk_text, page_start, page_end, page_type) in enumerate(chunks):
            chunk_info = ChunkInfo(
                index=i,
                start_pos=start,
                end_pos=end,
                length=len(chunk_text),
                text=chunk_text,
                metadata={'method': 'paragraphs_with_pages' if preserve_paragraphs else 'size_with_pages'},
                page_start=page_start,
                page_end=page_end,
                page_type=page_type
            )
            chunk_infos.append(chunk_info)
        
        logger.info(f"Created {len(chunk_infos)} chunks with page tracking from {len(text)} characters")
        return chunk_infos
    
    def _find_pages_for_position(self, page_info: List[Dict], start_pos: int, end_pos: int) -> Tuple[int, int, str]:
        """
        Find which pages a text chunk spans
        
        Args:
            page_info: List of page information dicts
            start_pos: Start character position in text
            end_pos: End character position in text
            
        Returns:
            Tuple of (first_page, last_page, page_type)
        """
        first_page = None
        last_page = None
        page_type = 'estimated'  # Default
        
        for page in page_info:
            page_start = page['start_pos']
            page_end = page['end_pos']
            page_num = page['page_num']
            
            # Check if this page overlaps with our chunk
            if page_end > start_pos and page_start < end_pos:
                if first_page is None:
                    first_page = page_num
                    page_type = page.get('page_type', 'estimated')
                last_page = page_num
        
        return first_page or 1, last_page or first_page or 1, page_type
    
    def _chunk_by_paragraphs_with_pages(self, text: str, page_info: List[Dict]) -> List[Tuple[int, int, str, int, int, str]]:
        """Chunk text by paragraphs while tracking page information"""
        # Use the existing paragraph chunking logic
        basic_chunks = self._chunk_by_paragraphs(text)
        
        # Add page information to each chunk
        page_aware_chunks = []
        for start, end, chunk_text in basic_chunks:
            page_start, page_end, page_type = self._find_pages_for_position(page_info, start, end)
            page_aware_chunks.append((start, end, chunk_text, page_start, page_end, page_type))
        
        return page_aware_chunks
    
    def _chunk_by_size_with_pages(self, text: str, page_info: List[Dict]) -> List[Tuple[int, int, str, int, int, str]]:
        """Chunk text by size while tracking page information"""
        # Use the existing size chunking logic
        basic_chunks = self._chunk_by_size(text)
        
        # Add page information to each chunk
        page_aware_chunks = []
        for start, end, chunk_text in basic_chunks:
            page_start, page_end, page_type = self._find_pages_for_position(page_info, start, end)
            page_aware_chunks.append((start, end, chunk_text, page_start, page_end, page_type))
        
        return page_aware_chunks

    def chunk_text(self, text: str, preserve_paragraphs: bool = True) -> List[ChunkInfo]:
        """
        Split text into manageable chunks for processing
        
        Args:
            text (str): Text content to chunk
            preserve_paragraphs (bool): Try to keep paragraphs intact
            
        Returns:
            List[ChunkInfo]: List of text chunks with metadata
        """
        if not text or len(text) < self.config.min_chunk_size:
            return []
        
        chunks = []
        
        if preserve_paragraphs:
            chunks = self._chunk_by_paragraphs(text)
        else:
            chunks = self._chunk_by_size(text)
        
        # Create ChunkInfo objects
        chunk_infos = []
        for i, (start, end, chunk_text) in enumerate(chunks):
            chunk_info = ChunkInfo(
                index=i,
                start_pos=start,
                end_pos=end,
                length=len(chunk_text),
                text=chunk_text,
                metadata={'method': 'paragraphs' if preserve_paragraphs else 'size'}
            )
            chunk_infos.append(chunk_info)
        
        logger.info(f"Created {len(chunk_infos)} chunks from {len(text)} characters")
        return chunk_infos
    
    def _chunk_by_paragraphs(self, text: str) -> List[Tuple[int, int, str]]:
        """Chunk text by paragraphs while respecting size limits"""
        # Split by double newlines (paragraph breaks)
        paragraphs = re.split(r'\n\s*\n', text)
        chunks = []
        current_chunk = ""
        current_start = 0
        text_pos = 0
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                text_pos += len(paragraph) + 2  # account for newlines
                continue
            
            # Check if adding this paragraph would exceed chunk size
            potential_chunk = current_chunk + "\n\n" + paragraph if current_chunk else paragraph
            
            if len(potential_chunk) <= self.config.chunk_size:
                current_chunk = potential_chunk
            else:
                # Save current chunk if it exists
                if current_chunk:
                    chunks.append((current_start, current_start + len(current_chunk), current_chunk))
                    
                # Handle paragraph that's too long
                if len(paragraph) > self.config.chunk_size:
                    # Split long paragraph
                    para_chunks = self._split_long_text(paragraph)
                    for para_chunk in para_chunks:
                        chunks.append((text_pos, text_pos + len(para_chunk), para_chunk))
                        text_pos += len(para_chunk)
                else:
                    current_start = text_pos
                    current_chunk = paragraph
            
            text_pos += len(paragraph) + 2
        
        # Add final chunk
        if current_chunk:
            chunks.append((current_start, current_start + len(current_chunk), current_chunk))
        
        return self._add_overlap(chunks, text)
    
    def _chunk_by_size(self, text: str) -> List[Tuple[int, int, str]]:
        """Simple chunking by character size"""
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.config.chunk_size
            
            if end >= len(text):
                chunk = text[start:]
                chunks.append((start, len(text), chunk))
                break
            
            # Try to break at a sentence or word boundary
            chunk = text[start:end]
            
            # Look for sentence boundaries
            last_sentence = max(
                chunk.rfind('.'),
                chunk.rfind('!'),
                chunk.rfind('?')
            )
            
            if last_sentence > len(chunk) * 0.5:  # If we found a sentence boundary in the latter half
                end = start + last_sentence + 1
            else:
                # Look for word boundaries
                last_space = chunk.rfind(' ')
                if last_space > len(chunk) * 0.5:
                    end = start + last_space
            
            chunk = text[start:end]
            chunks.append((start, end, chunk))
            start = end - self.config.chunk_overlap
        
        return chunks
    
    def _split_long_text(self, text: str) -> List[str]:
        """Split text that's longer than chunk size"""
        chunks = []
        words = text.split()
        current_chunk = []
        current_length = 0
        
        for word in words:
            word_length = len(word) + 1  # +1 for space
            
            if current_length + word_length > self.config.chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = [word]
                current_length = len(word)
            else:
                current_chunk.append(word)
                current_length += word_length
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    def _add_overlap(self, chunks: List[Tuple[int, int, str]], original_text: str) -> List[Tuple[int, int, str]]:
        """Add overlap between chunks"""
        if len(chunks) <= 1 or self.config.chunk_overlap <= 0:
            return chunks
        
        overlapped_chunks = []
        
        for i, (start, end, text) in enumerate(chunks):
            if i == 0:
                # First chunk - no overlap at the beginning
                overlapped_chunks.append((start, end, text))
            else:
                # Add overlap from previous chunk
                overlap_start = max(0, start - self.config.chunk_overlap)
                overlap_text = original_text[overlap_start:start]
                new_text = overlap_text + text
                overlapped_chunks.append((overlap_start, end, new_text))
        
        return overlapped_chunks


class ProcessingPipeline:
    """Main pipeline for processing ebooks"""
    
    def __init__(self, config: ProcessingConfig):
        self.config = config
        self.chunker = TextChunker(config)
        self.processing_stats = {
            'total_books': 0,
            'successful_books': 0,
            'failed_books': 0,
            'total_chunks': 0,
            'total_processing_time': 0,
            'start_time': None,
            'end_time': None
        }
    
    def process_book(self, 
                    text_content: str, 
                    metadata: Dict,
                    processor,  # OllamaProcessor instance
                    prompt_template: str = None,
                    system_prompt: str = None) -> Dict:
        """
        Process a complete book through the pipeline
        
        Args:
            text_content (str): Full text content of the book
            metadata (Dict): Book metadata
            processor: OllamaProcessor instance
            prompt_template (str): Template for processing prompts
            system_prompt (str): System prompt for processing
            
        Returns:
            Dict: Complete processing results
        """
        self.processing_stats['total_books'] += 1
        start_time = datetime.now()
        
        try:
            logger.info(f"Processing book: {metadata.get('title', 'Unknown')}")
            
            # Step 1: Chunk the text
            chunks = self.chunker.chunk_text(text_content)
            if not chunks:
                logger.warning("No valid chunks created from text")
                return self._create_empty_result(metadata, "No valid chunks created")
            
            self.processing_stats['total_chunks'] += len(chunks)
            
            # Step 2: Process chunks through Ollama (in parallel!)
            chunk_texts = [chunk.text for chunk in chunks]
            processing_results = processor.process_chunks_parallel(
                chunk_texts,
                prompt_template,
                system_prompt,
                max_workers=4,  # Adjust based on your system
                progress_bar=True
            )
            
            # Step 3: Combine results
            combined_result = self._combine_chunk_results(
                chunks, processing_results, metadata
            )

            # Attach raw chunk texts for downstream RAG ingestion (canonical source of truth)
            combined_result['raw_chunks'] = [c.text for c in chunks]
            combined_result['raw_text'] = "\n\n".join(combined_result['raw_chunks'])
            
            # Step 4: Create book-level summary if requested
            if self.config.processing_mode == 'summary':
                combined_result['book_summary'] = processor.create_book_summary(
                    text_content[:10000],  # First 10k characters for summary
                    metadata
                )
            
            processing_time = (datetime.now() - start_time).total_seconds()
            combined_result['processing_stats'] = {
                'processing_time': processing_time,
                'chunk_count': len(chunks),
                'success_rate': sum(1 for r in processing_results if r['success']) / len(processing_results)
            }
            
            self.processing_stats['successful_books'] += 1
            self.processing_stats['total_processing_time'] += processing_time
            
            logger.info(f"Successfully processed book in {processing_time:.2f} seconds")
            return combined_result
            
        except Exception as e:
            logger.error(f"Error processing book: {e}")
            self.processing_stats['failed_books'] += 1
            return self._create_empty_result(metadata, str(e))
    
    async def process_book_async(self, 
                               text_content: str, 
                               metadata: Dict, 
                               processor, 
                               prompt_template: str = None, 
                               system_prompt: str = None,
                               progress_callback: Optional[Callable[[int, int, str], None]] = None) -> Dict:
        """
        Asynchronous version of process_book for parallel processing.
        
        Args:
            text_content (str): Full text content of the book
            metadata (Dict): Book metadata (title, author, etc.)
            processor: Ollama processor instance
            prompt_template (str): Template for processing prompts
            system_prompt (str): System prompt for processing
            progress_callback: Optional callback for progress updates (current, total, status)
            
        Returns:
            Dict: Complete processing results
        """
        start_time = datetime.now()
        
        try:
            book_title = metadata.get('title', 'Unknown')
            logger.info(f"Processing book async: {book_title}")
            
            # Update progress
            if progress_callback:
                progress_callback(0, 100, f"Chunking {book_title}")
            
            # Step 1: Chunk the text (run in thread pool for CPU-bound work)
            loop = asyncio.get_event_loop()
            chunks = await loop.run_in_executor(
                None, 
                self.chunker.chunk_text, 
                text_content
            )
            
            if not chunks:
                logger.warning(f"No valid chunks created from {book_title}")
                return self._create_empty_result(metadata, "No valid chunks created")
            
            if progress_callback:
                progress_callback(20, 100, f"Processing {len(chunks)} chunks")
            
            # Step 2: Process chunks through Ollama asynchronously
            chunk_texts = [chunk.text for chunk in chunks]
            
            # Create progress callback for chunk processing
            chunk_progress_callback = None
            if progress_callback:
                def chunk_cb(current, total):
                    # Map chunk progress to overall progress (20% - 80%)
                    overall_progress = 20 + int((current / total) * 60)
                    progress_callback(overall_progress, 100, f"Processing chunk {current}/{total}")
                chunk_progress_callback = chunk_cb
            
            processing_results = await self._process_chunks_async(
                processor,
                chunk_texts,
                prompt_template,
                system_prompt,
                progress_callback=chunk_progress_callback
            )
            
            if progress_callback:
                progress_callback(80, 100, "Combining results")
            
            # Step 3: Combine results (same as sync version)
            combined_result = self._combine_chunk_results(chunks, processing_results, metadata)
            
            # Add book summary if enabled
            if self.config.processing_mode == 'summary':
                combined_result['book_summary'] = await self._create_book_summary_async(
                    processor,
                    text_content[:10000],  # First 10k characters for summary
                    metadata
                )
            
            processing_time = (datetime.now() - start_time).total_seconds()
            combined_result['processing_stats'] = {
                'processing_time': processing_time,
                'chunk_count': len(chunks),
                'success_rate': sum(1 for r in processing_results if r['success']) / len(processing_results)
            }
            
            if progress_callback:
                progress_callback(100, 100, "Complete")
            
            logger.info(f"Successfully processed book async in {processing_time:.2f} seconds")
            return combined_result
            
        except Exception as e:
            logger.error(f"Error processing book async: {e}")
            if progress_callback:
                progress_callback(100, 100, f"Error: {str(e)}")
            return self._create_empty_result(metadata, str(e))

    async def _process_chunks_async(self, 
                                   processor, 
                                   chunk_texts: List[str], 
                                   prompt_template: str = None,
                                   system_prompt: str = None,
                                   progress_callback: Optional[Callable[[int, int], None]] = None) -> List[Dict]:
        """
        Process chunks asynchronously with configurable parallelism.
        """
        # Use ThreadPoolExecutor for sync processors (most common case)
        loop = asyncio.get_event_loop()
        
        def process_chunk_sync(index: int, chunk_text: str) -> Tuple[int, Dict]:
            try:
                # Use the processor's existing chunk processing method
                if hasattr(processor, 'process_chunk'):
                    result = processor.process_chunk(chunk_text, prompt_template, system_prompt)
                elif hasattr(processor, 'process_text'):
                    result = processor.process_text(chunk_text, prompt_template, system_prompt)
                else:
                    # Fallback - just return the chunk text
                    result = {'success': True, 'response': chunk_text}
                
                return index, result
            except Exception as e:
                logger.error(f"Error processing chunk {index}: {e}")
                return index, {'success': False, 'error': str(e)}
        
        # Use ThreadPoolExecutor for concurrent processing
        with ThreadPoolExecutor(max_workers=4) as executor:
            # Submit all chunk processing tasks
            futures = [
                loop.run_in_executor(executor, process_chunk_sync, i, chunk_text)
                for i, chunk_text in enumerate(chunk_texts)
            ]
            
            # Collect results as they complete, updating progress
            completed_results = []
            for future in asyncio.as_completed(futures):
                result = await future
                completed_results.append(result)
                
                if progress_callback:
                    progress_callback(len(completed_results), len(chunk_texts))
        
        # Sort results by original order
        ordered_results = [None] * len(chunk_texts)
        for index, chunk_result in completed_results:
            ordered_results[index] = chunk_result
        
        return ordered_results

    async def _create_book_summary_async(self, processor, text_content: str, metadata: Dict) -> str:
        """Create book summary asynchronously."""
        loop = asyncio.get_event_loop()
        
        def create_summary_sync():
            if hasattr(processor, 'create_book_summary'):
                return processor.create_book_summary(text_content, metadata)
            else:
                return "Summary generation not available"
        
        return await loop.run_in_executor(None, create_summary_sync)
    
    def process_multiple_books(self,
                              book_data: List[Tuple[str, Dict]],  # (text, metadata) pairs
                              processor,
                              prompt_template: str = None,
                              system_prompt: str = None) -> List[Dict]:
        """
        Process multiple books
        
        Args:
            book_data: List of (text_content, metadata) tuples
            processor: OllamaProcessor instance
            prompt_template: Template for processing
            system_prompt: System prompt for processing
            
        Returns:
            List[Dict]: Results for all processed books
        """
        self.processing_stats['start_time'] = datetime.now()
        results = []
        
        logger.info(f"Starting batch processing of {len(book_data)} books")
        
        for i, (text_content, metadata) in enumerate(tqdm(book_data, desc="Processing books")):
            logger.info(f"Processing book {i+1}/{len(book_data)}: {metadata.get('title', 'Unknown')}")
            
            result = self.process_book(
                text_content, metadata, processor, prompt_template, system_prompt
            )
            results.append(result)
        
        self.processing_stats['end_time'] = datetime.now()
        
        logger.info(f"Batch processing completed. Success: {self.processing_stats['successful_books']}/{self.processing_stats['total_books']}")
        
        return results
    
    def _combine_chunk_results(self, 
                              chunks: List[ChunkInfo], 
                              processing_results: List[Dict], 
                              metadata: Dict) -> Dict:
        """Combine individual chunk results into a complete book result"""
        
        successful_results = [r for r in processing_results if r['success']]
        combined_text = "\n\n".join([r['response'] for r in successful_results])
        
        return {
            'metadata': metadata,
            'processing_config': {
                'chunk_size': self.config.chunk_size,
                'chunk_overlap': self.config.chunk_overlap,
                'processing_mode': self.config.processing_mode
            },
            'chunk_info': {
                'total_chunks': len(chunks),
                'successful_chunks': len(successful_results),
                'failed_chunks': len(chunks) - len(successful_results),
                'chunks': [
                    {
                        'index': chunk.index,
                        'length': chunk.length,
                        'success': processing_results[chunk.index]['success']
                    } for chunk in chunks
                ]
            },
            'combined_result': combined_text,
            # raw canonical text for RAG (do not rely on combined_result which may contain LLM transformations)
            'raw_chunks': [c.text for c in chunks],
            'raw_text': "\n\n".join([c.text for c in chunks]),
            'individual_results': processing_results if self.config.save_chunks else None,
            'timestamp': datetime.now().isoformat()
        }
    
    def _create_empty_result(self, metadata: Dict, error_message: str) -> Dict:
        """Create an empty result structure for failed processing"""
        return {
            'metadata': metadata,
            'processing_config': {
                'chunk_size': self.config.chunk_size,
                'chunk_overlap': self.config.chunk_overlap,
                'processing_mode': self.config.processing_mode
            },
            'chunk_info': {
                'total_chunks': 0,
                'successful_chunks': 0,
                'failed_chunks': 0,
                'chunks': []
            },
            'combined_result': "",
            'error': error_message,
            'individual_results': None,
            'timestamp': datetime.now().isoformat()
        }
    
    def save_results(self, results: List[Dict], output_dir: str) -> None:
        """
        Save processing results to files
        
        Args:
            results (List[Dict]): Processing results
            output_dir (str): Directory to save results
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save complete results as JSON
        json_file = output_path / f"ebook_processing_results_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Complete results saved to: {json_file}")
        
        # Save individual book results
        for i, result in enumerate(results):
            book_title = result['metadata'].get('title', f'book_{i}')
            # Clean title for filename
            clean_title = re.sub(r'[^\w\s-]', '', book_title).strip()
            clean_title = re.sub(r'[-\s]+', '_', clean_title)
            
            if self.config.output_format == 'txt':
                txt_file = output_path / f"{clean_title}_{timestamp}.txt"
                with open(txt_file, 'w', encoding='utf-8') as f:
                    f.write(f"Book: {result['metadata'].get('title', 'Unknown')}\n")
                    f.write(f"Author: {result['metadata'].get('author', 'Unknown')}\n\n")
                    f.write(result['combined_result'])
            
            elif self.config.output_format == 'markdown':
                md_file = output_path / f"{clean_title}_{timestamp}.md"
                with open(md_file, 'w', encoding='utf-8') as f:
                    f.write(f"# {result['metadata'].get('title', 'Unknown')}\n\n")
                    f.write(f"**Author:** {result['metadata'].get('author', 'Unknown')}\n\n")
                    f.write(f"**Processed:** {result['timestamp']}\n\n")
                    f.write("## Analysis Results\n\n")
                    f.write(result['combined_result'])
        
        # Save processing statistics
        stats_file = output_path / f"processing_stats_{timestamp}.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(self.processing_stats, f, indent=2, default=str)
        
        logger.info(f"Processing statistics saved to: {stats_file}")
    
    def get_stats(self) -> Dict:
        """Get current processing statistics"""
        return self.processing_stats.copy()


# Example usage
if __name__ == "__main__":
    # Example configuration
    config = ProcessingConfig(
        chunk_size=3000,
        chunk_overlap=150,
        processing_mode='summary',
        output_format='markdown',
        save_chunks=True
    )
    
    pipeline = ProcessingPipeline(config)
    
    # Example text chunking
    sample_text = "This is a sample text for demonstration purposes. " * 200
    chunker = TextChunker(config)
    chunks = chunker.chunk_text(sample_text)
    
    print(f"Created {len(chunks)} chunks from sample text")
    for chunk in chunks[:3]:  # Show first 3 chunks
        print(f"Chunk {chunk.index}: {len(chunk.text)} characters")