#!/usr/bin/env python3
"""
Enhanced Example Script with RAG System

This script demonstrates the new RAG (Retrieval Augmented Generation) capabilities
alongside the original ebook processing features.
"""

import sys
from pathlib import Path

# Add the current directory to the Python path
sys.path.append(str(Path(__file__).parent))

from main import EbookProcessorApp

try:
    from rag_system import EnhancedEbookProcessor, EbookRAGSystem
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False


def main():
    """Enhanced example usage with RAG capabilities"""
    
    print("Enhanced Ebook Processor with RAG System")
    print("=" * 50)
    
    if not RAG_AVAILABLE:
        print("❌ RAG system not available!")
        print("Install dependencies: pip install chromadb sentence-transformers numpy")
        print("Then restart this script.")
        return
    
    print("✅ RAG system available!")
    
    # Example 1: Original Processing (still works)
    print("\n" + "=" * 50)
    print("Example 1: Traditional Processing")
    print("=" * 50)
    
    app = EbookProcessorApp(model_name="llama2")
    
    print("Available models:")
    models = app.list_available_models()
    for model in models:
        print(f"  - {model}")
    
    # Example 2: Enhanced Processing with RAG
    print("\n" + "=" * 50)
    print("Example 2: Enhanced Processing with RAG")
    print("=" * 50)
    
    enhanced_processor = EnhancedEbookProcessor(model_name="llama2")
    
    print("This creates a searchable knowledge base of your books!")
    print("After processing, you can ask questions about your entire collection.")
    
    # Uncomment to process your books:
    # result = enhanced_processor.process_and_store("path/to/your/book.epub")
    
    # Example 3: RAG Database Operations
    print("\n" + "=" * 50)
    print("Example 3: RAG Database Operations")
    print("=" * 50)
    
    # Initialize RAG system
    rag_system = EbookRAGSystem("example_rag_db")
    
    print("RAG system initialized!")
    print("Database will be created at: example_rag_db/")
    
    stats = rag_system.get_collection_stats()
    print(f"Current database stats: {stats}")
    
    # Example 4: Querying Your Collection (after processing books)
    print("\n" + "=" * 50)
    print("Example 4: Querying Your Book Collection")
    print("=" * 50)
    
    print("Once you've processed books, you can ask questions like:")
    example_questions = [
        "What are the main themes across my science fiction books?",
        "Which books discuss artificial intelligence?",
        "What did Marcus Aurelius say about virtue?",
        "What are the key insights from my business books?",
        "Which characters appear in my fantasy novels?",
        "What historical events are covered in my history books?"
    ]
    
    for i, question in enumerate(example_questions, 1):
        print(f"  {i}. {question}")
    
    # Example of how you would ask a question (if you had books processed):
    # answer = enhanced_processor.ask_about_collection(
    #     "What are the main themes in my philosophy books?"
    # )
    # print(f"Answer: {answer}")
    
    # Example 5: CLI Usage Examples
    print("\n" + "=" * 50)
    print("Example 5: CLI Usage with RAG")
    print("=" * 50)
    
    cli_examples = [
        # Process and add to RAG database
        'python cli.py rag add-book "book.epub"',
        'python cli.py rag add-directory "/path/to/ebooks" --max-files 5',
        
        # Query your collection
        'python cli.py rag ask "What themes appear in my books?"',
        'python cli.py rag search "artificial intelligence"',
        
        # Database management
        'python cli.py rag stats',
    ]
    
    print("Enhanced CLI commands with RAG:")
    for example in cli_examples:
        print(f"  $ {example}")
    
    # Example 6: Step-by-Step RAG Workflow
    print("\n" + "=" * 50)
    print("Example 6: Complete RAG Workflow")
    print("=" * 50)
    
    workflow = [
        "1. Process and store your first book:",
        "   enhanced_processor.process_and_store('book1.epub')",
        "",
        "2. Add more books to build your knowledge base:",
        "   enhanced_processor.process_and_store('book2.pdf')",
        "   enhanced_processor.process_and_store('book3.mobi')",
        "",
        "3. Ask questions about your collection:",
        "   answer = enhanced_processor.ask_about_collection('What are the main themes?')",
        "",
        "4. Search for specific content:",
        "   results = rag_system.search_books('quantum physics', n_results=3)",
        "",
        "5. Get insights across your entire library:",
        "   answer = enhanced_processor.ask_about_collection('Compare the writing styles')"
    ]
    
    for step in workflow:
        print(step)
    
    # Example 7: Advanced Features
    print("\n" + "=" * 50)
    print("Example 7: Advanced RAG Features")
    print("=" * 50)
    
    print("🔍 Semantic Search:")
    print("   - Find books by meaning, not just keywords")
    print("   - Example: Search 'leadership' finds books about 'management' and 'authority'")
    print()
    print("🧠 Contextual Answers:")
    print("   - AI answers use content from your specific books")
    print("   - Cites which books the information comes from")
    print()
    print("📚 Cross-Book Analysis:")
    print("   - Compare themes across multiple books")
    print("   - Find connections between different authors")
    print()
    print("🎯 Personalized Knowledge:")
    print("   - Your personal AI assistant for your book collection")
    print("   - Remembers everything you've read")
    
    # Getting Started Instructions
    print("\n" + "=" * 60)
    print("🚀 GETTING STARTED WITH RAG:")
    print("=" * 60)
    
    getting_started = [
        "1. Make sure Ollama is running:",
        "   $ ollama serve",
        "",
        "2. Have a model installed:",
        "   $ ollama pull llama2",
        "",
        "3. Process your first book with RAG:",
        '   $ python cli.py rag add-book "path/to/book.epub"',
        "",
        "4. Ask your first question:",
        '   $ python cli.py rag ask "What is this book about?"',
        "",
        "5. Build your knowledge base:",
        '   $ python cli.py rag add-directory "/path/to/ebooks" --max-files 10',
        "",
        "6. Start asking questions about your entire collection!",
        '   $ python cli.py rag ask "What themes appear across my books?"'
    ]
    
    for instruction in getting_started:
        print(instruction)
    
    print("\n" + "=" * 60)
    print("💡 The RAG system transforms your ebook collection into")
    print("   a searchable, queryable knowledge base!")
    print("=" * 60)


if __name__ == "__main__":
    main()