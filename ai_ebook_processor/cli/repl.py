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
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any

import click

from ai_ebook_processor.core.processor import EbookProcessorApp
from ai_ebook_processor.utils.config import Config

# Import RAG functionality
try:
    from ai_ebook_processor.rag.system import EnhancedEbookProcessor, EbookRAGSystem
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False


class EbookREPL:
    """Interactive REPL for ebook processing and RAG operations."""
    
    def __init__(self):
        self.current_directory = Path.cwd()
        self.rag_system = None
        self.processor = None
        self.config = Config()
        self.history_file = Path.home() / ".ebook_processor_history"
        self.running = True
        
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
            'ask': self.cmd_ask,
            'list': self.cmd_list,
            'search': self.cmd_search,
            'config': self.cmd_config,
            'clear': self.cmd_clear,
        }
        
        # Command aliases for convenience
        self.aliases: Dict[str, str] = {
            'q': 'ask',
            'a': 'add',
            'l': 'list',
            's': 'search',
            'c': 'clear',
            'll': 'list',
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
        """Initialize RAG system and processor."""
        try:
            # Get model name from config
            model_name = self.config.get('ollama.model', 'llama3.2:latest')
            ollama_host = self.config.get('ollama.host', 'http://localhost:11434')
            
            self.rag_system = EbookRAGSystem()
            self.processor = EbookProcessorApp(model_name=model_name, ollama_host=ollama_host)
            click.echo("✓ Systems initialized successfully")
        except Exception as e:
            click.echo(f"⚠ Warning: Could not initialize systems: {e}", err=True)
    
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
        click.echo("🤖 AI Ebook Processor REPL")
        click.echo("Type 'help' for available commands, 'exit' to quit")
        click.echo(f"Current directory: {self.current_directory}")
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
        
        click.echo("🧠 RAG Operations:")
        click.echo("  add <file/dir>    Add book(s) to RAG knowledge base")
        click.echo("                    Examples: add book.epub")
        click.echo("                              add Fiction/")
        click.echo("                              add .  (current directory)")
        click.echo()
        click.echo("  ask <question>    Ask questions about your book collection")
        click.echo("                    Examples: ask What themes appear in my books?")
        click.echo("                              ask Who is the main character in 1984?")
        click.echo()
        click.echo("  list              List all books in your RAG system")
        click.echo("  search <term>     Search for specific content in your books")
        click.echo("                    Example: search \"artificial intelligence\"")
        click.echo()
        
        click.echo("⚙️  Configuration:")
        click.echo("  config            Show current system configuration")
        click.echo()
        
        click.echo("🚀 Quick Aliases (save typing):")
        click.echo("  q  → ask          Quick queries")
        click.echo("  a  → add          Quick book adding")  
        click.echo("  l  → list         Quick book listing")
        click.echo("  ll → list         Detailed book listing")
        click.echo("  s  → search       Quick searching")
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
            
            # Initialize RAG system if needed
            if not self.rag_system:
                self.rag_system = EbookRAGSystem()
            
            if path.is_file():
                click.echo(f"Adding book: {path.name}")
                with click.progressbar(length=1, label='Processing') as bar:
                    result = self.rag_system.add_book(str(path))
                    bar.update(1)
                    
                if result.get('success'):
                    click.echo(f"✓ Book '{result.get('title', path.name)}' added successfully")
                else:
                    click.echo(f"✗ Failed to add book: {result.get('error', 'Unknown error')}", err=True)
                    
            elif path.is_dir():
                click.echo(f"Adding books from directory: {path}")
                
                # Find ebook files
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
                
                with click.progressbar(ebook_files, label='Processing books') as bar:
                    for ebook_file in bar:
                        try:
                            result = self.rag_system.add_book(str(ebook_file))
                            if result.get('success'):
                                successful += 1
                        except Exception as e:
                            click.echo(f"\nError processing {ebook_file.name}: {e}", err=True)
                
                click.echo(f"✓ Successfully added {successful}/{len(ebook_files)} books")
            else:
                click.echo(f"Path is neither file nor directory: {path}", err=True)
                
        except Exception as e:
            click.echo(f"Error adding books: {e}", err=True)
    
    def cmd_ask(self, args: List[str]):
        """Ask a question about your books."""
        if not args:
            click.echo("Usage: ask <your question>")
            click.echo("Example: ask What are the main themes in my collection?")
            return
        
        if not RAG_AVAILABLE:
            click.echo("RAG system not available. Please check installation.", err=True)
            return
        
        # Initialize RAG system if needed
        if not self.rag_system:
            try:
                self.rag_system = EbookRAGSystem()
            except Exception as e:
                click.echo(f"Could not initialize RAG system: {e}", err=True)
                return
        
        question = " ".join(args)
        click.echo(f"Question: {question}")
        click.echo()
        
        try:
            with click.progressbar(length=1, label='Thinking') as bar:
                response = self.rag_system.ask_question(question, self.processor.ollama_processor)
                bar.update(1)
            
            click.echo("Answer:")
            click.echo("─" * 50)
            click.echo(response)
                    
        except Exception as e:
            click.echo(f"Error processing question: {e}", err=True)
    
    def cmd_list(self, args: List[str]):
        """List books in RAG system."""
        if not RAG_AVAILABLE:
            click.echo("RAG system not available. Please check installation.", err=True)
            return
        
        # Initialize RAG system if needed
        if not self.rag_system:
            try:
                self.rag_system = EbookRAGSystem()
            except Exception as e:
                click.echo(f"Could not initialize RAG system: {e}", err=True)
                return
        
        try:
            books = self.rag_system.list_books()
            
            if not books:
                click.echo("No books found in RAG system.")
                click.echo("Use 'add <file_or_directory>' to add books.")
                return
            
            click.echo(f"Books in RAG system ({len(books)} total):")
            click.echo("─" * 50)
            
            for i, book in enumerate(books, 1):
                title = book.get('title', 'Unknown Title')
                author = book.get('author', 'Unknown Author')
                chunks = book.get('chunk_count', 0)
                click.echo(f"{i:3}. {title}")
                click.echo(f"     Author: {author}")
                click.echo(f"     Chunks: {chunks}")
                click.echo()
                
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
        
        # Initialize RAG system if needed  
        if not self.rag_system:
            try:
                self.rag_system = EbookRAGSystem()
            except Exception as e:
                click.echo(f"Could not initialize RAG system: {e}", err=True)
                return
        
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
        """Show current configuration."""
        try:
            click.echo("Current configuration:")
            click.echo(f"  Config file: {self.config.config_path}")
            click.echo()
            
            # Display configuration sections
            for section, values in self.config.config.items():
                click.echo(f"[{section}]")
                if isinstance(values, dict):
                    for key, value in values.items():
                        click.echo(f"  {key}: {value}")
                else:
                    click.echo(f"  {values}")
                click.echo()
        except Exception as e:
            click.echo(f"Error showing config: {e}", err=True)


def start_repl():
    """Entry point for starting the REPL."""
    repl = EbookREPL()
    repl.run()


if __name__ == "__main__":
    start_repl()