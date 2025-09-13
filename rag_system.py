"""
RAG (Retrieval Augmented Generation) Extension for Ebook Processor

This module creates a vector database of your processed ebooks, allowing the AI
to retrieve relevant information and answer questions about your entire collection.
"""

import os
from typing import List, Dict, Optional
import json
import logging
from pathlib import Path
import hashlib

# You would need to install these:
# pip install chromadb sentence-transformers

try:
    import chromadb
    from sentence_transformers import SentenceTransformer
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    logging.warning("RAG dependencies not installed. Run: pip install chromadb sentence-transformers")

logger = logging.getLogger(__name__)


class EbookRAGSystem:
    """
    Retrieval Augmented Generation system for ebooks
    
    This creates a searchable knowledge base from your processed ebooks,
    allowing you to ask questions about your entire collection.
    """
    
    def __init__(self, db_path: str = "ebook_db"):
        if not RAG_AVAILABLE:
            raise ImportError("Please install: pip install chromadb sentence-transformers")
        
        self.db_path = db_path
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection("ebooks")
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
        
        logger.info(f"RAG system initialized with database at: {db_path}")
    
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
    
    def book_exists(self, book_id: str) -> bool:
        """
        Check if book already exists in the database
        
        Args:
            book_id: Unique identifier for the book
            
        Returns:
            True if book exists, False otherwise
        """
        try:
            results = self.collection.get(
                where={"book_id": book_id},
                limit=1
            )
            return len(results['ids']) > 0
        except Exception as e:
            logger.error(f"Error checking if book exists: {e}")
            return False
    
    def list_books(self) -> List[Dict]:
        """
        List all books in the database
        
        Returns:
            List of dictionaries with book information
        """
        try:
            # Get all documents to analyze unique books
            results = self.collection.get()
            books = {}
            
            for metadata in results['metadatas']:
                book_id = metadata.get('book_id')
                if book_id and book_id not in books:
                    books[book_id] = {
                        'book_id': book_id,
                        'title': metadata.get('book_title', 'Unknown'),
                        'author': metadata.get('author', 'Unknown'),
                        'format': metadata.get('format', 'Unknown'),
                        'file_hash': metadata.get('file_hash', ''),
                        'chunks': 0
                    }
                if book_id:
                    books[book_id]['chunks'] += 1
            
            return list(books.values())
        except Exception as e:
            logger.error(f"Error listing books: {e}")
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
            # Get all chunks for this book
            results = self.collection.get(where={"book_id": book_id})
            
            if results['ids']:
                self.collection.delete(ids=results['ids'])
                logger.info(f"Removed {len(results['ids'])} chunks for book {book_id}")
                return True
            else:
                logger.warning(f"No chunks found for book {book_id}")
                return False
        except Exception as e:
            logger.error(f"Error removing book {book_id}: {e}")
            return False
    
    def add_ebook_with_pages(self, file_path: str, overwrite: bool = False) -> str:
        """
        Add an ebook to the RAG database with page-aware content extraction
        
        Args:
            file_path: Path to the ebook file
            overwrite: Whether to overwrite existing book
            
        Returns:
            Status message
        """
        try:
            from ebook_reader import EbookReader
            from text_pipeline import TextChunker, ProcessingConfig
            
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
                    logger.warning(f"Book {book_id} already exists. Use overwrite=True to replace.")
                    return f"Book {book_id} already exists, skipped"
                else:
                    self.remove_book(book_id)
                    logger.info(f"Overwriting existing book {book_id}")
            
            # Create chunks with page awareness
            config = ProcessingConfig(chunk_size=1000, chunk_overlap=200)
            chunker = TextChunker(config)
            chunk_infos = chunker.chunk_text_with_pages(text_content, page_info)
            
            if not chunk_infos:
                logger.warning(f"No chunks created for {book_id}")
                return f"No chunks created for {book_id}"
            
            # Add chunks to database with page information
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
                
                self.collection.add(
                    documents=[chunk_info.text],
                    metadatas=[chunk_metadata],
                    ids=[doc_id]
                )
            
            success_msg = f"Added {len(chunk_infos)} chunks with page citations for '{metadata.get('title')}' to RAG database"
            logger.info(success_msg)
            return success_msg
            
        except Exception as e:
            error_msg = f"Error adding ebook with pages to RAG database: {e}"
            logger.error(error_msg)
            return error_msg

    def add_processed_ebook(self, result: Dict, file_path: str = None, overwrite: bool = False) -> str:
        """
        Add a processed ebook result to the RAG database with duplicate detection
        
        Args:
            result: Processing result from EbookProcessorApp
            file_path: Path to original file (for hash-based deduplication)
            overwrite: Whether to overwrite existing book
            
        Returns:
            Status message indicating what happened
        """
        try:
            # Extract metadata
            metadata = result['metadata']
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
                    logger.warning(f"Book {book_id} already exists. Use overwrite=True to replace.")
                    return f"Book {book_id} already exists, skipped"
                else:
                    # Remove existing book
                    self.remove_book(book_id)
                    logger.info(f"Overwriting existing book {book_id}")
            
            # Get the processed content
            content = result.get('combined_result', '')
            if not content:
                logger.warning(f"No content to add for {book_id}")
                return f"No content found for {book_id}"
            
            # Create chunks for vector storage
            chunks = self._chunk_content(content, chunk_size=1000)
            
            if not chunks:
                logger.warning(f"No chunks created for {book_id}")
                return f"No chunks created for {book_id}"
            
            # Add to database
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
                
                self.collection.add(
                    documents=[chunk],
                    metadatas=[chunk_metadata],
                    ids=[doc_id]
                )
            
            success_msg = f"Added {len(chunks)} chunks for '{metadata.get('title')}' to RAG database"
            logger.info(success_msg)
            return success_msg
            
        except Exception as e:
            error_msg = f"Error adding ebook to RAG database: {e}"
            logger.error(error_msg)
            return error_msg
    
    def add_multiple_ebooks(self, results: List[Dict]) -> None:
        """Add multiple processed ebooks to the database"""
        for result in results:
            self.add_processed_ebook(result)
    
    def search_books(self, query: str, n_results: int = 5) -> Dict:
        """
        Search for relevant content in your ebook collection
        
        Args:
            query: Search query
            n_results: Number of results to return
            
        Returns:
            Dictionary with search results including page citations
        """
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
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
    
    def ask_question(self, question: str, ollama_processor, context_chunks: int = 5) -> str:
        """
        Ask a question about your book collection using RAG
        
        Args:
            question: Question to ask
            ollama_processor: OllamaProcessor instance
            context_chunks: Number of relevant chunks to include
            
        Returns:
            AI response based on your books
        """
        # Try multiple search strategies to get better context
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
            return "I couldn't find relevant information in your book collection to answer that question."
        
        # Build context from search results
        context_parts = []
        for result in search_results['results']:
            book_title = result['metadata'].get('book_title', '').strip()
            author = result['metadata'].get('author', '').strip()
            content = result['content']
            
            # Create a better source attribution
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
            
            context_parts.append(f"{source}:\n{content}")
        
        context = "\n\n---\n\n".join(context_parts)
        
        # Create prompt with context
        prompt = f"""Based on the following information from the user's book collection, please answer their question:

CONTEXT FROM BOOKS:
{context}

USER QUESTION: {question}

Please provide a helpful answer based on the information above. If the context doesn't fully answer the question, mention what information might be missing."""
        
        try:
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
            count = self.collection.count()
            return {
                'total_chunks': count,
                'database_path': self.db_path
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}
    
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
        from main import EbookProcessorApp
        from ollama_processor import OllamaProcessor
        
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
                from ebook_reader import EbookReader
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
            # Use page-aware processing
            try:
                status = self.rag_system.add_ebook_with_pages(ebook_path, overwrite=overwrite)
                
                # Create a result structure similar to regular processing
                from ebook_reader import EbookReader
                reader = EbookReader()
                _, metadata, page_info = reader.read_ebook_with_pages(ebook_path)
                
                result = {
                    'metadata': metadata,
                    'processing_mode': 'page_aware',
                    'chunk_info': {
                        'total_pages': len(page_info),
                        'page_type': page_info[0].get('page_type', 'estimated') if page_info else 'unknown'
                    },
                    'rag_status': status
                }
                
                if "Added" in status:
                    logger.info(f"Successfully processed with pages: {metadata.get('title', 'Unknown')}")
                else:
                    result['error'] = status
                    
                return result
                
            except Exception as e:
                logger.error(f"Error in page-aware processing: {e}")
                return {'error': f"Page-aware processing failed: {e}"}
        else:
            # Use regular processing
            result = self.app.process_single_ebook(ebook_path)
            
            # Add to RAG database if available
            if self.rag_system and 'error' not in result:
                status = self.rag_system.add_processed_ebook(result, file_path=ebook_path, overwrite=overwrite)
                result['rag_status'] = status
            
            return result
    
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