#!/usr/bin/env python3
"""
Command Line Interface for Ebook Processor

Provides a comprehensive CLI for processing ebooks with Ollama models.
"""

import click
import yaml
import json
import os
from pathlib import Path
from typing import Dict, Any

from ai_ebook_processor.core.processor import EbookProcessorApp
from ai_ebook_processor.utils.config import Config
try:
    from ai_ebook_processor.rag.system import EnhancedEbookProcessor, EbookRAGSystem
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False

# Import DEFAULT_CONFIG for config_reset
try:
    from ai_ebook_processor.utils.config import DEFAULT_CONFIG
except ImportError:
    DEFAULT_CONFIG = {}



@click.group()
@click.option('--config', '-c', default='config/config.yml', help='Configuration file path')
@click.pass_context
def cli(ctx, config):
    """Ebook Processor with Ollama - Process ebooks using AI models"""
    ctx.ensure_object(dict)
    ctx.obj['config'] = Config(config)


@cli.command()
@click.pass_context
def models(ctx):
    """List available Ollama models"""
    config = ctx.obj['config']
    
    try:
        app = EbookProcessorApp(
            model_name=config.get('ollama.model'),
            ollama_host=config.get('ollama.host')
        )
        
        models = app.list_available_models()
        
        if models:
            click.echo("Available Ollama models:")
            for i, model in enumerate(models, 1):
                current = " (current)" if model == config.get('ollama.model') else ""
                click.echo(f"  {i}. {model}{current}")
        else:
            click.echo("No Ollama models found. Make sure Ollama is running.")
            
    except Exception as e:
        click.echo(f"Error listing models: {e}", err=True)


@cli.command()
@click.pass_context
def repl(ctx):
    """Start interactive REPL mode"""
    try:
        from ai_ebook_processor.cli.repl import start_repl
        start_repl()
    except ImportError as e:
        click.echo(f"Error: REPL functionality not available: {e}", err=True)
    except KeyboardInterrupt:
        click.echo("\nREPL interrupted by user")
    except Exception as e:
        click.echo(f"Error starting REPL: {e}", err=True)


@cli.command()
@click.argument('directory', type=click.Path(exists=True, file_okay=False))
@click.option('--recursive/--no-recursive', default=True, help='Search recursively')
@click.option('--extensions', '-e', multiple=True, help='File extensions to include (e.g., .epub .pdf)')
@click.pass_context
def discover(ctx, directory, recursive, extensions):
    """Discover ebooks in a directory"""
    config = ctx.obj['config']
    
    try:
        app = EbookProcessorApp()
        ebooks = app.find_ebooks(directory, recursive)
        
        # Filter by extensions if provided
        if extensions:
            extensions = [ext if ext.startswith('.') else f'.{ext}' for ext in extensions]
            ebooks = [book for book in ebooks if Path(book).suffix.lower() in extensions]
        
        click.echo(f"Found {len(ebooks)} ebook files:")
        for i, book in enumerate(ebooks, 1):
            book_info = app.get_ebook_info(book)
            title = book_info.get('title', Path(book).stem)
            author = book_info.get('author', 'Unknown')
            format_info = book_info.get('format', Path(book).suffix)
            click.echo(f"  {i:3}. {title} by {author} ({format_info})")
            
    except Exception as e:
        click.echo(f"Error discovering ebooks: {e}", err=True)


@cli.command()
@click.argument('file_path', type=click.Path(exists=True, dir_okay=False))
@click.option('--type', '-t', 'processing_type', 
              type=click.Choice(['summary', 'analysis', 'extraction', 'questions', 'critique', 'simplify']),
              default='summary', help='Type of processing')
@click.option('--prompt', '-p', help='Custom prompt template')
@click.option('--output', '-o', help='Output directory')
@click.pass_context
def process_file(ctx, file_path, processing_type, prompt, output):
    """Process a single ebook file"""
    config = ctx.obj['config']
    
    output_dir = output or config.get('output.directory')
    
    try:
        app = EbookProcessorApp(
            model_name=config.get('ollama.model'),
            ollama_host=config.get('ollama.host')
        )
        
        # Configure processing
        app.configure_processing(
            chunk_size=config.get('processing.chunk_size'),
            chunk_overlap=config.get('processing.chunk_overlap'),
            output_format=config.get('processing.output_format'),
            save_chunks=config.get('processing.save_chunks')
        )
        
        click.echo(f"Processing: {file_path}")
        click.echo(f"Processing type: {processing_type}")
        click.echo(f"Model: {config.get('ollama.model')}")
        
        with click.progressbar(length=1, label='Processing') as bar:
            result = app.process_single_ebook(
                file_path,
                processing_type,
                prompt,
                output_dir
            )
            bar.update(1)
        
        if 'error' in result:
            click.echo(f"Error: {result['error']}", err=True)
        else:
            title = result['metadata'].get('title', 'Unknown')
            chunks = result['chunk_info']['successful_chunks']
            click.echo(f"✓ Successfully processed '{title}' ({chunks} chunks)")
            click.echo(f"Results saved to: {output_dir}")
            
    except Exception as e:
        click.echo(f"Error processing file: {e}", err=True)


@cli.command()
@click.argument('directory', type=click.Path(exists=True, file_okay=False))
@click.option('--type', '-t', 'processing_type',
              type=click.Choice(['summary', 'analysis', 'extraction', 'questions', 'critique', 'simplify']),
              default='summary', help='Type of processing')
@click.option('--prompt', '-p', help='Custom prompt template')
@click.option('--output', '-o', help='Output directory')
@click.option('--recursive/--no-recursive', default=True, help='Search recursively')
@click.option('--extensions', '-e', multiple=True, help='File extensions to include')
@click.option('--max-files', type=int, help='Maximum number of files to process')
@click.pass_context
def process_directory(ctx, directory, processing_type, prompt, output, recursive, extensions, max_files):
    """Process all ebooks in a directory"""
    config = ctx.obj['config']
    
    output_dir = output or config.get('output.directory')
    
    try:
        app = EbookProcessorApp(
            model_name=config.get('ollama.model'),
            ollama_host=config.get('ollama.host')
        )
        
        # Configure processing
        app.configure_processing(
            chunk_size=config.get('processing.chunk_size'),
            chunk_overlap=config.get('processing.chunk_overlap'),
            output_format=config.get('processing.output_format'),
            save_chunks=config.get('processing.save_chunks')
        )
        
        # Find ebooks
        ebooks = app.find_ebooks(directory, recursive)
        
        # Filter by extensions if provided
        if extensions:
            extensions = [ext if ext.startswith('.') else f'.{ext}' for ext in extensions]
            ebooks = [book for book in ebooks if Path(book).suffix.lower() in extensions]
        
        # Limit number of files if specified
        if max_files and len(ebooks) > max_files:
            ebooks = ebooks[:max_files]
            click.echo(f"Limited to first {max_files} files")
        
        if not ebooks:
            click.echo("No ebooks found in the specified directory")
            return
        
        click.echo(f"Processing {len(ebooks)} ebook files")
        click.echo(f"Processing type: {processing_type}")
        click.echo(f"Model: {config.get('ollama.model')}")
        click.echo(f"Output directory: {output_dir}")
        
        results = app.process_multiple_ebooks(
            ebooks,
            processing_type,
            prompt,
            output_dir
        )
        
        # Summary
        successful = len([r for r in results if 'error' not in r])
        failed = len(results) - successful
        
        click.echo(f"\n✓ Processing completed!")
        click.echo(f"  Successful: {successful}")
        click.echo(f"  Failed: {failed}")
        click.echo(f"  Results saved to: {output_dir}")
        
        # Create report if requested
        if config.get('output.create_report'):
            report_path = Path(output_dir) / "processing_report.json"
            app.create_processing_report(results, str(report_path))
            click.echo(f"  Report saved to: {report_path}")
            
    except Exception as e:
        click.echo(f"Error processing directory: {e}", err=True)


@cli.command()
@click.pass_context
def config_show(ctx):
    """Show current configuration"""
    config = ctx.obj['config']
    click.echo("Current configuration:")
    click.echo(yaml.dump(config.config, default_flow_style=False))


@cli.command()
@click.argument('key')
@click.argument('value')
@click.pass_context
def config_set(ctx, key, value):
    """Set a configuration value"""
    config = ctx.obj['config']
    
    # Try to parse value as JSON for proper types
    try:
        parsed_value = json.loads(value)
    except json.JSONDecodeError:
        parsed_value = value
    
    config.set(key, parsed_value)
    config.save_config()
    click.echo(f"Set {key} = {parsed_value}")


@cli.command()
@click.argument('key')
@click.pass_context
def config_get(ctx, key):
    """Get a configuration value"""
    config = ctx.obj['config']
    value = config.get(key)
    click.echo(f"{key} = {value}")


@cli.command()
@click.pass_context
def config_reset(ctx):
    """Reset configuration to defaults"""
    config = ctx.obj['config']
    
    if click.confirm('Reset configuration to defaults?'):
        config.config = DEFAULT_CONFIG.copy()
        config.save_config()
        click.echo("Configuration reset to defaults")


# RAG System Commands
@cli.group()
@click.pass_context
def rag(ctx):
    """RAG (Retrieval Augmented Generation) system commands"""
    if not RAG_AVAILABLE:
        click.echo("RAG system not available. Install dependencies:", err=True)
        click.echo("pip install chromadb sentence-transformers numpy", err=True)
        ctx.exit(1)


@rag.command()
@click.argument('file_path', type=click.Path(exists=True, dir_okay=False))
@click.option('--type', '-t', 'processing_type',
              type=click.Choice(['summary', 'analysis', 'extraction', 'questions', 'critique', 'simplify']),
              default='summary', help='Type of processing')
@click.option('--db-path', default='ebook_db', help='Path to RAG database')
@click.option('--fast', is_flag=True, help='Fast mode: Skip AI analysis for quicker processing')
@click.option('--with-pages', is_flag=True, help='Enable page-aware processing for citations')
@click.pass_context
def add_book(ctx, file_path, processing_type, db_path, fast, with_pages):
    """Process and add a book to the RAG database"""
    config = ctx.obj['config']
    
    try:
        if fast:
            # Use fast mode
            from rag_system import EbookRAGSystem
            from ebook_reader import EbookReader
            from fast_mode import add_book_fast_mode
            
            click.echo(f"Fast mode: Processing and adding {file_path}")
            
            rag_system = EbookRAGSystem(db_path=db_path)
            ebook_reader = EbookReader()
            
            with click.progressbar(length=1, label='Processing (fast)') as bar:
                success = add_book_fast_mode(file_path, rag_system, ebook_reader)
                bar.update(1)
            
            if success:
                click.echo(f"✓ Added book to RAG database (fast mode)")
            else:
                click.echo(f"Error in fast mode processing", err=True)
        else:
            # Use normal or page-aware processing
            processor = EnhancedEbookProcessor(model_name=config.get('ollama.model'))
            processor.rag_system.db_path = db_path
            
            processing_mode = "with page citations" if with_pages else "standard"
            click.echo(f"Processing and adding ({processing_mode}): {file_path}")
            
            with click.progressbar(length=1, label='Processing') as bar:
                result = processor.process_and_store(file_path, with_pages=with_pages)
                bar.update(1)
            
            if 'error' in result:
                click.echo(f"Error: {result['error']}", err=True)
            elif result.get('duplicate'):
                title = result['metadata'].get('title', 'Unknown')
                click.echo(f"→ Skipped '{title}' (already exists)")
            else:
                title = result['metadata'].get('title', 'Unknown')
                if with_pages:
                    page_info = result.get('chunk_info', {})
                    page_count = page_info.get('total_pages', 'unknown')
                    page_type = page_info.get('page_type', 'estimated')
                    click.echo(f"✓ Added '{title}' with {page_count} {page_type} pages to RAG database")
                else:
                    click.echo(f"✓ Added '{title}' to RAG database")
            
    except Exception as e:
        click.echo(f"Error processing file: {e}", err=True)


@rag.command()
@click.argument('directory', type=click.Path(exists=True, file_okay=False))
@click.option('--type', '-t', 'processing_type',
              type=click.Choice(['summary', 'analysis', 'extraction', 'questions', 'critique', 'simplify']),
              default='summary', help='Type of processing')
@click.option('--db-path', default='ebook_db', help='Path to RAG database')
@click.option('--recursive/--no-recursive', default=True, help='Search recursively')
@click.option('--max-files', type=int, help='Maximum number of files to process')
@click.option('--with-pages', is_flag=True, help='Enable page-aware processing for citations')
@click.pass_context
def add_directory(ctx, directory, processing_type, db_path, recursive, max_files, with_pages):
    """Process and add all books in a directory to the RAG database"""
    config = ctx.obj['config']
    
    try:
        processor = EnhancedEbookProcessor(model_name=config.get('ollama.model'))
        processor.rag_system.db_path = db_path
        
        # Find ebooks
        ebooks = processor.app.find_ebooks(directory, recursive)
        
        if max_files and len(ebooks) > max_files:
            ebooks = ebooks[:max_files]
            click.echo(f"Limited to first {max_files} files")
        
        if not ebooks:
            click.echo("No ebooks found in directory")
            return
        
        processing_mode = "with page citations" if with_pages else "standard"
        click.echo(f"Processing and adding {len(ebooks)} books ({processing_mode}) to RAG database")
        
        successful = 0
        skipped = 0
        for i, ebook_path in enumerate(ebooks):
            click.echo(f"Processing {i+1}/{len(ebooks)}: {Path(ebook_path).name}")
            
            try:
                result = processor.process_and_store(ebook_path, with_pages=with_pages)
                if 'error' not in result:
                    if result.get('duplicate'):
                        skipped += 1
                        title = result['metadata'].get('title', 'Unknown')
                        click.echo(f"  → Skipped '{title}' (already exists)")
                    else:
                        successful += 1
                        title = result['metadata'].get('title', 'Unknown')
                        if with_pages:
                            page_info = result.get('chunk_info', {})
                            page_count = page_info.get('total_pages', 'unknown')
                            click.echo(f"  ✓ Added '{title}' with {page_count} pages")
                        else:
                            click.echo(f"  ✓ Added '{title}'")
                else:
                    click.echo(f"  ✗ Error: {result['error']}")
                    
            except Exception as e:
                click.echo(f"  ✗ Error: {e}")
        
        citation_note = " with page citations" if with_pages else ""
        if skipped > 0:
            click.echo(f"\n✓ Added {successful}/{len(ebooks)} books to RAG database{citation_note} ({skipped} skipped as duplicates)")
        else:
            click.echo(f"\n✓ Added {successful}/{len(ebooks)} books to RAG database{citation_note}")
        
    except Exception as e:
        click.echo(f"Error processing directory: {e}", err=True)


@rag.command()
@click.argument('question')
@click.option('--db-path', default='ebook_db', help='Path to RAG database')
@click.option('--context-chunks', default=5, help='Number of relevant chunks to use')
@click.pass_context
def ask(ctx, question, db_path, context_chunks):
    """Ask a question about your book collection"""
    config = ctx.obj['config']
    
    try:
        processor = EnhancedEbookProcessor(model_name=config.get('ollama.model'))
        processor.rag_system.db_path = db_path
        
        click.echo(f"Question: {question}")
        click.echo("Searching your book collection...")
        
        with click.progressbar(length=1, label='Thinking') as bar:
            answer = processor.rag_system.ask_question(
                question, 
                processor.ollama_processor, 
                context_chunks
            )
            bar.update(1)
        
        click.echo("\nAnswer:")
        click.echo("-" * 50)
        click.echo(answer)
        
    except Exception as e:
        click.echo(f"Error asking question: {e}", err=True)


@rag.command()
@click.argument('query')
@click.option('--db-path', default='ebook_db', help='Path to RAG database')
@click.option('--results', '-n', default=5, help='Number of results to show')
@click.pass_context
def search(ctx, query, db_path, results):
    """Search your book collection for relevant content"""
    try:
        rag_system = EbookRAGSystem(db_path)
        
        click.echo(f"Searching for: {query}")
        search_results = rag_system.search_books(query, results)
        
        if not search_results['results']:
            click.echo("No relevant content found.")
            return
        
        click.echo(f"\nFound {len(search_results['results'])} relevant passages:")
        click.echo("=" * 60)
        
        for i, result in enumerate(search_results['results'], 1):
            book_title = result['metadata'].get('book_title', '').strip()
            author = result['metadata'].get('author', '').strip()
            content = result['content'][:300] + "..." if len(result['content']) > 300 else result['content']
            
            # Use citation if available, otherwise fallback to old format
            if 'citation' in result and result['citation']:
                source_info = result['citation']
            else:
                # Fallback for older entries without page info
                if book_title and author:
                    source_info = f"From '{book_title}' by {author}"
                elif book_title:
                    source_info = f"From '{book_title}'"
                elif author:
                    source_info = f"From a book by {author}"
                else:
                    format_info = result['metadata'].get('format', '')
                    if format_info:
                        source_info = f"From your {format_info} book"
                    else:
                        source_info = "From your book collection"
            
            click.echo(f"\n{i}. {source_info}:")
            click.echo("-" * 40)
            click.echo(content)
        
    except Exception as e:
        click.echo(f"Error searching: {e}", err=True)


@rag.command()
@click.option('--db-path', default='ebook_db', help='Path to RAG database')
@click.pass_context
def stats(ctx, db_path):
    """Show RAG database statistics"""
    try:
        rag_system = EbookRAGSystem(db_path)
        stats = rag_system.get_collection_stats()
        
        click.echo("RAG Database Statistics:")
        click.echo(f"  Total chunks: {stats.get('total_chunks', 0)}")
        click.echo(f"  Database path: {stats.get('database_path', 'unknown')}")
        
        # Check if database directory exists
        db_path_obj = Path(db_path)
        if db_path_obj.exists():
            size_mb = sum(f.stat().st_size for f in db_path_obj.rglob('*') if f.is_file()) / (1024*1024)
            click.echo(f"  Database size: {size_mb:.2f} MB")
        
    except Exception as e:
        click.echo(f"Error getting stats: {e}", err=True)


@rag.command()
@click.option('--db-path', default='ebook_db', help='Path to RAG database')
@click.option('--filter', '-f', help='Filter books by title or author (case-insensitive)')
@click.pass_context
def list_books(ctx, db_path, filter):
    """List all books in the RAG database"""
    try:
        rag_system = EbookRAGSystem(db_path)
        books = rag_system.list_books()
        
        if not books:
            click.echo("No books found in the RAG database.")
            return
        
        # Apply filter if provided
        if filter:
            filter_lower = filter.lower()
            filtered_books = []
            for book in books:
                title = book.get('title', '').lower()
                author = book.get('author', '').lower()
                if filter_lower in title or filter_lower in author:
                    filtered_books.append(book)
            books = filtered_books
        
        if not books:
            click.echo(f"No books found matching filter: '{filter}'")
            return
        
        click.echo(f"Found {len(books)} book(s) in the RAG database:")
        click.echo("=" * 70)
        
        for i, book in enumerate(books, 1):
            title = book.get('title', 'Unknown Title')
            author = book.get('author', 'Unknown Author')
            format_type = book.get('format', 'Unknown')
            chunks = book.get('chunks', 0)
            
            click.echo(f"{i:3}. {title}")
            click.echo(f"     Author: {author}")
            click.echo(f"     Format: {format_type} | Chunks: {chunks}")
            if i < len(books):  # Don't add separator after last item
                click.echo()
        
    except Exception as e:
        click.echo(f"Error listing books: {e}", err=True)


@rag.command()
@click.argument('pattern')
@click.option('--db-path', default='ebook_db', help='Path to RAG database')
@click.option('--by', type=click.Choice(['title', 'author', 'both']), default='both', 
              help='Search by title, author, or both')
@click.pass_context
def find_book(ctx, pattern, db_path, by):
    """Find books by title or author pattern"""
    try:
        rag_system = EbookRAGSystem(db_path)
        books = rag_system.list_books()
        
        if not books:
            click.echo("No books found in the RAG database.")
            return
        
        pattern_lower = pattern.lower()
        matching_books = []
        
        for book in books:
            title = book.get('title', '').lower()
            author = book.get('author', '').lower()
            
            match = False
            if by == 'title' and pattern_lower in title:
                match = True
            elif by == 'author' and pattern_lower in author:
                match = True
            elif by == 'both' and (pattern_lower in title or pattern_lower in author):
                match = True
            
            if match:
                matching_books.append(book)
        
        if not matching_books:
            search_type = "title and author" if by == 'both' else by
            click.echo(f"No books found with '{pattern}' in {search_type}.")
            return
        
        search_type = "title and author" if by == 'both' else by
        click.echo(f"Found {len(matching_books)} book(s) matching '{pattern}' in {search_type}:")
        click.echo("=" * 70)
        
        for i, book in enumerate(matching_books, 1):
            title = book.get('title', 'Unknown Title')
            author = book.get('author', 'Unknown Author')
            format_type = book.get('format', 'Unknown')
            chunks = book.get('chunks', 0)
            book_id = book.get('book_id', '')
            
            click.echo(f"{i:3}. {title}")
            click.echo(f"     Author: {author}")
            click.echo(f"     Format: {format_type} | Chunks: {chunks}")
            click.echo(f"     Book ID: {book_id}")
            if i < len(matching_books):  # Don't add separator after last item
                click.echo()
        
    except Exception as e:
        click.echo(f"Error finding books: {e}", err=True)


if __name__ == '__main__':
    cli()