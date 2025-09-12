#!/usr/bin/env python3
"""
Simple RAG System Test

Tests the RAG system without requiring Ollama to be running.
"""

import sys
from pathlib import Path
import json

# Add the current directory to the Python path
sys.path.append(str(Path(__file__).parent))

try:
    from rag_system import EbookRAGSystem
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    print("RAG dependencies not available")


def test_rag_system():
    """Test the RAG system components"""
    
    print("🧪 Testing RAG System Components")
    print("=" * 40)
    
    if not RAG_AVAILABLE:
        print("❌ RAG system not available!")
        print("Install: pip install chromadb sentence-transformers numpy")
        return
    
    print("✅ RAG dependencies available")
    
    # Test 1: Initialize RAG system
    try:
        rag = EbookRAGSystem("test_rag_db")
        print("✅ RAG system initialized")
        
        # Test 2: Get stats
        stats = rag.get_collection_stats()
        print(f"✅ Database stats: {stats}")
        
        # Test 3: Create sample book data
        sample_book = {
            'metadata': {
                'title': 'Sample Philosophy Book',
                'author': 'Test Author',
                'format': 'EPUB'
            },
            'combined_result': '''
            This book explores the fundamental questions of existence and consciousness.
            The main themes include the nature of reality, the meaning of life, and 
            the relationship between mind and matter. Key insights include the importance
            of critical thinking and the value of questioning assumptions.
            
            Chapter 1 discusses consciousness and self-awareness. The author argues that
            consciousness is the foundation of all human experience and knowledge.
            
            Chapter 2 examines ethics and morality, proposing that moral principles
            should be based on reason rather than tradition or emotion.
            ''',
            'chunk_info': {
                'successful_chunks': 3,
                'total_chunks': 3
            }
        }
        
        # Test 4: Add sample book to database
        print("✅ Adding sample book to database...")
        rag.add_processed_ebook(sample_book)
        
        # Test 5: Search functionality
        print("✅ Testing search functionality...")
        search_results = rag.search_books("consciousness and reality", n_results=2)
        
        print(f"Search results for 'consciousness and reality':")
        for i, result in enumerate(search_results['results'], 1):
            print(f"  {i}. From '{result['metadata']['book_title']}':")
            print(f"     {result['content'][:100]}...")
        
        # Test 6: Updated stats
        updated_stats = rag.get_collection_stats()
        print(f"✅ Updated database stats: {updated_stats}")
        
        print("\n🎉 RAG system test completed successfully!")
        print("\nNext steps:")
        print("1. Make sure Ollama is running: ollama serve")
        print("2. Process your actual books:")
        print("   python cli.py rag add-book 'path/to/book.epub'")
        print("3. Ask questions about your collection:")
        print("   python cli.py rag ask 'What themes appear in my books?'")
        
    except Exception as e:
        print(f"❌ Error testing RAG system: {e}")
        import traceback
        traceback.print_exc()


def show_available_models():
    """Show what Ollama models are available"""
    print("\n📚 Available Ollama Models")
    print("=" * 40)
    
    try:
        import subprocess
        result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
        if result.returncode == 0:
            print(result.stdout)
            print("✅ Ollama is working! You can use any of these models.")
            print("\nRecommended models for ebook processing:")
            if 'llama3.2' in result.stdout:
                print("  - llama3.2 (good balance of speed and quality)")
            if 'mixtral' in result.stdout:
                print("  - mixtral (high quality, slower)")
            
        else:
            print("❌ Ollama not responding. Make sure it's running:")
            print("   ollama serve")
            
    except FileNotFoundError:
        print("❌ Ollama not installed or not in PATH")


if __name__ == "__main__":
    test_rag_system()
    show_available_models()