"""
Fast processing mode that skips AI analysis for quicker book ingestion
"""

def add_book_fast_mode(ebook_path: str, rag_system, ebook_reader):
    """
    Add a book to RAG database without AI analysis (much faster)
    
    Args:
        ebook_path: Path to the ebook
        rag_system: RAG system instance  
        ebook_reader: Ebook reader instance
    """
    from text_pipeline import TextChunker
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        # Read the ebook
        text_content, metadata = ebook_reader.read_ebook(ebook_path)
        
        if not text_content.strip():
            logger.warning(f"No text content extracted from {ebook_path}")
            return False
        
        # Chunk the text (without AI processing)
        chunker = TextChunker()
        chunks = chunker.chunk_text(text_content)
        
        if not chunks:
            logger.warning(f"No chunks created from {ebook_path}")
            return False
        
        # Create simplified result for RAG system
        result = {
            'metadata': metadata,
            'chunks': [
                {
                    'chunk_index': i,
                    'text': chunk.text,
                    'summary': chunk.text[:200] + "..." if len(chunk.text) > 200 else chunk.text,  # Use beginning as "summary"
                    'analysis': "Fast mode: Analysis skipped for speed",
                    'chunk_info': {
                        'start': chunk.start_pos,
                        'end': chunk.end_pos,
                        'length': chunk.length
                    }
                }
                for i, chunk in enumerate(chunks)
            ]
        }
        
        # Add to RAG database
        rag_system.add_processed_ebook(result)
        logger.info(f"Fast mode: Added {len(chunks)} chunks from {metadata.get('title', 'Unknown')} to RAG database")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in fast mode processing: {e}")
        return False