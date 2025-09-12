#!/usr/bin/env python3
"""
Example script showing how to use the Ebook Processor with Ollama

This script demonstrates basic usage of the ebook processing application.
Customize it according to your needs.
"""

import sys
from pathlib import Path

# Add the current directory to the Python path
sys.path.append(str(Path(__file__).parent))

from main import EbookProcessorApp


def main():
    """Example usage of the Ebook Processor"""
    
    print("Ebook Processor with Ollama - Example")
    print("=" * 40)
    
    # Initialize the application
    # Change the model name to match what you have installed
    app = EbookProcessorApp(
        model_name="llama2",  # Change this to your preferred model
        ollama_host="http://localhost:11434"
    )
    
    # List available models
    print("\nAvailable models:")
    models = app.list_available_models()
    for model in models:
        print(f"  - {model}")
    
    # Example 1: Process a single ebook
    print("\n" + "=" * 40)
    print("Example 1: Process a single ebook")
    print("=" * 40)
    
    # Replace this with the path to one of your ebooks
    # ebook_path = "path/to/your/book.epub"
    # Uncomment and modify the following lines:
    
    # try:
    #     result = app.process_single_ebook(
    #         ebook_path,
    #         processing_type='summary',  # Options: summary, analysis, extraction, questions, critique, simplify
    #         output_dir='output'
    #     )
    #     
    #     if 'error' not in result:
    #         print(f"✓ Successfully processed: {result['metadata']['title']}")
    #         print(f"  Author: {result['metadata']['author']}")
    #         print(f"  Chunks processed: {result['chunk_info']['successful_chunks']}")
    #         print(f"  Results saved to: output/")
    #     else:
    #         print(f"✗ Error: {result['error']}")
    # 
    # except FileNotFoundError:
    #     print("Please update ebook_path with the path to one of your ebooks")
    
    # Example 2: Process all ebooks in a directory
    print("\n" + "=" * 40)
    print("Example 2: Process directory of ebooks")
    print("=" * 40)
    
    # Replace this with the path to your ebooks directory
    # ebooks_directory = "path/to/your/ebooks"
    # Uncomment and modify the following lines:
    
    # try:
    #     # First, let's see what books are available
    #     ebooks = app.find_ebooks(ebooks_directory, recursive=True)
    #     print(f"Found {len(ebooks)} ebooks:")
    #     
    #     for i, book_path in enumerate(ebooks[:5], 1):  # Show first 5 books
    #         book_info = app.get_ebook_info(book_path)
    #         print(f"  {i}. {book_info.get('title', Path(book_path).stem)}")
    #     
    #     if len(ebooks) > 5:
    #         print(f"  ... and {len(ebooks) - 5} more")
    #     
    #     # Process the first few books as an example
    #     if ebooks:
    #         print(f"\nProcessing first 2 books as example...")
    #         results = app.process_multiple_ebooks(
    #             ebooks[:2],  # Process first 2 books
    #             processing_type='summary',
    #             output_dir='batch_output'
    #         )
    #         
    #         successful = len([r for r in results if 'error' not in r])
    #         print(f"✓ Processed {successful}/{len(results)} books successfully")
    #         print(f"Results saved to: batch_output/")
    # 
    # except FileNotFoundError:
    #     print("Please update ebooks_directory with the path to your ebooks folder")
    
    # Example 3: Custom processing with different configurations
    print("\n" + "=" * 40)
    print("Example 3: Custom configuration")
    print("=" * 40)
    
    # Configure processing parameters
    app.configure_processing(
        chunk_size=3000,        # Smaller chunks for faster processing
        chunk_overlap=150,      # Overlap between chunks
        output_format='markdown',  # Options: json, txt, markdown
        save_chunks=False       # Don't save individual chunk results
    )
    
    print("Processing configuration updated:")
    print(f"  - Chunk size: 3000 characters")
    print(f"  - Chunk overlap: 150 characters")
    print(f"  - Output format: markdown")
    
    # Example 4: Different processing types
    print("\n" + "=" * 40)
    print("Example 4: Different processing types")
    print("=" * 40)
    
    processing_types = [
        ('summary', 'Creates concise summaries'),
        ('analysis', 'Analyzes themes and concepts'),
        ('extraction', 'Extracts key facts and insights'),
        ('questions', 'Generates study questions and answers'),
        ('critique', 'Provides critical analysis'),
        ('simplify', 'Explains in simpler terms')
    ]
    
    print("Available processing types:")
    for proc_type, description in processing_types:
        print(f"  - {proc_type}: {description}")
    
    print("\n" + "=" * 50)
    print("TO GET STARTED:")
    print("1. Make sure Ollama is running: `ollama serve`")
    print("2. Make sure you have a model installed: `ollama pull llama2`")
    print("3. Update the file paths in this script")
    print("4. Run this script: `python example.py`")
    print("\nAlternatively, use the CLI:")
    print("`python cli.py --help`")
    print("`python cli.py process-file /path/to/book.epub`")
    print("`python cli.py process-directory /path/to/ebooks`")
    print("=" * 50)


if __name__ == "__main__":
    main()