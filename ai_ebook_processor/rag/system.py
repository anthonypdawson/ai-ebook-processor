"""
RAG (Retrieval Augmented Generation) Extension for Ebook Processor

This module creates a vector database of your processed ebooks, allowing the AI
to retrieve relevant information and answer questions about your entire collection.
"""

import os
from typing import List, Dict, Optional, Any
import json
from ai_ebook_processor.utils.logger import get_logger
import time
from pathlib import Path
import hashlib
import sys

# You would need to install these:
# pip install chromadb sentence-transformers

# Import timing utilities
from .timing import timing_decorator, Timer, detailed_timer
from ..utils.config import Config

logger = get_logger(__name__)

# Try to import psutil for memory detection, fallback if not available
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

try:
    import chromadb
    
    from sentence_transformers import SentenceTransformer
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    logger.warning("RAG dependencies not installed. Run: pip install chromadb sentence-transformers")




class EbookRAGSystem:
    """
    Retrieval Augmented Generation system for ebooks
    
    This creates a searchable knowledge base from your processed ebooks,
    allowing you to ask questions about your entire collection.
    """
    
    @timing_decorator("RAG System Initialization")
    def __init__(self, db_path: str = "ebook_db", config_path: str = "config/config.yml"):
        if not RAG_AVAILABLE:
            raise ImportError("Please install: pip install chromadb sentence-transformers")
        
        # Load configuration using existing Config class
        self.config = Config(config_path)
        
        with Timer("ChromaDB Client Setup"):
            self.db_path = db_path
            self.client = chromadb.PersistentClient(path=db_path, settings=chromadb.config.Settings(anonymized_telemetry=False))
            self.collection = self.client.get_or_create_collection("ebooks")
            # Separate collection for book metadata only - this makes book listing super fast
            self.book_registry = self.client.get_or_create_collection("book_registry")
        
        # Lazy load the encoder only when needed for embeddings
        self._encoder = None
        
        logger.info(f"RAG system initialized with database at: {db_path}")
    
    @property
    def encoder(self):
        """Lazy load sentence transformer only when needed"""
        if self._encoder is None:
            with Timer("Loading Sentence Transformer Model", verbose=True):
                    try:
                        model_name = self.config.get("rag.embedding_model") or "all-MiniLM-L6-v2"
                        logger.info(f"Loading sentence transformer model: {model_name}")
                        import torch
                        device = "cuda" if torch.cuda.is_available() else "cpu"
                        logger.info(f"Using device: {device}")
                        self._encoder = SentenceTransformer(model_name, device=device)
                    except Exception as e:
                        logger.error(f"Error loading sentence transformer model '{model_name}': {e}")
                        raise ImportError(f"Could not load embedding model '{model_name}'. Please check your config and install the model if needed.")
        return self._encoder
    
    def get_file_hash(self, file_path: str) -> str:
        """
        Get MD5 hash of file for deduplication
        
        Args:
            file_path: Path to the file
            
        Returns:
            MD5 hash as hexadecimal string
        """
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logger.error(f"Error computing file hash for {file_path}: {e}")
            return ""
    
    @timing_decorator('register_book')
    def register_book(self, book_id: str, metadata: Dict, chunk_ids: List[str] = None) -> bool:
        """Register a book in the book registry for fast lookup
        
        Args:
            book_id: Unique book identifier
            metadata: Book metadata dictionary
            chunk_ids: List of chunk IDs for this book (for efficient retrieval)
        """
        try:
            # Enhance metadata with chunk tracking information
            enhanced_metadata = metadata.copy()
            
            if chunk_ids:
                enhanced_metadata.update({
                    'chunk_count': len(chunk_ids),
                    'first_chunk_id': chunk_ids[0] if chunk_ids else '',
                    'last_chunk_id': chunk_ids[-1] if chunk_ids else '',
                    'chunk_id_pattern': f"{book_id}_chunk_*",  # Pattern for finding chunks
                    'chunk_range': f"{chunk_ids[0]} to {chunk_ids[-1]}" if chunk_ids else ''
                })
            elif 'chunks' in metadata:
                # Fallback to metadata chunk count if chunk_ids not provided
                enhanced_metadata['chunk_count'] = metadata['chunks']
            
            # Check if book already exists
            existing = self.book_registry.get(ids=[book_id])
            if existing['ids']:
                # Update existing book
                self.book_registry.update(
                    ids=[book_id],
                    metadatas=[enhanced_metadata]
                )
                logger.debug(f"Updated book registry for {book_id} with {len(chunk_ids or [])} chunks")
            else:
                # Add new book
                self.book_registry.add(
                    ids=[book_id],
                    documents=[f"Book: {metadata.get('title', 'Unknown')} ({len(chunk_ids or [])} chunks)"],
                    metadatas=[enhanced_metadata]
                )
                logger.debug(f"Registered new book {book_id} in registry with {len(chunk_ids or [])} chunks")
            return True
        except Exception as e:
            logger.error(f"Error registering book {book_id}: {e}")
            return False
    
    def get_book_chunks_efficient(self, book_id: str, limit: int = None, 
                                include_page_info: bool = True) -> Dict[str, Any]:
        """
        Efficiently retrieve chunks for a specific book using registry offset information
        
        Args:
            book_id: Book identifier
            limit: Maximum number of chunks to return
            include_page_info: Whether to include page location metadata
            
        Returns:
            Dictionary with chunk data, metadata, and page information
        """
        try:
            # First check the book registry for efficient retrieval hints
            registry_results = self.book_registry.get(ids=[book_id])
            if registry_results['ids'] and registry_results['metadatas']:
                book_meta = registry_results['metadatas'][0]
                
                # Use chunk ID pattern for efficient retrieval
                chunk_pattern = book_meta.get('chunk_id_pattern', f"{book_id}_chunk_*")
                
                # If we have specific chunk range info, we can be very targeted
                first_chunk = book_meta.get('first_chunk_id')
                last_chunk = book_meta.get('last_chunk_id')
                
                if first_chunk and last_chunk:
                    logger.debug(f"Using efficient chunk retrieval for {book_id}: {first_chunk} to {last_chunk}")
                
            # Get chunks using the book_id filter (still efficient with indexing)
            results = self.collection.get(
                where={"book_id": book_id},
                include=["documents", "metadatas"],
                limit=limit
            )
            
            # Sort by chunk_id for logical reading order
            if results['metadatas']:
                combined = list(zip(results['documents'], results['metadatas'], results['ids']))
                combined.sort(key=lambda x: x[1].get('chunk_id', 0))
                
                sorted_docs, sorted_metas, sorted_ids = zip(*combined)
                
                response = {
                    'book_id': book_id,
                    'chunk_count': len(sorted_docs),
                    'chunks': list(sorted_docs),
                    'metadatas': list(sorted_metas),
                    'ids': list(sorted_ids)
                }
                
                # Add page information summary if requested
                if include_page_info and sorted_metas:
                    page_info = {
                        'has_page_data': any('page_start' in meta for meta in sorted_metas if meta),
                        'page_range': None,
                        'page_types': set()
                    }
                    
                    page_starts = []
                    page_ends = []
                    for meta in sorted_metas:
                        if meta:
                            if 'page_start' in meta:
                                page_starts.append(meta['page_start'])
                            if 'page_end' in meta:
                                page_ends.append(meta['page_end'])
                            if 'page_type' in meta:
                                page_info['page_types'].add(meta['page_type'])
                    
                    if page_starts and page_ends:
                        page_info['page_range'] = f"Pages {min(page_starts)}-{max(page_ends)}"
                    
                    page_info['page_types'] = list(page_info['page_types'])
                    response['page_info'] = page_info
                
                return response
            
            return {
                'book_id': book_id, 
                'chunk_count': 0, 
                'chunks': [], 
                'metadatas': [], 
                'ids': []
            }
            
        except Exception as e:
            logger.error(f"Error retrieving chunks for book {book_id}: {e}")
            return {'book_id': book_id, 'chunk_count': 0, 'chunks': [], 'metadatas': [], 'ids': []}
    
    def get_book_chunks_by_page(self, book_id: str, start_page: int = None, end_page: int = None, 
                               page_type: str = None) -> Dict[str, Any]:
        """
        Get chunks from a book by page range using stored page metadata
        
        Args:
            book_id: Book identifier
            start_page: Starting page number (inclusive)
            end_page: Ending page number (inclusive) 
            page_type: Filter by page type ('actual' or 'estimated')
            
        Returns:
            Dictionary with chunks, their page info, and metadata
        """
        try:
            # ChromaDB doesn't support MongoDB-style operators, so we need to get all chunks
            # for the book and filter them manually
            results = self.collection.get(
                where={"book_id": book_id},
                include=["documents", "metadatas"]
            )
            
            # Filter by page range manually
            filtered_results = {'documents': [], 'metadatas': [], 'ids': []}
            
            if results['metadatas']:
                for doc, meta, doc_id in zip(results['documents'], results['metadatas'], results['ids']):
                    if meta:
                        page_start = meta.get('page_start')
                        page_end = meta.get('page_end')
                        meta_page_type = meta.get('page_type')
                        
                        # Apply filters
                        include_chunk = True
                        
                        if start_page is not None and page_start is not None:
                            if page_start < start_page:
                                include_chunk = False
                        
                        if end_page is not None and page_end is not None:
                            if page_end > end_page:
                                include_chunk = False
                        
                        if page_type and meta_page_type != page_type:
                            include_chunk = False
                        
                        if include_chunk:
                            filtered_results['documents'].append(doc)
                            filtered_results['metadatas'].append(meta)
                            filtered_results['ids'].append(doc_id)
            
            # Sort by page_start for logical reading order
            if filtered_results['metadatas']:
                combined = list(zip(filtered_results['documents'], filtered_results['metadatas'], filtered_results['ids']))
                combined.sort(key=lambda x: x[1].get('page_start', 0))
                
                sorted_docs, sorted_metas, sorted_ids = zip(*combined)
                
                return {
                    'book_id': book_id,
                    'chunk_count': len(sorted_docs),
                    'chunks': list(sorted_docs),
                    'metadatas': list(sorted_metas),
                    'ids': list(sorted_ids),
                    'page_range': f"Pages {start_page or 'start'}-{end_page or 'end'}"
                }
            
            return {'book_id': book_id, 'chunk_count': 0, 'chunks': [], 'metadatas': [], 'ids': []}
            
        except Exception as e:
            logger.error(f"Error retrieving chunks by page for book {book_id}: {e}")
            return {'book_id': book_id, 'chunk_count': 0, 'chunks': [], 'metadatas': [], 'ids': []}
    
    def get_book_chunks_paginated(self, book_id: str, page: int = 1, page_size: int = 100) -> Dict[str, Any]:
        """
        Get chunks from a book using pagination (chunk-based, not page-based)
        
        Args:
            book_id: Book identifier
            page: Page number (1-based)
            page_size: Number of chunks per page
            
        Returns:
            Dictionary with paginated chunks and pagination info
        """
        try:
            # Get all chunks for this book to determine actual count and apply pagination
            all_chunks = self.collection.get(
                where={"book_id": book_id},
                include=["documents", "metadatas"]
            )
            
            if not all_chunks['metadatas']:
                return {
                    'book_id': book_id, 
                    'chunk_count': 0, 
                    'chunks': [], 
                    'metadatas': [], 
                    'ids': [],
                    'pagination': {'current_page': page, 'page_size': page_size, 'total_pages': 0, 'total_chunks': 0}
                }
            
            # Sort by chunk_id for consistent ordering
            combined = list(zip(all_chunks['documents'], all_chunks['metadatas'], all_chunks['ids']))
            combined.sort(key=lambda x: x[1].get('chunk_id', 0))
            
            total_chunks = len(combined)
            total_pages = (total_chunks + page_size - 1) // page_size
            
            # Calculate offset and apply pagination
            offset = (page - 1) * page_size
            paginated = combined[offset:offset + page_size]
            
            if paginated:
                docs, metas, ids = zip(*paginated)
                
                return {
                    'book_id': book_id,
                    'chunk_count': len(docs),
                    'chunks': list(docs),
                    'metadatas': list(metas),
                    'ids': list(ids),
                    'pagination': {
                        'current_page': page,
                        'page_size': page_size,
                        'total_pages': total_pages,
                        'total_chunks': total_chunks,
                        'has_next': page < total_pages,
                        'has_prev': page > 1
                    }
                }
            
            return {
                'book_id': book_id, 
                'chunk_count': 0, 
                'chunks': [], 
                'metadatas': [], 
                'ids': [],
                'pagination': {'current_page': page, 'page_size': page_size, 'total_pages': 0, 'total_chunks': 0}
            }
            
        except Exception as e:
            logger.error(f"Error getting paginated chunks for book {book_id}: {e}")
            return {'book_id': book_id, 'chunk_count': 0, 'chunks': [], 'metadatas': [], 'ids': []}
    
    def get_book_page_summary(self, book_id: str) -> Dict[str, Any]:
        """
        Get a summary of page information for a book
        
        Args:
            book_id: Book identifier
            
        Returns:
            Dictionary with page statistics and ranges
        """
        try:
            # Get all chunk metadata for page analysis
            results = self.collection.get(
                where={"book_id": book_id},
                include=["metadatas"]
            )
            
            if not results['metadatas']:
                return {'book_id': book_id, 'error': 'No chunks found'}
            
            page_starts = []
            page_ends = []
            page_types = set()
            total_pages = 0
            
            for meta in results['metadatas']:
                if meta:
                    if 'page_start' in meta:
                        page_starts.append(meta['page_start'])
                    if 'page_end' in meta:
                        page_ends.append(meta['page_end'])
                    if 'page_type' in meta:
                        page_types.add(meta['page_type'])
                    if 'total_pages' in meta:
                        total_pages = max(total_pages, meta['total_pages'])
            
            return {
                'book_id': book_id,
                'chunk_count': len(results['metadatas']),
                'page_range': {
                    'first_page': min(page_starts) if page_starts else None,
                    'last_page': max(page_ends) if page_ends else None,
                    'total_pages': total_pages
                },
                'page_types': list(page_types),
                'coverage': {
                    'chunks_with_page_info': len([m for m in results['metadatas'] if m and 'page_start' in m]),
                    'total_chunks': len(results['metadatas'])
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting page summary for book {book_id}: {e}")
            return {'book_id': book_id, 'error': str(e)}

    def update_registry_with_chunk_info(self, book_id: str = None) -> bool:
        """
        Update book registry entries with chunk offset information for efficient retrieval
        
        Args:
            book_id: Specific book to update, or None to update all books
            
        Returns:
            True if successful
        """
        try:
            if book_id:
                # Update single book
                book_ids_to_update = [book_id]
            else:
                # Update all books that don't have chunk info
                registry_results = self.book_registry.get(include=["metadatas"])
                book_ids_to_update = []
                
                for i, metadata in enumerate(registry_results.get('metadatas', [])):
                    if metadata and not metadata.get('first_chunk_id'):
                        # This book doesn't have chunk offset info yet
                        book_id = metadata.get('book_id')
                        if book_id:
                            book_ids_to_update.append(book_id)
            
            for book_id in book_ids_to_update:
                # Get all chunk IDs for this book
                chunk_results = self.collection.get(
                    where={"book_id": book_id},
                    include=[]  # Only need IDs
                )
                
                if chunk_results['ids']:
                    chunk_ids = sorted(chunk_results['ids'])  # Sort for consistent ordering
                    
                    # Get existing book metadata from registry
                    registry_book = self.book_registry.get(ids=[book_id])
                    if registry_book['metadatas']:
                        existing_metadata = registry_book['metadatas'][0].copy()
                        
                        # Add chunk tracking information
                        existing_metadata.update({
                            'chunk_count': len(chunk_ids),
                            'first_chunk_id': chunk_ids[0],
                            'last_chunk_id': chunk_ids[-1],
                            'chunk_id_pattern': f"{book_id}_chunk_*",
                            'chunk_range': f"{chunk_ids[0]} to {chunk_ids[-1]}"
                        })
                        
                        # Update the registry
                        self.book_registry.update(
                            ids=[book_id],
                            metadatas=[existing_metadata]
                        )
                        
                        logger.debug(f"Updated registry for {book_id} with {len(chunk_ids)} chunk references")
            
            logger.info(f"Updated chunk offset information for {len(book_ids_to_update)} books")
            return True
            
        except Exception as e:
            logger.error(f"Error updating registry with chunk info: {e}")
            return False
    
    def _calculate_optimal_batch_size(self, sample_doc: str = None, sample_metadata: Dict = None, 
                                    total_items: int = 1000, target_memory_usage_mb: int = 100) -> int:
        """
        Calculate optimal batch size based on available memory and item size
        
        Args:
            sample_doc: Sample document text to estimate size
            sample_metadata: Sample metadata to estimate size  
            total_items: Total number of items to process
            target_memory_usage_mb: Target memory usage in MB for batch processing
            
        Returns:
            Optimal batch size (between 50 and 2000), or config override if set
        """
        # Check for config override first
        override = self.config.get("rag.batch_size_override")
        if override is not None:
            logger.info(f"📊 Config override: Using fixed batch size {override}")
            return int(override)
        
        try:
            # Get available memory if psutil is available
            if HAS_PSUTIL:
                memory = psutil.virtual_memory()
                available_mb = memory.available / (1024 * 1024)
                total_mb = memory.total / (1024 * 1024)
                # Use conservative percentage of available memory
                safe_memory_mb = min(target_memory_usage_mb, available_mb * 0.1)  # Max 10% of available
                logger.info(f"💾 Memory: {available_mb:.1f}MB available / {total_mb:.1f}MB total, using {safe_memory_mb:.1f}MB for batching")
            else:
                # Fallback: assume reasonable amount of available memory (2GB)
                available_mb = 2048  # 2GB fallback
                safe_memory_mb = min(target_memory_usage_mb, 200)  # Conservative 200MB max
                logger.info("💾 psutil not available, using conservative memory estimates (200MB max)")

            # Estimate item size
            if sample_doc and sample_metadata:
                # Estimate size of one item (doc + metadata + embedding space + overhead)
                doc_size = sys.getsizeof(sample_doc)
                meta_size = sys.getsizeof(str(sample_metadata))
                embedding_size = 384 * 4  # ~384 dimensions * 4 bytes per float
                overhead = 200  # Additional overhead per item
                
                item_size_bytes = doc_size + meta_size + embedding_size + overhead
                item_size_mb = item_size_bytes / (1024 * 1024)
                logger.info(f"📏 Item size estimation: doc={doc_size}B, meta={meta_size}B, embedding={embedding_size}B → {item_size_mb*1024:.1f}KB per item")
            else:
                # Conservative estimate: ~2KB per document + metadata + embedding
                item_size_mb = 0.002  # 2KB average
                logger.info("📏 Using conservative item size estimate: 2KB per item")
            
            # Calculate batch size based on memory constraint
            if item_size_mb > 0:
                memory_based_batch = int(safe_memory_mb / item_size_mb)
            else:
                memory_based_batch = 500  # Fallback
            
            # Apply reasonable bounds
            batch_size = max(50, min(2000, memory_based_batch))
            
            # Additional constraint: don't make batches too large for small datasets
            if total_items < 200:
                batch_size = min(batch_size, max(10, total_items // 2))
                logger.info(f"🔧 Adjusted batch size for small dataset: {batch_size}")
            
            total_batches = (total_items + batch_size - 1) // batch_size
            reduction_pct = 100 * (1 - total_batches / total_items) if total_items > 0 else 0
            
            logger.info(f"🚀 Final batch size: {batch_size} for {total_items:,} items → {total_batches} batches ({reduction_pct:.1f}% transaction reduction)")
            
            return batch_size
            
        except Exception as e:
            logger.warning(f"Error calculating optimal batch size: {e}, using default 500")
            return 500
    
    def batch_insert_chunks(self, documents: List[str], metadatas: List[Dict], ids: List[str], 
                           batch_size: int = None, show_progress: bool = False) -> bool:
        """
        Insert documents in batches for better performance
        
        Args:
            documents: List of document texts
            metadatas: List of metadata dictionaries
            ids: List of document IDs
            batch_size: Number of documents per batch
            show_progress: Whether to log progress
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if len(documents) != len(metadatas) or len(documents) != len(ids):
                logger.error("Documents, metadatas, and ids must have the same length")
                return False
            
            total_docs = len(documents)
            total_batches = (total_docs + batch_size - 1) // batch_size
            
            if show_progress:
                logger.info(f"Inserting {total_docs} documents in {total_batches} batches of {batch_size}")
            
            for batch_idx in range(total_batches):
                start_idx = batch_idx * batch_size
                end_idx = min(start_idx + batch_size, total_docs)
                
                batch_docs = documents[start_idx:end_idx]
                batch_metas = metadatas[start_idx:end_idx]
                batch_ids = ids[start_idx:end_idx]
                
                try:
                    self.collection.add(
                        documents=batch_docs,
                        metadatas=batch_metas,
                        ids=batch_ids
                    )
                    
                    if show_progress:
                        logger.debug(f"Batch {batch_idx + 1}/{total_batches} completed ({len(batch_docs)} docs)")
                        
                except Exception as e:
                    logger.error(f"Error inserting batch {batch_idx + 1}/{total_batches}: {e}")
                    return False
            
            if show_progress:
                logger.info(f"Successfully inserted all {total_docs} documents")
            
            return True
            
        except Exception as e:
            logger.error(f"Error in batch insert: {e}")
            return False

    def book_exists(self, book_id: str) -> bool:
        """
        Check if book already exists in the database
        
        Args:
            book_id: Unique identifier for the book
            
        Returns:
            True if book exists, False otherwise
        """
        try:
            # Check the book registry first (much faster than scanning chunks)
            try:
                registry_results = self.book_registry.get(ids=[book_id])
                if registry_results['ids']:
                    return True
            except Exception:
                # Registry might not exist or have issues, fall back to chunk check
                pass
            
            # Fallback to checking the main collection 
            collection_results = self.collection.get(
                where={"book_id": book_id},
                limit=1
            )
            return len(collection_results['ids']) > 0
        except Exception as e:
            logger.error(f"Error checking if book exists: {e}")
            return False
    
    @timing_decorator("List Books")
    def list_books(self) -> List[Dict]:
        """
        List all books in the database using the book registry
        
        Returns:
            List of dictionaries with book information
        """
        try:
            with detailed_timer("Book Registry Query", show_analysis=True) as timer:
                # Get all books from the registry - this should be very fast
                registry_results = self.book_registry.get(include=["metadatas"])
                books = []
                
                for metadata in registry_results.get('metadatas', []):
                    if metadata:
                        # Try both 'chunk_count' (new) and 'chunks' (legacy) for backward compatibility
                        chunk_count = metadata.get('chunk_count', metadata.get('chunks', 0))
                        books.append({
                            'book_id': metadata.get('book_id', 'Unknown'),
                            'title': metadata.get('title', 'Unknown'),
                            'author': metadata.get('author', 'Unknown'),
                            'format': metadata.get('format', 'Unknown'),
                            'file_hash': metadata.get('file_hash', ''),
                            'chunks': chunk_count,
                            # Add additional chunk tracking info if available
                            'chunk_range': metadata.get('chunk_range', ''),
                            'first_chunk_id': metadata.get('first_chunk_id', ''),
                            'last_chunk_id': metadata.get('last_chunk_id', '')
                        })
                
                timer.set_result_count(len(books))
            
            # If registry is empty, fall back to the old method and populate registry
            if not books:
                print("📝 Book registry is empty, populating from chunks...")
                books = self._populate_book_registry()
            
            # Sort results
            with Timer("Sorting Results", verbose=True):
                result = sorted(books, key=lambda x: x['title'])
                total_chunks = sum(book.get('chunks', 0) for book in result)
                print(f"📊 Found {len(result)} books with {total_chunks} total chunks")
            
            return result
            
        except Exception as e:
            logger.error(f"Error listing books from registry: {e}")
            # Fallback to scanning chunks if registry fails
            return self._list_books_fallback()
    
    def _populate_book_registry(self) -> List[Dict]:
        """Populate the book registry from existing chunks in the database"""
        try:
            print("🔄 Scanning chunks to build book registry...")
            
            # Get all chunk metadata
            all_results = self.collection.get(include=["metadatas"])
            book_data = {}
            
            # Group by book_id and count chunks
            for meta in all_results.get('metadatas', []):
                if not meta or 'book_id' not in meta:
                    continue
                    
                book_id = meta['book_id']
                if book_id not in book_data:
                    title = meta.get('book_title') or meta.get('title') or 'Unknown'
                    author = meta.get('author') or 'Unknown'
                    # Derive from filename if needed
                    if title == 'Unknown' and author == 'Unknown':
                        file_path = meta.get('file_path', '')
                        if file_path:
                            from pathlib import Path as _P
                            stem = _P(file_path).stem
                            # If filename contains ' by ', split for author
                            if ' by ' in stem.lower():
                                parts = stem.split(' by ', 1)
                                title = parts[0].strip() if parts[0].strip() else 'Unknown'
                                author = parts[1].strip() if len(parts) > 1 and parts[1].strip() else 'Unknown'
                            else:
                                title = stem.strip() or 'Unknown'
                    
                    book_data[book_id] = {
                        'book_id': book_id,
                        'title': title,
                        'author': author,
                        'format': meta.get('format', 'Unknown'),
                        'file_hash': meta.get('file_hash', ''),
                        'file_path': meta.get('file_path', ''),
                        'chunks': 0
                    }
                
                book_data[book_id]['chunks'] += 1
            
            # Register all books in the registry
            for book_id, book_info in book_data.items():
                self.register_book(book_id, book_info)
            
            print(f"✅ Populated book registry with {len(book_data)} books")
            return list(book_data.values())
            
        except Exception as e:
            logger.error(f"Error populating book registry: {e}")
            return []

    def _list_books_fallback(self) -> List[Dict]:
        """Fallback method for listing books when optimized approach fails"""
        try:
            print("⚠️  Using fallback method - this may be slower...")
            with detailed_timer("Database Query - Full Metadata (Fallback)", show_analysis=True) as timer:
                results = self.collection.get(include=["metadatas"])
                metadatas_raw = results.get('metadatas') or []
                ids_raw = results.get('ids') or []
                timer.set_result_count(len(ids_raw))

            if not metadatas_raw:
                return []

            # Process metadata efficiently
            book_data = {}
            id_counts = {}
            
            # Count chunks per book from IDs
            for doc_id in ids_raw:
                if isinstance(doc_id, str) and '_chunk_' in doc_id:
                    book_id = doc_id.split('_chunk_')[0]
                    id_counts[book_id] = id_counts.get(book_id, 0) + 1
            
            # Process metadata
            for meta in metadatas_raw:
                if not isinstance(meta, dict):
                    continue
                    
                book_id = meta.get('book_id')
                if not book_id or book_id in book_data:
                    continue
                    
                title = meta.get('book_title') or meta.get('title') or 'Unknown'
                author = meta.get('author') or 'Unknown'
                
                book_data[book_id] = {
                    'book_id': book_id,
                    'title': title,
                    'author': author,
                    'format': meta.get('format', 'Unknown'),
                    'file_hash': meta.get('file_hash', ''),
                    'chunks': id_counts.get(book_id, 0)
                }

            return sorted(book_data.values(), key=lambda x: x['title'])
            
        except Exception as e:
            logger.error(f"Error in fallback list_books: {e}")
            return []
    
    def remove_book(self, book_id: str) -> bool:
        """
        Remove all chunks for a specific book
        
        Args:
            book_id: Unique identifier for the book to remove
            
        Returns:
            True if book was removed, False otherwise
        """
        try:
            # Remove chunks from main collection
            results = self.collection.get(where={"book_id": book_id})
            if results['ids']:
                self.collection.delete(ids=results['ids'])
                logger.info(f"Removed {len(results['ids'])} chunks for book {book_id}")
                
                # Also remove from book registry
                try:
                    self.book_registry.delete(ids=[book_id])
                    logger.debug(f"Removed book {book_id} from registry")
                except Exception as e:
                    logger.warning(f"Could not remove book {book_id} from registry: {e}")
                
                return True
            else:
                logger.warning(f"No chunks found for book {book_id}")
                return False
        except Exception as e:
            logger.error(f"Error removing book {book_id}: {e}")
            return False
    
    def _build_add_result(self,
                          success: bool,
                          action: str,
                          book_id: Optional[str] = None,
                          title: Optional[str] = None,
                          author: Optional[str] = None,
                          chunks: int = 0,
                          message: Optional[str] = None,
                          error: Optional[str] = None,
                          skipped: bool = False,
                          metadata: Optional[Dict] = None) -> Dict[str, Any]:
        return {
            'success': success,
            'action': action,
            'book_id': book_id,
            'title': title,
            'author': author,
            'chunks_added': chunks,
            'message': message,
            'error': error,
            'skipped': skipped,
            'metadata': metadata or {}
        }

    def embed_chunks(self, chunk_texts: list, show_progress_bar: bool = True):
        """
        Centralized embedding logic for chunk texts.
        Returns list of embeddings.
        """
        try:
            return self.encoder.encode(chunk_texts, show_progress_bar=show_progress_bar)
        except Exception as e:
            logger.error(f"Error encoding embeddings: {e}")
            raise

    def add_ebook_with_pages(self, file_path: str, overwrite: bool = False) -> Dict[str, Any]:
        """
        Add an ebook to the RAG database with page-aware content extraction
        
        Args:
            file_path: Path to the ebook file
            overwrite: Whether to overwrite existing book
            
        Returns:
            Status message
        """
        start_time = time.time()
        try:
            from ai_ebook_processor.readers.ebook_reader import EbookReader
            from ai_ebook_processor.core.pipeline import TextChunker, ProcessingConfig
            
            logger.info(f"⏱️ Starting to add book with pages: '{file_path}'")
            
            # Read ebook with page information
            reader = EbookReader()
            text_content, metadata, page_info = reader.read_ebook_with_pages(file_path)
            
            # Create book ID
            file_hash = self.get_file_hash(file_path)
            base_book_id = f"{metadata.get('title', 'unknown')}_{metadata.get('author', 'unknown')}"
            base_book_id = base_book_id.replace(' ', '_').replace('/', '_').replace('\\', '_')
            book_id = f"{base_book_id}_{file_hash[:8]}"
            
            # Check if book already exists
            if self.book_exists(book_id):
                if not overwrite:
                    msg = f"Book {book_id} already exists, skipped"
                    logger.warning(msg)
                    return self._build_add_result(False, 'add_pages', book_id, metadata.get('title'), metadata.get('author'), 0, msg, skipped=True, metadata=metadata)
                else:
                    self.remove_book(book_id)
                    logger.info(f"Overwriting existing book {book_id}")
            
            # Create chunks with page awareness
            config = ProcessingConfig(
                chunk_size=self.config.get('processing.chunk_size', 4000),
                chunk_overlap=self.config.get('processing.chunk_overlap', 200)
            )
            chunker = TextChunker(config)
            import click
            click.echo(f"Chunking text for '{metadata.get('title')}'...")
            chunk_infos = chunker.chunk_text_with_pages(text_content, page_info)

            if not chunk_infos:
                msg = f"No chunks created for {book_id}"
                logger.warning(msg)
                click.echo(msg)
                return self._build_add_result(False, 'add_pages', book_id, metadata.get('title'), metadata.get('author'), 0, msg, error=msg, metadata=metadata)

            click.echo(f"Storing {len(chunk_infos)} chunks in database...")
            # Prepare batch data for efficient insertion
            all_documents = []
            all_metadatas = []
            all_ids = []
            for chunk_info in chunk_infos:
                doc_id = f"{book_id}_chunk_{chunk_info.index}"
                chunk_metadata = {
                    'book_title': metadata.get('title', 'Unknown'),
                    'author': metadata.get('author', 'Unknown'),
                    'format': metadata.get('format', 'Unknown'),
                    'chunk_id': chunk_info.index,
                    'book_id': book_id,
                    'file_hash': file_hash,
                    'file_path': str(file_path),
                    'page_start': chunk_info.page_start,
                    'page_end': chunk_info.page_end,
                    'page_type': chunk_info.page_type,  # 'actual' or 'estimated'
                    'total_pages': metadata.get('pages', 0)
                }
                all_documents.append(chunk_info.text)
                all_metadatas.append(chunk_metadata)
                all_ids.append(doc_id)

            # Calculate optimal batch size based on available memory
            sample_doc = all_documents[0] if all_documents else None
            sample_meta = all_metadatas[0] if all_metadatas else None
            batch_size = self._calculate_optimal_batch_size(
                sample_doc=sample_doc,
                sample_metadata=sample_meta,
                total_items=len(all_documents)
            )
            total_batches = (len(all_documents) + batch_size - 1) // batch_size
            stored_chunk_ids = all_ids.copy()  # For cleanup if cancelled

            click.echo("Encoding chunks to embeddings...")
            try:
                embeddings = self.embed_chunks(all_documents, show_progress_bar=True)
            except Exception as e:
                click.echo(f"Error encoding embeddings: {e}")
                return self._build_add_result(False, 'add_pages', book_id, metadata.get('title'), metadata.get('author'), 0, "Embedding error", error=str(e), metadata=metadata)

            try:
                for batch_idx in range(total_batches):
                    start_idx = batch_idx * batch_size
                    end_idx = min(start_idx + batch_size, len(all_documents))

                    batch_docs = all_documents[start_idx:end_idx]
                    batch_metas = all_metadatas[start_idx:end_idx]
                    batch_ids = all_ids[start_idx:end_idx]
                    batch_embeddings = embeddings[start_idx:end_idx]
                    self.collection.add(
                        documents=batch_docs,
                        metadatas=batch_metas,
                        ids=batch_ids,
                        embeddings=batch_embeddings
                    )
                    # Print progress every batch or at the end
                    progress = min(end_idx, len(chunk_infos))
                    click.echo(f"  Stored batch {batch_idx + 1}/{total_batches} - {progress}/{len(chunk_infos)} chunks")
            except KeyboardInterrupt:
                click.echo("\nProcessing cancelled by user. Cleaning up partial book...")
                if stored_chunk_ids:
                    self.collection.delete(ids=stored_chunk_ids)
                    click.echo(f"Removed {len(stored_chunk_ids)} partial chunks for '{metadata.get('title')}'")
                return self._build_add_result(False, 'add_pages', book_id, metadata.get('title'), metadata.get('author'), len(stored_chunk_ids), "Processing cancelled and cleaned up.", error="Cancelled", metadata=metadata)

            # Register the book in the registry for fast listing with chunk tracking
            book_registry_metadata = {
                'book_id': book_id,
                'title': metadata.get('title', 'Unknown'),
                'author': metadata.get('author', 'Unknown'),
                'format': metadata.get('format', 'Unknown'),
                'file_hash': file_hash,
                'file_path': str(file_path),
                'chunks': len(chunk_infos)
            }
            self.register_book(book_id, book_registry_metadata, stored_chunk_ids)

            elapsed_time = time.time() - start_time
            success_msg = f"Added {len(chunk_infos)} chunks of size {config.chunk_size} with page citations for '{metadata.get('title')}' to RAG database in {elapsed_time:.2f}s"
            logger.info(f"✅ {success_msg}")
            click.echo(success_msg)
            return self._build_add_result(True, 'add_pages', book_id, metadata.get('title'), metadata.get('author'), len(chunk_infos), success_msg, metadata=metadata)
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            error_msg = f"Error adding ebook with pages to RAG database after {elapsed_time:.2f}s: {e}"
            logger.error(f"❌ {error_msg}")
            return self._build_add_result(False, 'add_pages', message=error_msg, error=str(e))

    def add_processed_ebook(self, result: Dict, file_path: str = None, overwrite: bool = False) -> Dict[str, Any]:
        """
        Add a processed ebook result to the RAG database with duplicate detection
        
        Args:
            result: Processing result from EbookProcessorApp
            file_path: Path to original file (for hash-based deduplication)
            overwrite: Whether to overwrite existing book
            
        Returns:
            Status message indicating what happened
        """
        start_time = time.time()
        try:
            # Extract metadata
            metadata = result['metadata']
            title = metadata.get('title', 'Unknown')
            logger.info(f"⏱️ Starting to add book: '{title}'")
            base_book_id = f"{metadata.get('title', 'unknown')}_{metadata.get('author', 'unknown')}"
            base_book_id = base_book_id.replace(' ', '_').replace('/', '_').replace('\\', '_')
            
            # Add file hash for better deduplication if file_path provided
            file_hash = ""
            if file_path and os.path.exists(file_path):
                file_hash = self.get_file_hash(file_path)
                book_id = f"{base_book_id}_{file_hash[:8]}"  # Use first 8 chars of hash
            else:
                book_id = base_book_id
            
            # Check if book already exists
            if self.book_exists(book_id):
                if not overwrite:
                    msg = f"Book {book_id} already exists, skipped"
                    logger.warning(msg)
                    return self._build_add_result(False, 'add_processed', book_id, metadata.get('title'), metadata.get('author'), 0, msg, skipped=True, metadata=metadata)
                else:
                    # Remove existing book
                    self.remove_book(book_id)
                    logger.info(f"Overwriting existing book {book_id}")
            
            # Prefer raw canonical text (list of original chunk texts) over LLM combined summaries
            raw_chunks = result.get('raw_chunks') or []
            if raw_chunks:
                chunks = raw_chunks
            else:
                content = result.get('raw_text') or result.get('combined_result', '')
                if not content:
                    msg = f"No content found for {book_id}"
                    logger.warning(msg)
                    return self._build_add_result(False, 'add_processed', book_id, metadata.get('title'), metadata.get('author'), 0, msg, error=msg, metadata=metadata)
                chunks = self._chunk_content(content, chunk_size=self.config.get('processing.chunk_size', 1000))
            
            if not chunks:
                msg = f"No chunks created for {book_id}"
                logger.warning(msg)
                return self._build_add_result(False, 'add_processed', book_id, metadata.get('title'), metadata.get('author'), 0, msg, error=msg, metadata=metadata)
            
            # Prepare batch data for efficient insertion
            all_documents = []
            all_metadatas = []
            all_ids = []
            for i, chunk in enumerate(chunks):
                doc_id = f"{book_id}_chunk_{i}"
                chunk_metadata = {
                    'book_title': metadata.get('title', 'Unknown'),
                    'author': metadata.get('author', 'Unknown'),
                    'format': metadata.get('format', 'Unknown'),
                    'chunk_id': i,
                    'book_id': book_id
                }
                # Add file hash to metadata if available
                if file_hash:
                    chunk_metadata['file_hash'] = file_hash
                if file_path:
                    chunk_metadata['file_path'] = str(file_path)
                all_documents.append(chunk)
                all_metadatas.append(chunk_metadata)
                all_ids.append(doc_id)

            # Calculate optimal batch size based on available memory
            sample_doc = all_documents[0] if all_documents else None
            sample_meta = all_metadatas[0] if all_metadatas else None
            batch_size = self._calculate_optimal_batch_size(
                sample_doc=sample_doc,
                sample_metadata=sample_meta,
                total_items=len(all_documents)
            )
            total_batches = (len(all_documents) + batch_size - 1) // batch_size

            logger.info(f"Inserting {len(chunks)} chunks in {total_batches} batches of {batch_size} (auto-calculated)")

            # Import click for progress display
            import click
            click.echo(f"Storing {len(chunks)} chunks in database...")

            click.echo("Encoding chunks to embeddings...")
            try:
                embeddings = self.embed_chunks(all_documents, show_progress_bar=True)
            except Exception as e:
                click.echo(f"Error encoding embeddings: {e}")
                return self._build_add_result(False, 'add_processed', book_id, metadata.get('title'), metadata.get('author'), 0, "Embedding error", error=str(e), metadata=metadata)
            
            # Calculate optimal batch size based on available memory
            sample_doc = all_documents[0] if all_documents else None
            sample_meta = all_metadatas[0] if all_metadatas else None
            batch_size = self._calculate_optimal_batch_size(
                sample_doc=sample_doc,
                sample_metadata=sample_meta,
                total_items=len(all_documents)
            )
            total_batches = (len(all_documents) + batch_size - 1) // batch_size
            
            logger.info(f"Inserting {len(chunks)} chunks in {total_batches} batches of {batch_size} (auto-calculated)")
            
            # Import click for progress display
            import click
            click.echo(f"Storing {len(chunks)} chunks in database...")
            
            for batch_idx in range(total_batches):
                start_idx = batch_idx * batch_size
                end_idx = min(start_idx + batch_size, len(all_documents))
                
                batch_docs = all_documents[start_idx:end_idx]
                batch_metas = all_metadatas[start_idx:end_idx]
                batch_ids = all_ids[start_idx:end_idx]
                
                try:
                    self.collection.add(
                        documents=batch_docs,
                        metadatas=batch_metas,
                        ids=batch_ids
                    )
                    # Show progress like add_ebook_with_pages does
                    progress = min(end_idx, len(chunks))
                    click.echo(f"  Stored batch {batch_idx + 1}/{total_batches} - {progress}/{len(chunks)} chunks")
                except Exception as e:
                    logger.error(f"Error inserting batch {batch_idx + 1}: {e}")
                    click.echo(f"  ❌ Error in batch {batch_idx + 1}/{total_batches}: {e}")
                    # Continue with next batch rather than failing completely
                    continue
            
            # Register the book in the registry for fast listing with chunk tracking
            book_registry_metadata = {
                'book_id': book_id,
                'title': metadata.get('title', 'Unknown'),
                'author': metadata.get('author', 'Unknown'),
                'format': metadata.get('format', 'Unknown'),
                'file_hash': file_hash,
                'file_path': str(file_path) if file_path else '',
                'chunks': len(chunks)
            }
            self.register_book(book_id, book_registry_metadata, all_ids)

            elapsed_time = time.time() - start_time
            success_msg = f"Added {len(chunks)} chunks for '{metadata.get('title')}' to RAG database in {elapsed_time:.2f}s"
            logger.info(f"✅ {success_msg}")
            click.echo(success_msg)  # Show user-visible success message
            return self._build_add_result(True, 'add_processed', book_id, metadata.get('title'), metadata.get('author'), len(chunks), success_msg, metadata=metadata)
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            error_msg = f"Error adding ebook to RAG database after {elapsed_time:.2f}s: {e}"
            logger.error(f"❌ {error_msg}")
            return self._build_add_result(False, 'add_processed', message=error_msg, error=str(e))
    
    def add_multiple_ebooks(self, results: List[Dict]) -> None:
        """Add multiple processed ebooks to the database.

        Returns list of standardized result dicts for each add attempt.
        """
        added_results = []
        for result in results:
            try:
                added_results.append(self.add_processed_ebook(result))
            except Exception as e:
                added_results.append(self._build_add_result(False, 'add_processed', message=f"Unhandled error: {e}", error=str(e)))
        return added_results
    
    def add_multiple_ebooks_batch(self, results: List[Dict], batch_size: int = None) -> Dict[str, Any]:
        """
        Add multiple processed ebooks to the database with batch optimization.
        
        Args:
            results: List of processed ebook results
            batch_size: Number of chunks to batch together (None for auto-calculation)
            
        Returns:
            Dictionary with batch processing statistics
        """
        stats = {
            'total_books': len(results),
            'successful_books': 0,
            'failed_books': 0,
            'total_chunks': 0,
            'processing_time': 0,
            'errors': []
        }
        
        import time
        start_time = time.time()
        
        try:
            # Collect all chunks from all books for batch processing
            all_texts = []
            all_metadatas = []
            all_ids = []
            book_chunk_counts = {}
            books_to_register = {}  # Track books for registry registration
            book_chunk_ids = {}  # Track chunk IDs for each book
            
            for result in results:
                raw_chunks = result.get('raw_chunks')
                metadata = result.get('metadata', {})
                base_book_id = f"{metadata.get('title', 'unknown')}_{metadata.get('author', 'unknown')}"
                base_book_id = base_book_id.replace(' ', '_').replace('/', '_').replace('\\', '_')
                file_hash = ""
                if result.get('file_path') and os.path.exists(result.get('file_path')):
                    file_hash = self.get_file_hash(result['file_path'])
                    book_id = f"{base_book_id}_{file_hash[:8]}"
                else:
                    book_id = base_book_id
                    
                if not raw_chunks:
                    stats['failed_books'] += 1
                    stats['errors'].append(f"No raw chunks in result for {metadata.get('title', 'unknown')}")
                    continue
                    
                chunk_count = len(raw_chunks)
                stats['successful_books'] += 1
                stats['total_chunks'] += chunk_count
                book_chunk_counts[book_id] = chunk_count
                
                # Prepare book for registry registration
                books_to_register[book_id] = {
                    'book_id': book_id,
                    'title': metadata.get('title', 'Unknown'),
                    'author': metadata.get('author', 'Unknown'),
                    'format': metadata.get('format', 'Unknown'),
                    'file_hash': file_hash,
                    'file_path': str(result.get('file_path', '')),
                    'chunks': chunk_count
                }
                
                # Track chunk IDs for this book
                book_chunk_ids[book_id] = []
                
                for i, chunk in enumerate(raw_chunks):
                    doc_id = f"{book_id}_chunk_{i}"
                    chunk_metadata = {
                        'book_title': metadata.get('title', 'Unknown'),
                        'author': metadata.get('author', 'Unknown'),
                        'format': metadata.get('format', 'Unknown'),
                        'chunk_id': i,
                        'book_id': book_id
                    }
                    if file_hash:
                        chunk_metadata['file_hash'] = file_hash
                    if result.get('file_path'):
                        chunk_metadata['file_path'] = str(result['file_path'])
                    all_texts.append(chunk)
                    all_metadatas.append(chunk_metadata)
                    all_ids.append(doc_id)
                    
                    # Track this chunk ID for the book
                    book_chunk_ids[book_id].append(doc_id)
            
            # Calculate optimal batch size if not provided
            if batch_size is None:
                sample_doc = all_texts[0] if all_texts else None
                sample_meta = all_metadatas[0] if all_metadatas else None
                batch_size = self._calculate_optimal_batch_size(
                    sample_doc=sample_doc,
                    sample_metadata=sample_meta,
                    total_items=len(all_texts)
                )
                logger.info(f"Parallel processing: Auto-calculated batch size {batch_size} for {len(all_texts)} total chunks")
            
            # Batch add chunks to database
            total_batches = (len(all_texts) + batch_size - 1) // batch_size
            logger.info(f"Processing {len(all_texts)} chunks in {total_batches} batches of {batch_size}")
            
            # Import click for progress display
            import click
            click.echo(f"Batch processing {stats['successful_books']} books with {len(all_texts)} total chunks...")
            
            for i in range(0, len(all_texts), batch_size):
                batch_num = (i // batch_size) + 1
                end_idx = min(i + batch_size, len(all_texts))
                batch_texts = all_texts[i:end_idx]
                batch_metadatas = all_metadatas[i:end_idx]
                batch_ids = all_ids[i:end_idx]
                
                self.collection.add(
                    documents=batch_texts,
                    metadatas=batch_metadatas,
                    ids=batch_ids
                )
                
                # Show progress
                click.echo(f"  Processed batch {batch_num}/{total_batches} - {end_idx}/{len(all_texts)} chunks")
                
            # Register all books in the registry after successful batch processing
            for book_id, book_metadata in books_to_register.items():
                chunk_ids = book_chunk_ids.get(book_id, [])
                self.register_book(book_id, book_metadata, chunk_ids)
                
            stats['processing_time'] = time.time() - start_time
            logger.info(f"✅ Successfully added {stats['successful_books']} books with {stats['total_chunks']} chunks in {stats['processing_time']:.2f}s")
            
        except Exception as e:
            stats['processing_time'] = time.time() - start_time
            error_msg = f"Error in batch processing after {stats['processing_time']:.2f}s: {e}"
            stats['errors'].append(error_msg)
            logger.error(f"❌ {error_msg}")
        
        return stats
    
    def add_ebooks_parallel_batch(self, file_paths: List[str], max_workers: int = 3) -> Dict[str, Any]:
        """
        Process multiple ebooks in parallel and add them to the database in batches.
        
        Args:
            file_paths: List of ebook file paths
            max_workers: Number of parallel processing workers
            
        Returns:
            Dictionary with processing statistics
        """
        from concurrent.futures import ThreadPoolExecutor
        import time
        
        start_time = time.time()
        stats = {
            'total_files': len(file_paths),
            'successful_files': 0,
            'failed_files': 0,
            'total_chunks': 0,
            'processing_time': 0,
            'errors': []
        }
        
        def process_single_file(file_path: str) -> Dict[str, Any]:
            """Process a single ebook file and return standardized result wrapper."""
            try:
                add_result = self.add_ebook_with_pages(file_path, overwrite=False)
                return {
                    'success': add_result.get('success', False),
                    'file_path': file_path,
                    'add_result': add_result,
                    'skipped': add_result.get('skipped', False),
                    'error': add_result.get('error')
                }
            except Exception as e:
                return {'success': False, 'file_path': file_path, 'error': str(e), 'add_result': None}
        
        # Process files in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(process_single_file, file_paths))
        
        # Collect statistics
        for r in results:
            if r.get('success'):
                stats['successful_files'] += 1
            else:
                if r.get('skipped'):
                    # treat skipped separately
                    pass
                else:
                    stats['failed_files'] += 1
                    stats['errors'].append(f"Failed to process {r.get('file_path')}: {r.get('error')}")
        
        stats['processing_time'] = time.time() - start_time
        logger.info(f"Parallel batch processing complete: {stats['successful_files']}/{stats['total_files']} files processed in {stats['processing_time']:.2f}s")
        
        return stats
    
    @timing_decorator("Search Books")
    def search_books(self, query: str, n_results: int = None) -> Dict:
        """
        Search for relevant content in your ebook collection
        
        Args:
            query: Search query
            n_results: Number of results to return
            
        Returns:
            Dictionary with search results including page citations
        """
        try:
            if n_results is None:
                n_results = self.config.get('rag.context_chunk_count', 5)
            with Timer(f"ChromaDB Query (n={n_results})"):
                results = self.collection.query(
                    query_texts=[query],
                    n_results=n_results
                )
            
            with Timer("Processing Search Results"):
                search_results = {
                    'query': query,
                    'results': []
                }
                
                if results['documents'] and results['documents'][0]:
                    for doc, meta, dist in zip(
                        results['documents'][0],
                        results['metadatas'][0], 
                        results['distances'][0]
                    ):
                        # Create citation information
                        citation_info = self._create_citation(meta)
                        
                        result_item = {
                            'content': doc,
                            'metadata': meta,
                            'distance': dist,
                            'similarity_score': 1 - dist,  # Convert distance to similarity
                            'citation': citation_info
                        }
                        search_results['results'].append(result_item)
            
            return search_results
            
        except Exception as e:
            logger.error(f"Error searching books: {e}")
            return {'query': query, 'results': []}
    
    def _create_citation(self, metadata: Dict) -> str:
        """
        Create a citation string from chunk metadata
        
        Args:
            metadata: Chunk metadata containing page and book information
            
        Returns:
            Formatted citation string
        """
        book_title = metadata.get('book_title', 'Unknown Title')
        author = metadata.get('author', 'Unknown Author')
        page_start = metadata.get('page_start')
        page_end = metadata.get('page_end')
        page_type = metadata.get('page_type', 'estimated')
        
        # Format basic citation
        citation = f"{author}. \"{book_title}\""
        
        # Add page information if available
        if page_start and page_end:
            if page_start == page_end:
                page_indicator = "(est. p." if page_type == 'estimated' else "(p."
                citation += f" {page_indicator} {page_start})"
            else:
                page_indicator = "(est. pp." if page_type == 'estimated' else "(pp."
                citation += f" {page_indicator} {page_start}-{page_end})"
        
        return citation
    
    @timing_decorator("Ask Question (Total)")
    def ask_question(self, question: str, ollama_processor, context_chunks: int = None, verbose: bool = False, book_filter: str = None) -> str:
        """
        Ask a question about your book collection using RAG
        
        Args:
            question: Question to ask
            ollama_processor: OllamaProcessor instance
            context_chunks: Number of relevant chunks to include
            verbose: If True, print debug info about retrieved context and prompt
            book_filter: If provided, limit search to chunks from this specific book_id
            
        Returns:
            AI response based on your books
        """
        if context_chunks is None:
            context_chunks = self.config.get('rag.context_chunk_count', 5)
        # Try multiple search strategies to get better context
        if book_filter:
            # Search only within the specified book
            try:
                book_results = self.collection.query(
                    query_texts=[question],
                    n_results=context_chunks,
                    where={"book_id": book_filter}
                )
                search_results = {
                    'query': question,
                    'results': []
                }
                
                if book_results['documents'] and book_results['documents'][0]:
                    for doc, meta, dist in zip(
                        book_results['documents'][0],
                        book_results['metadatas'][0], 
                        book_results['distances'][0]
                    ):
                        citation_info = self._create_citation(meta)
                        result_item = {
                            'content': doc,
                            'metadata': meta,
                            'distance': dist,
                            'similarity_score': 1 - dist,
                            'citation': citation_info
                        }
                        search_results['results'].append(result_item)
            except Exception as e:
                logger.error(f"Error searching focused book {book_filter}: {e}")
                # Fallback to regular search
                search_results = self.search_books(question, context_chunks)
        else:
            # Regular search across all books
            search_results = self.search_books(question, context_chunks)
        
        # If we don't have many results, try to expand the search with related terms
        if len(search_results.get('results', [])) < context_chunks:
            # Generate AI-powered related terms
            related_terms = self._generate_related_search_terms(question, ollama_processor)
            for term in related_terms:
                additional_results = self.search_books(term, max(1, context_chunks - len(search_results['results'])))
                if additional_results['results']:
                    # Merge results, avoiding duplicates using composite key (book_id, chunk_id)
                    existing_ids = {
                        (r.get('metadata', {}).get('book_id', ''), r.get('metadata', {}).get('chunk_id', '')) 
                        for r in search_results['results']
                    }
                    for result in additional_results['results']:
                        composite_key = (
                            result.get('metadata', {}).get('book_id', ''), 
                            result.get('metadata', {}).get('chunk_id', '')
                        )
                        if composite_key not in existing_ids:
                            search_results['results'].append(result)
                            existing_ids.add(composite_key)
                            if len(search_results['results']) >= context_chunks:
                                break
                if len(search_results['results']) >= context_chunks:
                    break
        
        if not search_results['results']:
            if verbose:
                print(f"\\n🔍 DEBUG: No relevant chunks found for query: '{question}'")
            return "I couldn't find relevant information in your book collection to answer that question."
        
        # Build context from search results
        context_parts = []
        book_metadata_summary = {}  # Collect unique book metadata
        
        for result in search_results['results']:
            book_title = result['metadata'].get('book_title', '').strip()
            author = result['metadata'].get('author', '').strip()
            content = result['content']
            book_id = result['metadata'].get('book_id', '')
            
            # Collect book metadata for summary
            if book_id and book_id not in book_metadata_summary:
                book_metadata_summary[book_id] = {
                    'title': book_title,
                    'author': author,
                    'format': result['metadata'].get('format', 'Unknown'),
                    'total_pages': result['metadata'].get('total_pages', 'Unknown'),
                    'file_hash': result['metadata'].get('file_hash', '')[:8] if result['metadata'].get('file_hash') else '',
                }
            
            # Create a better source attribution with page info
            if book_title and author:
                source = f"From '{book_title}' by {author}"
            elif book_title:
                source = f"From '{book_title}'"
            elif author:
                source = f"From a book by {author}"
            else:
                # Try to extract title/author from content or use file info
                format_info = result['metadata'].get('format', '')
                if format_info:
                    source = f"From your {format_info} book"
                else:
                    source = "From your book collection"
            
            # Add page information if available
            page_start = result['metadata'].get('page_start')
            page_end = result['metadata'].get('page_end')
            page_type = result['metadata'].get('page_type', 'estimated')
            
            if page_start and page_end:
                if page_start == page_end:
                    page_indicator = "est. p." if page_type == 'estimated' else "p."
                    source += f" ({page_indicator} {page_start})"
                else:
                    page_indicator = "est. pp." if page_type == 'estimated' else "pp."
                    source += f" ({page_indicator} {page_start}-{page_end})"
            
            context_parts.append(f"{source}:\\n{content}")
        
        if verbose:
            print(f"\\n🔍 DEBUG: Retrieved {len(search_results['results'])} context chunks:")
            for i, result in enumerate(search_results['results'], 1):
                print(f"\\n--- Chunk {i} (similarity: {result.get('similarity_score', 0):.3f}) ---")
                print(f"Source: {result['citation']}")
                print(f"Book ID: {result['metadata'].get('book_id', 'Unknown')}")
                print(f"Format: {result['metadata'].get('format', 'Unknown')}")
                print(f"Pages: {result['metadata'].get('page_start', '?')}-{result['metadata'].get('page_end', '?')} ({result['metadata'].get('page_type', 'estimated')})")
                print(f"Content: {result['content'][:200]}{'...' if len(result['content']) > 200 else ''}")
            
            if book_metadata_summary:
                print(f"\\n📚 DEBUG: Book metadata summary:")
                for book_id, meta in book_metadata_summary.items():
                    pages_info = f", {meta['total_pages']} pages" if meta['total_pages'] != 'Unknown' else ""
                    print(f"  - '{meta['title']}' by {meta['author']} ({meta['format']}{pages_info})")
        
        context = "\\n\\n---\\n\\n".join(context_parts)
        
        # Build book metadata summary for additional context
        metadata_context = ""
        if book_metadata_summary:
            metadata_context = "\\n\\nBOOK METADATA SUMMARY:\\n"
            for book_id, meta in book_metadata_summary.items():
                pages_info = f", {meta['total_pages']} pages" if meta['total_pages'] != 'Unknown' else ""
                metadata_context += f"- '{meta['title']}' by {meta['author']} ({meta['format']} format{pages_info})\\n"
        
        # Create prompt with context and metadata
        prompt = f"""Based on the following information from the user's book collection, please answer their question:

CONTEXT FROM BOOKS:
{context}

{metadata_context}
USER QUESTION: {question}

Please provide a helpful answer based on the information above. When relevant, reference specific books, authors, or page numbers. If the context doesn't fully answer the question, mention what information might be missing."""
        
        if verbose:
            print(f"\\n🤖 DEBUG: Full prompt being sent to AI model:")
            print(f"{'='*60}")
            print(prompt)
            print(f"{'='*60}\\n")
        
        try:
            # Suppress httpx INFO logging for cleaner output
            import logging as log_module
            httpx_logger = log_module.getLogger("httpx")
            original_level = httpx_logger.level
            httpx_logger.setLevel(log_module.WARNING)
            
            try:
                with Timer("AI Response Generation", verbose=verbose):
                    # Call ollama directly since we don't need the text formatting
                    response = ollama_processor.client.chat(
                        model=ollama_processor.model_name,
                        messages=[
                            {'role': 'system', 'content': 'You are a knowledgeable assistant helping someone understand their book collection.'},
                            {'role': 'user', 'content': prompt}
                        ],
                        options={'temperature': ollama_processor.temperature}
                    )
                return response['message']['content']
            finally:
                # Restore original logging level
                httpx_logger.setLevel(original_level)
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return f"Error generating response: {e}"
    
    def _generate_related_search_terms(self, question: str, ollama_processor) -> List[str]:
        """
        Use AI to generate contextually relevant search terms to improve retrieval
        
        Args:
            question: The original user question
            ollama_processor: OllamaProcessor instance for generating terms
            
        Returns:
            List of related search terms
        """
        try:
            prompt = f"""Given this question about books: "{question}"

Generate 3-5 related search terms or phrases that would help find relevant content in a book collection. 
Focus on:
- Synonyms and alternative phrasings
- Related concepts and themes  
- Key terms that might appear in book content
- Broader or more specific versions of the question

Return only the search terms, one per line, without explanations or numbering.

Examples:
For "What are the main themes?" you might suggest:
central ideas
key messages  
underlying concepts
moral lessons

For "Who are the protagonists?" you might suggest:
main characters
heroes
central figures
lead character"""

            response = ollama_processor.client.chat(
                model=ollama_processor.model_name,
                messages=[
                    {'role': 'system', 'content': 'You are a helpful assistant that generates search terms for book content retrieval.'},
                    {'role': 'user', 'content': prompt}
                ],
                options={'temperature': 0.3}  # Lower temperature for more focused results
            )
            
            # Extract terms from response
            terms_text = response['message']['content'].strip()
            terms = [term.strip() for term in terms_text.split('\n') if term.strip()]
            
            # Clean up terms and limit to 5
            clean_terms = []
            for term in terms[:5]:
                # Remove numbering, bullets, or other artifacts
                clean_term = term.replace('•', '').replace('-', '').strip()
                if clean_term and len(clean_term) > 2:
                    clean_terms.append(clean_term)
            
            logger.info(f"Generated {len(clean_terms)} related search terms for: {question}")
            return clean_terms
            
        except Exception as e:
            logger.error(f"Error generating related search terms: {e}")
            # Fallback to simple keyword extraction from the question
            return self._fallback_term_extraction(question)
    
    def _fallback_term_extraction(self, question: str) -> List[str]:
        """
        Fallback method for generating search terms when AI generation fails
        
        Args:
            question: The original question
            
        Returns:
            List of basic search terms extracted from the question
        """
        # Simple fallback: extract meaningful words from the question
        import re
        
        # Remove common question words and extract meaningful terms
        stop_words = {'what', 'who', 'when', 'where', 'why', 'how', 'is', 'are', 'the', 'a', 'an', 'and', 'or', 'but'}
        words = re.findall(r'\b\w+\b', question.lower())
        meaningful_words = [word for word in words if word not in stop_words and len(word) > 2]
        
        # Take up to 3 meaningful words
        return meaningful_words[:3]
    
    def get_collection_stats(self) -> Dict:
        """Get statistics about the RAG database"""
        try:
            # Use a more efficient count if available
            count = self.collection.count()
            return {
                'total_chunks': count,
                'database_path': self.db_path
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {'total_chunks': 0, 'database_path': self.db_path}
    
    def _chunk_content(self, content: str, chunk_size: int = 1000) -> List[str]:
        """Split content into chunks for vector storage"""
        words = content.split()
        chunks = []
        current_chunk = []
        current_length = 0
        
        for word in words:
            if current_length + len(word) > chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = [word]
                current_length = len(word)
            else:
                current_chunk.append(word)
                current_length += len(word) + 1  # +1 for space
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks


# Example usage integration with main app
class EnhancedEbookProcessor:
    """Enhanced processor with RAG capabilities"""
    
    def __init__(self, model_name: str = "llama2"):
        # Import here to avoid circular imports
        from ai_ebook_processor.core.processor import EbookProcessorApp
        from ai_ebook_processor.models.ollama import OllamaProcessor
        
        self.app = EbookProcessorApp(model_name=model_name)
        self.ollama_processor = OllamaProcessor(model_name=model_name)
        
        if RAG_AVAILABLE:
            self.rag_system = EbookRAGSystem()
        else:
            self.rag_system = None
            logger.warning("RAG system not available")
    
    def process_and_store(self, ebook_path: str, overwrite: bool = False, with_pages: bool = False) -> Dict:
        """Process an ebook and add it to the RAG system with duplicate prevention
        
        Args:
            ebook_path: Path to the ebook file
            overwrite: Whether to overwrite existing books
            with_pages: Whether to use page-aware processing for citations
            
        Returns:
            Processing result dictionary
        """
        # Early duplicate check to avoid unnecessary processing
        if self.rag_system:
            try:
                # Quick metadata read to generate book ID
                from ai_ebook_processor.readers.ebook_reader import EbookReader
                reader = EbookReader()
                
                # Get basic metadata without full processing
                try:
                    if with_pages:
                        _, metadata, _ = reader.read_ebook_with_pages(ebook_path)
                    else:
                        _, metadata = reader.read_ebook(ebook_path)
                except Exception:
                    # If metadata reading fails, proceed with processing
                    pass
                else:
                    # Generate book ID for duplicate check
                    file_hash = self.rag_system.get_file_hash(ebook_path)
                    base_book_id = f"{metadata.get('title', 'unknown')}_{metadata.get('author', 'unknown')}"
                    base_book_id = base_book_id.replace(' ', '_').replace('/', '_').replace('\\', '_')
                    book_id = f"{base_book_id}_{file_hash[:8]}"
                    
                    # Check if book already exists
                    if self.rag_system.book_exists(book_id):
                        if not overwrite:
                            logger.info(f"Book '{metadata.get('title', 'Unknown')}' already exists, skipping processing")
                            return {
                                'metadata': metadata,
                                'processing_mode': 'skipped',
                                'rag_status': f"Book {book_id} already exists, skipped",
                                'duplicate': True
                            }
                        else:
                            logger.info(f"Book '{metadata.get('title', 'Unknown')}' exists, will overwrite after processing")
            except Exception as e:
                logger.warning(f"Could not perform early duplicate check: {e}, proceeding with processing")
        
        if with_pages and self.rag_system:
            try:
                add_result = self.rag_system.add_ebook_with_pages(ebook_path, overwrite=overwrite)
                # Minimal structured wrapper
                return {
                    'mode': 'page_aware',
                    'rag_add_result': add_result,
                    'success': add_result.get('success'),
                    'skipped': add_result.get('skipped'),
                    'message': add_result.get('message'),
                    'error': add_result.get('error'),
                    'metadata': add_result.get('metadata', {})
                }
            except Exception as e:
                logger.error(f"Error in page-aware processing: {e}")
                return {'mode': 'page_aware', 'error': f"Page-aware processing failed: {e}"}
        else:
            processing_result = self.app.process_single_ebook(ebook_path)
            if self.rag_system and 'error' not in processing_result:
                add_result = self.rag_system.add_processed_ebook(processing_result, file_path=ebook_path, overwrite=overwrite)
                processing_result['rag_add_result'] = add_result
            return processing_result
    
    def ask_about_collection(self, question: str) -> str:
        """Ask a question about your entire book collection"""
        if not self.rag_system:
            return "RAG system not available. Install dependencies: pip install chromadb sentence-transformers"
        
        return self.rag_system.ask_question(question, self.ollama_processor)
    
    def list_books(self) -> List[Dict]:
        """List all books in the RAG database"""
        if not self.rag_system:
            return []
        return self.rag_system.list_books()
    
    def remove_book(self, book_id: str) -> bool:
        """Remove a book from the RAG database"""
        if not self.rag_system:
            return False
        return self.rag_system.remove_book(book_id)
    
    def book_exists(self, book_id: str) -> bool:
        """Check if a book exists in the RAG database"""
        if not self.rag_system:
            return False
        return self.rag_system.book_exists(book_id)


# Example usage
if __name__ == "__main__":
    print("Enhanced Ebook Processor with RAG and Duplicate Prevention")
    print("This creates a searchable knowledge base of your books!")
    print("\nTo use:")
    print("1. pip install chromadb sentence-transformers")
    print("2. processor = EnhancedEbookProcessor()")
    print("3. processor.process_and_store('book.epub')  # Automatically prevents duplicates")
    print("4. processor.process_and_store('book.epub', overwrite=True)  # Force overwrite")
    print("5. books = processor.list_books()  # See all books in database")
    print("6. answer = processor.ask_about_collection('What themes appear in my books?')")
    print("\nDuplicate Prevention Features:")
    print("- File hash-based deduplication prevents identical files")
    print("- Smart book ID generation (title_author_hash)")
    print("- List existing books with metadata")
    print("- Remove books cleanly from database")
    print("- Graceful handling of duplicate attempts")