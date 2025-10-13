"""
Interactive REPL (Read-Eval-Print Loop) for the AI Ebook Processor.

This module provides an interactive command-line interface that maintains
session state, command history, and provides a more seamless user experience
than repeated CLI calls.
"""

import os
import sys
import shlex
import readline
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any

import click

from ai_ebook_processor.core.processor import EbookProcessorApp
from ai_ebook_processor.utils.config import Config
from ai_ebook_processor.core.parallel import create_parallel_processor
from ai_ebook_processor.core.pipeline import ProcessingPipeline

logger = logging.getLogger(__name__)

# Import RAG functionality
try:
    from ai_ebook_processor.rag.document_processor import DocumentProcessor
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False


class EbookREPL:
    """Interactive REPL for ebook processing and RAG operations."""
    
    def __init__(self):
        self.current_directory = Path.cwd()
        self.processor = None
        self.parallel_processor = None
        self.config = Config()
        self.history_file = Path.home() / ".ebook_processor_history"
        self.running = True
        self.focused_book = None  # Initialize focused book tracking

        # Check if parallel processing is enabled
        self.parallel_enabled = self.config.get('features.parallel_processing', True) and \
                               self.config.get('processing.parallel.enabled', True)

        # Command registry
        self.commands: Dict[str, Callable] = {
            'help': self.cmd_help,
            '?': self.cmd_help,
            'exit': self.cmd_exit,
            'quit': self.cmd_exit,
            'cd': self.cmd_cd,
            'pwd': self.cmd_pwd,
            'ls': self.cmd_ls,
            'dir': self.cmd_ls,  # Windows alias
            'add': self.cmd_add,
            'batch': self.cmd_batch,
            'ask': self.cmd_ask,
            'list': self.cmd_list,
            'focus': self.cmd_focus,
            'unfocus': self.cmd_unfocus,
            'status': self.cmd_status,
            'search': self.cmd_search,
            'config': self.cmd_config,
            'clear': self.cmd_clear,
            'cleardb': self.cmd_cleardb,
            'remove': self.cmd_remove,
        }

        # Command aliases for convenience (RAG-focused)
        self.aliases: Dict[str, str] = {
            'q': 'ask',      # Primary: Ask questions about your books
            'a': 'add',      # Primary: Add books to knowledge base  
            'b': 'batch',    # Primary: Batch add multiple directories
            'l': 'list',     # Show your book collection
            's': 'search',   # Search within your books
            'c': 'clear',
            'll': 'list',
            'rm': 'remove'
        }

        self._setup_readline()
        self._initialize_systems()
    
    def _setup_readline(self):
        """Configure readline for command history and completion."""
        try:
            # Load command history
            if self.history_file.exists():
                readline.read_history_file(str(self.history_file))
            
            # Set history length
            readline.set_history_length(1000)
            
            # Enable tab completion
            readline.set_completer(self._complete)
            readline.parse_and_bind("tab: complete")
            
            # Configure better tab completion behavior
            readline.parse_and_bind("set show-all-if-ambiguous on")
            readline.parse_and_bind("set completion-ignore-case on")
            readline.parse_and_bind("set show-all-if-unmodified on")
            
            # Handle quotes and special characters better
            readline.set_completer_delims(' \t\n`!@#$%^&*()=+[{]}\\|;:\'",<>?')
            
            # Prevent freezing on large directories
            readline.parse_and_bind("set completion-query-items 100")
            
        except ImportError:
            # readline not available on this system
            pass
    
    def _initialize_systems(self):
        """Initialize modular RAG system and processor."""
        try:
            model_name = self.config.get('ollama.model', 'llama3.2:latest')
            db_path = self.config.get('rag.db_path', 'ebook_db')
            config_path = self.config.config_path if hasattr(self.config, 'config_path') else 'config/config.yml'
            self.processor = DocumentProcessor(db_path=db_path, config_path=config_path, model_name=model_name)
            click.echo("✓ Modular RAG system initialized")
        except Exception as e:
            click.echo(f"⚠ Warning: Could not initialize RAG system: {e}", err=True)
            click.echo("  Some features may be unavailable")
    
    def _run_async(self, coro):
        """Run an async coroutine in the REPL context."""
        try:
            # Try to get existing event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're in an already running loop, create a new task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, coro)
                    return future.result()
            else:
                return loop.run_until_complete(coro)
        except RuntimeError:
            # No event loop, create a new one
            return asyncio.run(coro)
    
    def _process_book_for_rag(self, book_path: Path) -> Dict[str, Any]:
        """Process a single book and add to RAG system."""
        try:
            # Use the enhanced RAG system which does both processing and ingestion
            result = self.rag_system.add_ebook_with_pages(str(book_path))
            
            return {
                'success': True,
                'title': result.get('title', book_path.name),
                'path': str(book_path),
                'message': result
            }
        except Exception as e:
            logger.error(f"Error processing book for RAG: {book_path}: {e}")
            return {
                'success': False,
                'title': book_path.name,
                'path': str(book_path),
                'error': str(e)
            }
    
    def _save_history(self):
        """Save command history to file."""
        try:
            readline.write_history_file(str(self.history_file))
        except (ImportError, IOError):
            pass
    
    def _complete(self, text: str, state: int) -> Optional[str]:
        """Tab completion function with proper space handling."""
        try:
            line = readline.get_line_buffer()
            
            # Handle quoted strings and spaces properly
            tokens = []
            try:
                tokens = shlex.split(line) if line.strip() else []
            except ValueError:
                # Handle unclosed quotes by trying to parse what we have
                tokens = line.split()
            
            # Get the position where completion is happening
            endidx = readline.get_endidx()
            begidx = readline.get_begidx()
            
            # If we're at the beginning or completing a command
            if not tokens or (len(tokens) == 1 and endidx <= len(tokens[0])):
                # Complete command names
                commands = list(self.commands.keys()) + list(self.aliases.keys())
                matches = [cmd for cmd in commands if cmd.startswith(text)]
            else:
                # We're completing arguments - check if it's a path-based command
                command = tokens[0] if tokens else ""
                if command in ['cd', 'add'] or command in self.aliases:
                    # Complete file paths for these commands
                    matches = self._complete_path(text)
                else:
                    # No completion for other commands
                    matches = []
            
            return matches[state] if state < len(matches) else None
        except (IndexError, TypeError, Exception):
            return None
    
    def _complete_path(self, text: str) -> List[str]:
        """Complete file paths with proper space handling and timeout protection."""
        if not text:
            text = "."
        
        try:
            # Handle Windows drive letter completion (any single letter followed by colon)
            import re
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError("Path completion timed out")
            
            if re.match(r'^[A-Za-z]:$', text):
                # Drive letter completion - check if drive exists
                drive_path = Path(text + "\\")
                if drive_path.exists():
                    return [text + "\\"]
                return []
            
            # Remove quotes from text for path resolution
            clean_text = text.strip('"\'')
            path = Path(clean_text)
            
            # Handle different path scenarios
            if path.is_absolute() or clean_text.startswith("\\\\"):
                # Absolute path or UNC path
                try:
                    if clean_text.endswith("\\") or clean_text.endswith("/"):
                        base_dir = path
                        prefix = ""
                    else:
                        base_dir = path.parent
                        prefix = path.name
                except Exception:
                    return []
                is_absolute = True
            else:
                # Relative path
                parent = path.parent if str(path.parent) != "." else Path()
                base_dir = self.current_directory / parent
                prefix = path.name
                is_absolute = False
            
            if not base_dir.exists():
                return []
            
            matches = []
            try:
                # Set a timeout to prevent freezing on slow network paths
                if os.name != 'nt':  # Only on Unix systems
                    signal.signal(signal.SIGALRM, timeout_handler)
                    signal.alarm(2)  # 2 second timeout
                
                count = 0
                for item in base_dir.iterdir():
                    # Limit the number of completions to prevent freezing
                    if count >= 50:
                        break
                        
                    if item.name.startswith(prefix):
                        count += 1
                        
                        # Determine the completion text
                        if is_absolute:
                            # For absolute paths, return the full path
                            completion = str(item)
                            if item.is_dir():
                                completion += os.sep
                        else:
                            # For relative paths, construct the proper relative path
                            if str(path.parent) != ".":
                                # Include the parent path
                                completion = str(path.parent) + os.sep + item.name
                                if item.is_dir():
                                    completion += os.sep
                            else:
                                # Just the name
                                completion = item.name
                                if item.is_dir():
                                    completion += os.sep
                        
                        # Quote the completion if it contains spaces or special characters
                        if ' ' in completion or any(c in completion for c in '&()[]{}^=;!\'"+,`~'):
                            completion = f'"{completion}"'
                        
                        matches.append(completion)
                
                if os.name != 'nt':
                    signal.alarm(0)  # Cancel the timeout
                        
            except (PermissionError, TimeoutError):
                # Can't read directory or timed out, return empty list
                if os.name != 'nt':
                    signal.alarm(0)  # Cancel the timeout
                return []
            
            return sorted(matches)
        except (OSError, ValueError, Exception):
            return []
    
    def run(self):
        """Main REPL loop."""
        self._print_welcome()
        
        try:
            while self.running:
                try:
                    # Show prompt with current directory
                    rel_path = self._get_relative_path()
                    prompt = f"[{rel_path}] ebook> "
                    
                    # Get user input
                    line = input(prompt).strip()
                    
                    if not line:
                        continue
                    
                    # Parse and execute command
                    self._execute_command(line)
                    
                except KeyboardInterrupt:
                    click.echo("\nUse 'exit' or 'quit' to leave the REPL")
                    continue
                except EOFError:
                    click.echo("\nGoodbye!")
                    break
        finally:
            self._save_history()
    
    def _print_welcome(self):
        """Print welcome message."""
        click.echo("� AI Ebook RAG System - Interactive Shell")
        click.echo("Build your intelligent book collection and ask questions about your library!")
        click.echo()
        
        if not RAG_AVAILABLE:
            click.echo("⚠️  RAG system unavailable - install: pip install chromadb sentence-transformers")
        else:
            try:
                books = []
                if self.rag_system:
                    books = self.rag_system.list_books()
                
                if books:
                    total_chunks = sum(book.get('chunks', 0) for book in books)
                    click.echo(f"✅ Knowledge base: {len(books)} books with {total_chunks:,} chunks ready to query")
                    click.echo("💡 Try: ask What are the main themes across my books?")
                    click.echo("� Type 'list' to see all books")
                else:
                    click.echo("📚 Empty knowledge base - add your first book!")
                    click.echo("💡 Try: add book.epub  or  add ~/Books/")
            except Exception as e:
                click.echo(f"Error: {e}", err=True)
                click.echo(f"⚠️  RAG system error: {e}")
                click.echo("✅ RAG system ready - add books to start!")
        
        click.echo()
        click.echo("Type 'help' for commands, 'q <question>' to ask, 'exit' to quit")
        click.echo(f"📁 Current directory: {self.current_directory}")
        click.echo()
    
    def _get_relative_path(self) -> str:
        """Get current directory relative to home if possible."""
        try:
            return str(self.current_directory.relative_to(Path.home()))
        except ValueError:
            return str(self.current_directory)
    
    def _execute_command(self, line: str):
        """Parse and execute a command."""
        try:
            # Handle trailing backslashes that cause shlex issues
            cleaned_line = line.rstrip()
            if cleaned_line.endswith('\\') and not cleaned_line.endswith('\\\\'):
                # Remove single trailing backslash that would cause escape errors
                cleaned_line = cleaned_line.rstrip('\\')
            
            tokens = shlex.split(cleaned_line)
        except ValueError as e:
            # If shlex fails, fall back to simple split
            click.echo(f"Parse error: {e}", err=True)
            # Try simple split as fallback
            tokens = line.split()
            if not tokens:
                return
        
        if not tokens:
            return
        
        command = tokens[0].lower()
        args = tokens[1:]
        
        # Clean up arguments - remove trailing path separators
        cleaned_args = []
        for arg in args:
            # Remove trailing separators from path arguments
            cleaned_arg = arg.rstrip('\\/').strip('"\'')
            if cleaned_arg:  # Only add non-empty arguments
                cleaned_args.append(cleaned_arg)
        
        # Check aliases
        if command in self.aliases:
            command = self.aliases[command]
        
        # Execute command
        if command in self.commands:
            try:
                self.commands[command](cleaned_args)
            except Exception as e:
                click.echo(f"Error: {e}", err=True)
                click.echo(f"Error executing command: {e}", err=True)
        else:
            click.echo(f"Unknown command: {command}. Type 'help' for available commands.")
    
    # Command implementations
    def cmd_help(self, args: List[str]):
        """Show help information."""
        click.echo("🤖 AI Ebook Processor REPL - Available Commands")
        click.echo("=" * 60)
        click.echo()
        
        click.echo("📖 General Commands:")
        click.echo("  help, ?           Show this help message")
        click.echo("  exit, quit        Exit the REPL")
        click.echo("  clear, c          Clear the screen")
        click.echo()
        
        click.echo("📁 File System Navigation:")
        click.echo("  cd <path>         Change directory (supports tab completion)")
        click.echo("                    Example: cd ~/Documents/Books")
        click.echo("  pwd               Show current working directory")
        click.echo("  ls, dir           List directory contents (📚 highlights ebooks)")
        click.echo()
        
        click.echo("🧠 RAG Operations (Primary Features):")
        click.echo("  add <file/dir>    Add book(s) to RAG knowledge base")
        click.echo("                    Examples: add book.epub")
        click.echo("                              add Fiction/")
        click.echo("                              add .  (current directory)")
        if self.parallel_enabled:
            click.echo("                    📦 Parallel processing enabled for directories")
        click.echo()
        click.echo("  batch <dir1> <dir2> ... Process multiple directories in parallel")
        click.echo("                    Example: batch Fiction/ NonFiction/ SciFi/")
        if self.parallel_enabled:
            click.echo("                    🚀 Uses parallel processing for optimal speed")
        click.echo()
        click.echo("  ask <question>    Ask questions about your book collection")
        click.echo("                    Examples: ask What themes appear in my books?")
        click.echo("                              ask Compare the writing styles")
        click.echo("                              ask What books mention artificial intelligence?")
        click.echo()
        click.echo("  search <query>    Search for specific content in your books")
        click.echo("                    Example: search character development techniques")
        click.echo()
        click.echo("  list              Show all books in your RAG knowledge base")
        click.echo("                    Shows processing status and book metadata")
        click.echo()
        
        click.echo("🔧 System Management:")
        click.echo("  config            Show current system configuration")
        click.echo("  cleardb           Clear entire RAG database (remove all books)")
        click.echo("  remove <number>   Remove a specific book (use 'list' to see numbers)")
        if self.parallel_enabled:
            click.echo("                    📊 Parallel processing: ENABLED")
        else:
            click.echo()
        
        click.echo("� Navigation & Aliases:")
        click.echo("  q <question>      Quick alias for 'ask'")
        click.echo("  a <file/dir>      Quick alias for 'add'") 
        click.echo("  b <dirs...>       Quick alias for 'batch'")
        click.echo("  l                 Quick alias for 'list'")
        click.echo("  s <query>         Quick alias for 'search'")
        click.echo()
        
        click.echo("💡 Pro Tips:")
        click.echo("  - Use tab completion for file paths")
        click.echo("  - Add entire directories to build your knowledge base quickly") 
        click.echo("  - Ask follow-up questions - the AI remembers the conversation context")
        click.echo("  - Use specific queries for better results: 'themes in Victorian novels'")
        if self.parallel_enabled:
            click.echo("  - Parallel processing makes large collections fast to ingest")
        
        if not RAG_AVAILABLE:
            click.echo()
            click.echo("⚠️  RAG System Status: NOT AVAILABLE")
            click.echo("    Install dependencies: pip install chromadb sentence-transformers")
        else:
            book_count = 0
            try:
                if self.rag_system:
                    book_count = len(self.rag_system.list_books())
            except:
                pass
            click.echo()
            click.echo(f"✅ RAG System Status: ACTIVE ({book_count} books in knowledge base)")
        click.echo("  c  → clear        Quick screen clear")
        click.echo()
        
        click.echo("💡 Tips:")
        click.echo("  • Use TAB for command and file path completion")
        click.echo("  • Use ↑/↓ arrows to navigate command history")
        click.echo("  • Commands support both relative and absolute paths")
        click.echo("  • Current directory shown in prompt: [path] ebook>")
        click.echo("  • 📚 and 📁 icons help identify ebooks and directories")
        click.echo()
        
        click.echo("🎯 Example Workflow:")
        click.echo("  cd ~/Documents/Books     # Navigate to your books")
        click.echo("  ls                       # See what's available")
        click.echo("  add .                    # Add all books in directory")
        click.echo("  ask What genres do I have?  # Query your collection")
        click.echo()
        
        if not RAG_AVAILABLE:
            click.echo("⚠️  Note: RAG functionality requires additional setup.")
            click.echo("   Check installation instructions for full features.")
    
    def cmd_exit(self, args: List[str]):
        """Exit the REPL."""
        click.echo("Goodbye!")
        self.running = False
    
    def cmd_clear(self, args: List[str]):
        """Clear the screen."""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def cmd_cd(self, args: List[str]):
        """Change current directory."""
        if not args:
            # Go to home directory
            self.current_directory = Path.home()
        else:
            path = Path(args[0]).expanduser()
            if not path.is_absolute():
                path = self.current_directory / path
            
            try:
                path = path.resolve()
                if path.exists() and path.is_dir():
                    self.current_directory = path
                    click.echo(f"Changed to: {path}")
                else:
                    click.echo(f"Directory not found: {path}", err=True)
            except (OSError, ValueError) as e:
                click.echo(f"Error: {e}", err=True)
    
    def cmd_pwd(self, args: List[str]):
        """Show current directory."""
        click.echo(self.current_directory)
    
    def cmd_ls(self, args: List[str]):
        """List directory contents."""
        target_dir = self.current_directory
        
        if args:
            target_path = Path(args[0])
            if not target_path.is_absolute():
                target_path = self.current_directory / target_path
            
            if target_path.exists():
                target_dir = target_path
            else:
                click.echo(f"Path not found: {target_path}", err=True)
                return
        
        try:
            items = sorted(target_dir.iterdir())
            if not items:
                click.echo("(empty directory)")
                return
            
            # Group directories and files
            dirs = [item for item in items if item.is_dir()]
            files = [item for item in items if item.is_file()]
            
            # Show directories first
            for item in dirs:
                click.echo(f"📁 {item.name}/")
            
            # Show files, highlighting ebooks
            ebook_extensions = {'.epub', '.pdf', '.mobi', '.azw', '.azw3', '.txt'}
            for item in files:
                if item.suffix.lower() in ebook_extensions:
                    click.echo(f"📚 {item.name}")
                else:
                    click.echo(f"📄 {item.name}")
                    
        except PermissionError:
            click.echo(f"Permission denied: {target_dir}", err=True)
        except OSError as e:
            click.echo(f"Error: {e}", err=True)
    
    def cmd_add(self, args: List[str]):
        """Add book(s) to RAG system."""
        if not args:
            click.echo("Usage: add <file_or_directory>")
            return
        
        if not RAG_AVAILABLE:
            click.echo("RAG system not available. Please check installation.", err=True)
            return
        
        path_str = args[0]
        if path_str == '.':
            path = self.current_directory
        else:
            path = Path(path_str)
            if not path.is_absolute():
                path = self.current_directory / path
        
        try:
            if not path.exists():
                click.echo(f"Path not found: {path}", err=True)
                return
            
            # DocumentProcessor is initialized in __init__
            if path.is_file():
                click.echo(f"Adding book: {path.name}")
                with click.progressbar(length=1, label='Processing') as bar:
                    result = self.processor.add_document(str(path))
                    bar.update(1)
                success = result.get('success', False)
                title = result.get('title') or result.get('metadata', {}).get('title') or path.name
                if success:
                    click.echo(f"✓ Book '{title}' added successfully")
                    if msg := result.get('message'):
                        click.echo(msg)
                else:
                    err_msg = result.get('error') or result.get('message') or 'Unknown error'
                    if result.get('skipped'):
                        click.echo(f"⚠ Skipped '{title}': {err_msg}")
                    else:
                        click.echo(f"✗ Failed to add book '{title}': {err_msg}", err=True)
            elif path.is_dir():
                click.echo(f"Adding books from directory: {path}")
                ebook_extensions = {'.epub', '.pdf', '.mobi', '.azw', '.azw3', '.txt'}
                ebook_files = []
                for ext in ebook_extensions:
                    ebook_files.extend(path.glob(f"*{ext}"))
                    ebook_files.extend(path.glob(f"*{ext.upper()}"))
                if not ebook_files:
                    click.echo("No ebook files found in directory")
                    return
                click.echo(f"Found {len(ebook_files)} ebook files")
                successful = 0
                for ebook_file in ebook_files:
                    result = self.processor.add_document(str(ebook_file))
                    if result.get('success', False):
                        successful += 1
                click.echo(f"✓ Successfully added {successful}/{len(ebook_files)} books")
            
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
    
    def _process_books_sequential(self, ebook_files: List[Path]) -> int:
        """Process books sequentially (original behavior)."""
        successful = 0
        
        with click.progressbar(ebook_files, label='Processing books') as bar:
            for ebook_file in bar:
                try:
                    result = self.rag_system.add_ebook_with_pages(str(ebook_file))
                    if isinstance(result, dict):
                        if result.get('success'):
                            successful += 1
                        elif result.get('skipped'):
                            click.echo(f"Skipped {ebook_file.name}: {result.get('message')}")
                        else:
                            click.echo(f"Failed {ebook_file.name}: {result.get('error') or result.get('message')}")
                except Exception as e:
                    click.echo(f"\nError processing {ebook_file.name}: {e}", err=True)
        
        return successful
    
    async def _process_books_parallel(self, ebook_files: List[Path]) -> int:
        """Process books in parallel using the parallel processor."""
        if not self.parallel_processor:
            return self._process_books_sequential(ebook_files)
        
        successful = 0
        
        try:
            click.echo("🔄 Starting parallel processing...")
            click.echo(f"📚 Processing {len(ebook_files)} books with {self.config.get('processing.parallel.book_workers', 3)} workers...")
            
            # Use the parallel processor to process all books
            results = await self.parallel_processor.process_books_parallel(ebook_files)
            
            # Count successful results and provide feedback
            for i, result in enumerate(results):
                book_name = ebook_files[i].name
                if result.get('success', False) or result.get('status') == 'complete':
                    successful += 1
                    click.echo(f"✓ Processed: {book_name}")
                else:
                    error_msg = result.get('error', 'Unknown error')
                    click.echo(f"✗ Failed: {book_name} - {error_msg}")
            
        except Exception as e:
            click.echo(f"Parallel processing error: {e}", err=True)
            # Fall back to sequential
            return self._process_books_sequential(ebook_files)
        
        return successful
    
    def cmd_batch(self, args: List[str]):
        """Process multiple directories in parallel (batch processing)."""
        if not args:
            click.echo("Usage: batch <directory1> <directory2> ...")
            click.echo("Example: batch Fiction/ NonFiction/ SciFi/")
            return
        
        if not RAG_AVAILABLE:
            click.echo("RAG system not available. Please check installation.", err=True)
            return
        
        # DocumentProcessor is initialized in __init__
        # Collect all directories and validate them
        directories = []
        for path_str in args:
            if path_str == '.':
                path = self.current_directory
            else:
                path = Path(path_str)
                if not path.is_absolute():
                    path = self.current_directory / path
            
            if not path.exists():
                click.echo(f"Path not found: {path}", err=True)
                continue
            
            if not path.is_dir():
                click.echo(f"Not a directory: {path}", err=True)
                continue
                
            directories.append(path)
        
        if not directories:
            click.echo("No valid directories found.", err=True)
            return
        
        click.echo(f"📦 Batch processing {len(directories)} directories...")
        
        # Collect all ebook files from all directories
        all_ebook_files = []
        ebook_extensions = {'.epub', '.pdf', '.mobi', '.azw', '.azw3', '.txt'}
        
        for directory in directories:
            dir_files = []
            for ext in ebook_extensions:
                dir_files.extend(directory.glob(f"*{ext}"))
                dir_files.extend(directory.glob(f"*{ext.upper()}"))
            
            click.echo(f"  📁 {directory.name}: {len(dir_files)} files")
            all_ebook_files.extend(dir_files)
        
        if not all_ebook_files:
            click.echo("No ebook files found in any directory.")
            return
        
        click.echo(f"\n📚 Found {len(all_ebook_files)} total ebook files")
        
        # Use parallel processing if enabled and multiple files
        if self.parallel_enabled and self.parallel_processor and len(all_ebook_files) > 1:
            click.echo("🚀 Using parallel batch processing...")
            successful = self._run_async(self._process_books_parallel(all_ebook_files))
        else:
            click.echo("📚 Processing sequentially...")
            successful = self._process_books_sequential(all_ebook_files)
        
        click.echo(f"\n✅ Batch processing complete!")
        click.echo(f"✓ Successfully processed {successful}/{len(all_ebook_files)} books")
        
        if successful < len(all_ebook_files):
            failed = len(all_ebook_files) - successful
            click.echo(f"⚠ {failed} books failed to process")

    def cmd_ask(self, args: List[str]):
        """Ask a question about your books."""
        if not args:
            click.echo("Usage: ask [--verbose] <your question>")
            click.echo("       ask --verbose What are the main themes?")
            click.echo("Example: ask What are the main themes in my collection?")
            return
        
        if not RAG_AVAILABLE:
            click.echo("RAG system not available. Please check installation.", err=True)
            return
        
        # Parse verbose flag
        verbose = False
        question_args = args[:]
        if args and (args[0] == '--verbose' or args[0] == '-v'):
            verbose = True
            question_args = args[1:]
        
        if not question_args:
            click.echo("Please provide a question after the --verbose flag")
            return
        
        # DocumentProcessor is initialized in __init__
        
        question = " ".join(question_args)
        click.echo(f"Question: {question}")
        if verbose:
            click.echo("🔍 Debug mode enabled - showing context and prompt details")
        if self.focused_book:
            click.echo(f"📖 Searching in: {self.focused_book['title']} by {self.focused_book['author']}")
        click.echo()
        
        try:
            with click.progressbar(length=1, label='Thinking') as bar:
                # Pass focused book filter if set
                book_filter = self.focused_book['book_id'] if self.focused_book else None
                response = self.rag_system.ask_question(
                    question, 
                    self.processor.ollama_processor, 
                    verbose=verbose,
                    book_filter=book_filter
                )
                bar.update(1)
            
            if verbose:
                click.echo()
            click.echo("Answer:")
            click.echo("─" * 50)
            click.echo(response)
                    
        except Exception as e:
            click.echo(f"Error processing question: {e}", err=True)

    def cmd_unfocus(self, args: List[str]):
        """Remove book focus and return to searching all books."""
        if self.focused_book:
            prev_title = self.focused_book['title']
            self.focused_book = None
            click.echo(f"📚 Unfocused from '{prev_title}' - now searching all books")
        else:
            click.echo("No book is currently focused")
        # Clear last focus matches so number selection doesn't persist
        if hasattr(self, '_last_focus_matches'):
            self._last_focus_matches = []

    def cmd_status(self, args: List[str]):
        """Show current focus status and book information."""
        if self.focused_book:
            click.echo(f"📖 Currently focused on:")
            click.echo(f"   Title: {self.focused_book['title']}")
            click.echo(f"   Author: {self.focused_book['author']}")
            click.echo(f"   Format: {self.focused_book['format']}")
            click.echo(f"   Chunks: {self.focused_book['chunks']}")
            click.echo(f"   Book ID: {self.focused_book['book_id']}")
        else:
            click.echo("📚 Not focused on any specific book - searching all books")
            if hasattr(self, 'rag_system') and self.rag_system:
                try:
                    books = self.rag_system.list_books()
                    total_chunks = sum(book['chunks'] for book in books)
                    click.echo(f"   Total books available: {len(books)}")
                    click.echo(f"   Total chunks: {total_chunks}")
                except Exception:
                    pass

    def cmd_focus(self, args: List[str]):
        """Focus on a specific book for targeted questions."""
        # Enable selection by number after ambiguous search
        if hasattr(self, '_last_focus_matches') and self._last_focus_matches and args and len(args) == 1 and args[0].isdigit():
            idx = int(args[0])
            matches = self._last_focus_matches
            if 1 <= idx <= len(matches):
                self.focused_book = matches[idx - 1]
                click.echo(f"📖 Focused on: {self.focused_book['title']} by {self.focused_book['author']}")
                click.echo(f"   Book ID: {self.focused_book['book_id']}")
                click.echo(f"   Chunks: {self.focused_book['chunks']}")
                self._last_focus_matches = []
            else:
                click.echo(f"Invalid selection. Please choose a number between 1 and {len(matches)}.")
            return

        if not args:
            click.echo("Usage: focus <book_title_or_partial_match>")
            click.echo("Example: focus Deathworlders")
            click.echo("         focus Neural Network")
            return

        if not RAG_AVAILABLE:
            click.echo("RAG system not available. Please check installation.", err=True)
            return

        # DocumentProcessor is initialized in __init__

        search_term = " ".join(args).lower()

        try:
            books = self.rag_system.list_books()
            matches = []

            # Improved matching: whole term or all words must be present
            search_words = [w for w in search_term.split() if w]
            for book in books:
                title_lower = book['title'].lower()
                author_lower = book['author'].lower()
                # Exact match (whole search term)
                if search_term == title_lower or search_term == author_lower:
                    matches.append(book)
                    continue
                # Substring match (whole search term)
                if search_term in title_lower or search_term in author_lower:
                    matches.append(book)
                    continue
                # All words present in title or author
                if (all(word in title_lower for word in search_words) or
                    all(word in author_lower for word in search_words)):
                    matches.append(book)

            if not matches:
                click.echo(f"No books found matching '{search_term}'")
                click.echo("Available books:")
                for book in books:
                    click.echo(f"  - {book['title']} by {book['author']}")
                self._last_focus_matches = []
                return

            if len(matches) == 1:
                self.focused_book = matches[0]
                click.echo(f"📖 Focused on: {self.focused_book['title']} by {self.focused_book['author']}")
                click.echo(f"   Book ID: {self.focused_book['book_id']}")
                click.echo(f"   Chunks: {self.focused_book['chunks']}")
                self._last_focus_matches = []
            else:
                click.echo(f"Multiple books match '{search_term}':")
                for i, book in enumerate(matches, 1):
                    click.echo(f"  {i}. {book['title']} by {book['author']}")
                click.echo("\nPlease be more specific or choose by number.")
                self._last_focus_matches = matches

        except Exception as e:
            click.echo(f"Error focusing on book: {e}", err=True)
    
    def cmd_unfocus(self, args: List[str]):
        """Remove book focus and return to searching all books."""
        if self.focused_book:
            prev_title = self.focused_book['title']
            self.focused_book = None
            click.echo(f"📚 Unfocused from '{prev_title}' - now searching all books")
        else:
            click.echo("No book is currently focused")
    
    def cmd_status(self, args: List[str]):
        """Show current focus status and book information."""
        if self.focused_book:
            click.echo(f"📖 Currently focused on:")
            click.echo(f"   Title: {self.focused_book['title']}")
            click.echo(f"   Author: {self.focused_book['author']}")
            click.echo(f"   Format: {self.focused_book['format']}")
            click.echo(f"   Chunks: {self.focused_book['chunks']}")
            click.echo(f"   Book ID: {self.focused_book['book_id']}")
        else:
            click.echo("📚 Not focused on any specific book - searching all books")
            if hasattr(self, 'rag_system') and self.rag_system:
                try:
                    books = self.rag_system.list_books()
                    total_chunks = sum(book['chunks'] for book in books)
                    click.echo(f"   Total books available: {len(books)}")
                    click.echo(f"   Total chunks: {total_chunks}")
                except Exception:
                    pass
    
    def cmd_list(self, args: List[str]):
        """List books in RAG system."""
        if not RAG_AVAILABLE:
            click.echo("RAG system not available. Please check installation.", err=True)
            return
        
        # DocumentProcessor is initialized in __init__
        
        try:
            books = self.processor.list_documents()
            if not books:
                click.echo("No books found in RAG system.")
                click.echo("Use 'add <file_or_directory>' to add books.")
                return
            click.echo(f"Books in RAG system ({len(books)} total):")
            click.echo("─" * 60)
            total_chunks = 0
            for i, book in enumerate(books, 1):
                title = book.get('title', 'Unknown Title')
                author = book.get('author', 'Unknown Author')
                chunks = book.get('chunks', book.get('chunk_count', 0))
                format_type = book.get('format', 'Unknown')
                total_chunks += chunks
                click.echo(f"{i:3}. {title}")
                click.echo(f"     Author: {author}")
                click.echo(f"     Chunks: {chunks:,}")
                click.echo(f"     Format: {format_type}")
                click.echo()
            click.echo("─" * 60)
            click.echo(f"📊 Total: {len(books)} books with {total_chunks:,} chunks")
        except Exception as e:
            click.echo(f"Error listing books: {e}", err=True)
    
    def cmd_search(self, args: List[str]):
        """Search for books."""
        if not args:
            click.echo("Usage: search <search_term>")
            click.echo("Example: search science fiction")
            return
        
        if not RAG_AVAILABLE:
            click.echo("RAG system not available. Please check installation.", err=True)
            return
        
        # DocumentProcessor is initialized in __init__
        
        search_term = " ".join(args)
        click.echo(f"Searching for: {search_term}")
        
        try:
            with click.progressbar(length=1, label='Searching') as bar:
                results = self.rag_system.search(search_term)
                bar.update(1)
            
            if not results:
                click.echo("No results found.")
                return
            
            click.echo(f"\nSearch results ({len(results)} found):")
            click.echo("─" * 50)
            
            for i, result in enumerate(results, 1):
                title = result.get('title', 'Unknown')
                content = result.get('content', '')[:200] + "..."
                score = result.get('score', 0)
                
                click.echo(f"{i}. {title} (relevance: {score:.2f})")
                click.echo(f"   {content}")
                click.echo()
                
        except Exception as e:
            click.echo(f"Error searching: {e}", err=True)
    
    def cmd_config(self, args: List[str]):
        """Show current configuration with RAG-focused information."""
        try:
            click.echo("🧠 RAG System Configuration:")
            click.echo(f"  Config file: {self.config.config_path}")
            click.echo()
            
            # Show RAG-specific status first
            if RAG_AVAILABLE and self.rag_system:
                try:
                    books = self.rag_system.list_books()
                    total_chunks = sum(book.get('chunk_count', 0) for book in books)
                    click.echo("📚 Knowledge Base Status:")
                    click.echo(f"  Books indexed: {len(books)}")
                    click.echo(f"  Total chunks: {total_chunks}")
                    click.echo(f"  Database path: {self.rag_system.db_path}")
                    click.echo()
                except:
                    click.echo("📚 Knowledge Base Status: Unable to load stats")
                    click.echo()
            
            # Show performance settings
            if self.parallel_enabled:
                parallel_config = self.config.get('processing.parallel', {})
                click.echo("🚀 Performance Settings:")
                click.echo(f"  Parallel processing: ENABLED")
                click.echo(f"  Book workers: {parallel_config.get('book_workers', 3)}")
                click.echo(f"  Chunk workers: {parallel_config.get('chunk_workers', 4)}")
                click.echo(f"  Batch size: {parallel_config.get('embedding_batch_size', 32)}")
                click.echo()
            else:
                click.echo("🚀 Performance Settings:")
                click.echo("  Parallel processing: DISABLED")
                click.echo()
            
            # Show LLM settings
            click.echo("🤖 Language Model Settings:")
            click.echo(f"  Model: {self.config.get('ollama.model', 'llama3.2:latest')}")
            click.echo(f"  Host: {self.config.get('ollama.host', 'http://localhost:11434')}")
            click.echo(f"  Temperature: {self.config.get('ollama.temperature', 0.7)}")
            click.echo()
            
            # Show processing settings
            click.echo("⚙️ Text Processing Settings:")
            click.echo(f"  Chunk size: {self.config.get('processing.chunk_size', 4000)}")
            click.echo(f"  Chunk overlap: {self.config.get('processing.chunk_overlap', 200)}")
            click.echo(f"  Summary mode: {self.config.get('processing.summary_mode', 'classic')}")
            
        except Exception as e:
            click.echo(f"Error showing config: {e}", err=True)
    
    def cmd_cleardb(self, args: List[str]):
        """Clear the RAG database (remove all books)."""
        if not RAG_AVAILABLE:
            click.echo("RAG system not available. Please check installation.", err=True)
            return
        
        # DocumentProcessor is initialized in __init__
        
        try:
            books = self.processor.list_documents()
            if not books:
                click.echo("📚 Database is already empty.")
                return
            
            total_chunks = sum(book.get('chunks', book.get('chunk_count', 0)) for book in books)
            
            click.echo(f"⚠️  This will remove ALL {len(books)} books ({total_chunks:,} chunks) from the database!")
            click.echo("📚 Books to be removed:")
            for book in books:
                chunk_count = book.get('chunks', book.get('chunk_count', 0))
                click.echo(f"   - {book['title']}: {chunk_count:,} chunks")
            
            # Confirm deletion
            if click.confirm("\n🗑️  Are you sure you want to clear the entire database?"):
                click.echo("🔄 Clearing database...")
                
                removed_count = 0
                with click.progressbar(books, label='Removing books') as bar:
                    for book in bar:
                        if self.processor.remove_document(book['book_id']):
                            removed_count += 1
                
                click.echo(f"✅ Successfully removed {removed_count} books from the database.")
                click.echo("📚 Database is now empty. You can re-add books with 'add <file_or_directory>'.")
            else:
                click.echo("❌ Database clear cancelled.")
                
        except Exception as e:
            click.echo(f"Error clearing database: {e}", err=True)
    
    def cmd_remove(self, args: List[str]):
        """Remove a specific book from the RAG database."""
        if not RAG_AVAILABLE:
            click.echo("RAG system not available. Please check installation.", err=True)
            return
        
        if not args:
            click.echo("Usage: remove <book_number>")
            click.echo("Use 'list' to see book numbers")
            return
        
        # DocumentProcessor is initialized in __init__
        
        try:
            book_num = int(args[0])
            books = self.processor.list_documents()
            
            if not books:
                click.echo("📚 No books in database.")
                return
            
            if book_num < 1 or book_num > len(books):
                click.echo(f"❌ Invalid book number. Please choose 1-{len(books)}")
                return
            
            book_to_remove = books[book_num - 1]
            chunk_count = book_to_remove.get('chunks', book_to_remove.get('chunk_count', 0))
            
            click.echo(f"📖 Book to remove: {book_to_remove['title']}")
            click.echo(f"👤 Author: {book_to_remove['author']}")
            click.echo(f"📄 Chunks: {chunk_count:,}")
            
            if click.confirm(f"\n🗑️  Remove '{book_to_remove['title']}' from the database?"):
                if self.processor.remove_document(book_to_remove['book_id']):
                    click.echo(f"✅ Successfully removed '{book_to_remove['title']}' from the database.")
                else:
                    click.echo(f"❌ Failed to remove '{book_to_remove['title']}'.")
            else:
                click.echo("❌ Book removal cancelled.")
                
        except ValueError:
            click.echo("❌ Please provide a valid book number")
        except Exception as e:
            click.echo(f"Error removing book: {e}", err=True)


def start_repl():
    """Entry point for starting the REPL."""
    repl = EbookREPL()
    repl.run()


if __name__ == "__main__":
    start_repl()