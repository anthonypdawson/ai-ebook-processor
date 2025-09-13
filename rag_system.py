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
    
    def add_processed_ebook(self, result: Dict) -> None:
        """
        Add a processed ebook result to the RAG database
        
        Args:
            result: Processing result from EbookProcessorApp
        """
        try:
            # Extract metadata
            metadata = result['metadata']
            book_id = f"{metadata.get('title', 'unknown')}_{metadata.get('author', 'unknown')}"
            book_id = book_id.replace(' ', '_').replace('/', '_')
            
            # Get the processed content
            content = result.get('combined_result', '')
            if not content:
                logger.warning(f"No content to add for {book_id}")
                return
            
            # Create chunks for vector storage
            chunks = self._chunk_content(content, chunk_size=1000)
            
            # Add to database
            for i, chunk in enumerate(chunks):
                doc_id = f"{book_id}_chunk_{i}"
                
                self.collection.add(
                    documents=[chunk],
                    metadatas=[{
                        'book_title': metadata.get('title', 'Unknown'),
                        'author': metadata.get('author', 'Unknown'),
                        'format': metadata.get('format', 'Unknown'),
                        'chunk_id': i,
                        'book_id': book_id
                    }],
                    ids=[doc_id]
                )
            
            logger.info(f"Added {len(chunks)} chunks for '{metadata.get('title')}' to RAG database")
            
        except Exception as e:
            logger.error(f"Error adding ebook to RAG database: {e}")
    
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
            Dictionary with search results
        """
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            return {
                'query': query,
                'results': [
                    {
                        'content': doc,
                        'metadata': meta,
                        'distance': dist
                    }
                    for doc, meta, dist in zip(
                        results['documents'][0],
                        results['metadatas'][0], 
                        results['distances'][0]
                    )
                ]
            }
            
        except Exception as e:
            logger.error(f"Error searching books: {e}")
            return {'query': query, 'results': []}
    
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
                    # Merge results, avoiding duplicates
                    existing_ids = {r.get('metadata', {}).get('chunk_id', '') for r in search_results['results']}
                    for result in additional_results['results']:
                        if result.get('metadata', {}).get('chunk_id', '') not in existing_ids:
                            search_results['results'].append(result)
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
    
    def process_and_store(self, ebook_path: str) -> Dict:
        """Process an ebook and add it to the RAG system"""
        # Process the ebook
        result = self.app.process_single_ebook(ebook_path)
        
        # Add to RAG database if available
        if self.rag_system and 'error' not in result:
            self.rag_system.add_processed_ebook(result)
        
        return result
    
    def ask_about_collection(self, question: str) -> str:
        """Ask a question about your entire book collection"""
        if not self.rag_system:
            return "RAG system not available. Install dependencies: pip install chromadb sentence-transformers"
        
        return self.rag_system.ask_question(question, self.ollama_processor)


# Example usage
if __name__ == "__main__":
    print("Enhanced Ebook Processor with RAG")
    print("This creates a searchable knowledge base of your books!")
    print("\nTo use:")
    print("1. pip install chromadb sentence-transformers")
    print("2. processor = EnhancedEbookProcessor()")
    print("3. processor.process_and_store('book.epub')")
    print("4. answer = processor.ask_about_collection('What themes appear in my books?')")