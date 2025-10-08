## 🆕 Recent Changes & Improvements

- **Robust Error Handling**: All commands now provide clear error messages and feedback using `click.echo`, including REPL and CLI operations.
- **Progress Bars Restored**: Book processing and batch operations show real-time progress bars for better user feedback.
- **Intelligent Batch Sizing**: Batch size for embedding is now memory-aware and can be overridden via config.
- **Config Override**: Easily override batch size and other settings in `config.yml` or via CLI commands.
- **REPL Ask Command Fixes**: The REPL's `ask` command now safely handles cases when no book is focused, with clear user feedback.
- **Focused Book Logic**: You can focus/unfocus on a specific book for targeted queries; status and feedback are shown in the REPL.
- **Parallel Processing**: Directory and batch operations use parallel workers for faster ingestion (configurable in `config.yml`).
- **Command Aliases**: Short aliases for all major commands (`q` for ask, `a` for add, `b` for batch, `l` for list, `s` for search, `c` for clear, `ll` for detailed list).
- **Config Management**: Use `config-show`, `config-set`, and `config-get` to view and update configuration at runtime.
- **Enhanced Help & Status**: REPL help and status commands show current focus, book count, and system health.
- **Verbose Mode**: Use `ask --verbose` for detailed context and debug info in answers.
- **Graceful Fallbacks**: If parallel processing fails, the system falls back to sequential mode automatically.
- **Session Persistence**: REPL maintains command history and session state for seamless workflow.

# AI Ebook Processor with RAG System

A comprehensive Python application that processes ebooks using local Ollama AI models and creates a searchable knowledge base of your entire collection through advanced RAG (Retrieval Augmented Generation) techniques.

## 🤝 Development & Collaboration

This project showcases the potential of human-AI collaboration in building sophisticated RAG systems:

- **Concept & Vision**: Original idea, architecture decisions, and quality control by [Anthony Dawson](https://github.com/anthonypdawson)
- **Implementation & Design**: Feature development, technical architecture, and system design created through collaboration with AI assistance (Claude - Anthropic)
- **Development Process**: Demonstrates effective patterns for human-AI collaboration in software development

This transparent approach highlights how AI tools can accelerate development while human expertise drives vision, requirements, and integration decisions.

## ✨ Key Features

### 🧠 Advanced RAG Features
- **Intelligent Searchable Knowledge Base**: Ask questions about your entire book collection using natural language
- **Semantic Search**: Find content by meaning and context, not just keywords  
- **Cross-Book Analysis**: Compare themes, characters, and insights across multiple books
- **AI-Powered Search Enhancement**: Dynamically generates related search terms for better context retrieval
- **Contextual Responses**: Get detailed answers with proper citations from your specific books
- **Persistent Memory**: Build and maintain a growing vector database of all your processed books

### 📚 Core Processing Features
- **Multiple Format Support**: EPUB, PDF, MOBI, AZW, AZW3, TXT, DOCX
- **Local AI Processing**: Uses Ollama models for complete privacy and control
- **Intelligent Chunking**: Smart text segmentation for optimal processing
- **Batch Processing**: Process entire directories of ebooks efficiently
- **Flexible Output**: JSON, Markdown, or plain text output formats
- **Command Line Interface**: Easy-to-use CLI with comprehensive configuration management
- **Progress Tracking**: Real-time progress bars and detailed processing statistics

## 🚀 Roadmap & Upcoming Features

See [NEXT_FEATURES.md](NEXT_FEATURES.md) for detailed roadmap including:
- **Interactive REPL Interface**: Seamless command-line interaction without repeated CLI calls
- **Auto-Discovery System**: Scan directories for ebooks, build catalogs without processing
- **Book-Specific Targeting**: Focus conversations on specific books vs. entire library  
- **Advanced Context Memory**: Graph-based conversation memory with Redis integration
- **Adaptive AI Persona**: AI personality that evolves with your reading patterns

For technical implementation details, see [IMPLEMENTATION_DETAILS.md](IMPLEMENTATION_DETAILS.md).

## 📦 Installation & Setup

### Prerequisites
1. **Python 3.9+** installed on your system
2. **uv** for dependency management (recommended) or pip
3. **Ollama** installed and running
4. At least one Ollama model downloaded

### Step 1: Install Ollama
```bash
# Visit https://ollama.ai/ for installation instructions
# Or use package managers:

# macOS
brew install ollama

# Windows - Download from website
# Linux  
curl https://ollama.ai/install.sh | sh
```

### Step 2: Download a Model
```bash
ollama pull llama2        # Recommended
ollama pull mistral       # Alternative  
ollama pull codellama     # For code analysis
```

### Step 3: Install uv (Recommended)
```bash
# Install uv (if not already installed)
pip install uv
```

### Step 4: Install the Ebook Processor

**Option A: uv Installation (Recommended)**
```bash
# Clone the repository
git clone https://github.com/anthonypdawson/ai-ebook-processor.git
cd ai-ebook-processor

# Install dependencies with uv
uv install

# 🆕 If you want to use PyTorch with CUDA 12.9 support, install with:
uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu129
```

This will install PyTorch and related libraries with CUDA 12.9 support. If you do not have a compatible NVIDIA GPU or do not need CUDA, you can skip this step.

### 🆕 REPL Command Aliases & Features

- `q <question>`: Quick alias for `ask`
- `a <file/dir>`: Quick alias for `add`
- `b <dirs...>`: Quick alias for `batch`
- `l`: Quick alias for `list`
- `s <query>`: Quick alias for `search`
- `c`: Quick alias for `clear`
- `ll`: Quick alias for detailed list

### 🆕 REPL Status & Focus

- Use `focus <search>` to target a specific book for queries
- Use `unfocus` to clear book focus and search all books
- Use `status` to show current focus and book info

### 🆕 Error Handling & Feedback

- All commands provide clear error messages and feedback
- Progress bars are shown for book processing and batch operations
- If a command fails, a helpful message is displayed
- REPL ask command handles unfocused state gracefully


# Use uv to run commands:
uv run python -m ai_ebook_processor --help
uv run python -m ai_ebook_processor rag add-book "path/to/book.epub"
```

**Option B: Package Installation**
```bash
# Clone the repository
git clone https://github.com/anthonypdawson/ai-ebook-processor.git
cd ai-ebook-processor

# Install the package
pip install -e .

# Use it anywhere
python -m ai_ebook_processor --help
python -m ai_ebook_processor rag add-book "path/to/book.epub"
```

**Option C: Direct Usage**
```bash
# Install dependencies only
pip install -r requirements.txt

# Run using module syntax
python -m ai_ebook_processor --help
python -m ai_ebook_processor rag add-book "path/to/book.epub"
```

### Step 5: Convenience Wrappers (Optional)
For even easier usage, wrapper scripts are included that work from anywhere on your system:

**Windows:**
```cmd
# Works from any directory - uses uv automatically if available
~/src/ai-ebook-processor/scripts/ebook-processor.bat --help
~/src/ai-ebook-processor/scripts/ebook-processor.bat rag add-book "book.epub"

# Or use Python wrapper (cross-platform)
python ~/src/ai-ebook-processor/scripts/ebook-processor.py --help
```

**Linux/Mac/Windows (with bash):**
```bash
# Works from any directory - uses uv automatically if available
~/src/ai-ebook-processor/scripts/ebook-processor --help
~/src/ai-ebook-processor/scripts/ebook-processor rag add-book "book.epub"
```

**Features of the wrapper scripts:**
- 🌍 Work from any directory on your system
- 🎯 Automatically use uv if available, with fallback to virtual env
- 📦 Set up proper Python paths automatically
- 🔄 Intelligent environment detection

## 🚀 Quick Start

### 1. Start Ollama
```bash
ollama serve
```

### 2. Start Interactive REPL (Recommended)
```bash
# Using uv (recommended)
uv run python -m ai_ebook_processor repl
```

**REPL Session Example:**
```bash
🤖 AI Ebook Processor REPL
Type 'help' for available commands, 'exit' to quit

[~] ebook> cd ~/Documents/Books
[Documents/Books] ebook> ls
📁 Fiction/
📁 Non-Fiction/
📚 book1.epub
📚 book2.pdf

[Documents/Books] ebook> add Fiction/
Processing 15 books... ✓ Successfully added 15/15 books

[Documents/Books] ebook> ask What are the main themes in my collection?
Answer:
──────────────────────────────────────────────────
Based on your fiction collection, the main themes include...

[Documents/Books] ebook> search "time travel"
Search results (3 found):
──────────────────────────────────────────────────
1. The Time Machine (relevance: 0.92)
   A scientist invents a machine that allows him to travel through time...
```

### 3. Traditional CLI Commands (Alternative)
```bash
# Using uv (recommended)
uv run python -m ai_ebook_processor rag add-book "path/to/your/book.epub"
uv run python -m ai_ebook_processor rag add-directory "path/to/ebooks/"
uv run python -m ai_ebook_processor rag ask "What are the main themes in my collection?"
```

### 4. Traditional Processing (Alternative)
```bash
# Using uv
uv run python -m ai_ebook_processor process-file "path/to/your/book.epub"
uv run python -m ai_ebook_processor process-file "path/to/your/book.epub"

# Process all ebooks in a directory  
uv run python -m ai_ebook_processor process-directory "path/to/ebooks/"
```

## 🖥️ CLI Commands Reference

### Main Commands
```bash
# Show all available commands
uv run python -m ai_ebook_processor --help

# Configuration management
uv run python -m ai_ebook_processor config-show                       # Show current config
uv run python -m ai_ebook_processor config-set ollama.model llama2    # Set default model  
uv run python -m ai_ebook_processor models                            # List available models

# Discover books without processing
uv run python -m ai_ebook_processor discover "path/to/ebooks/"        # Find all ebooks in directory
```

### RAG System Commands
```bash
# Import books
uv run python -m ai_ebook_processor rag add-book "book.epub"          # Add single book
uv run python -m ai_ebook_processor rag add-book "book.pdf" --fast    # Fast import (skip AI analysis)
uv run python -m ai_ebook_processor rag add-directory "path/"         # Add entire directory

# Query your collection
uv run python -m ai_ebook_processor rag ask "What themes appear in my books?"
uv run python -m ai_ebook_processor rag search "artificial intelligence"
uv run python -m ai_ebook_processor rag stats                         # Show database statistics
```

### Alternative Usage
```bash
# Use wrapper scripts from anywhere (recommended for convenience)
~/src/ai-ebook-processor/scripts/ebook-processor rag add-book "book.epub"     # Unix/bash
~/src/ai-ebook-processor/scripts/ebook-processor.bat rag add-book "book.epub" # Windows
python ~/src/ai-ebook-processor/scripts/ebook-processor.py rag add-book "book.epub" # Cross-platform

# Module execution (from project directory)
python -m ai_ebook_processor rag add-book "book.epub"       # Package module execution

# After pip install -e . (from anywhere)
ebook-processor rag add-book "book.epub"                    # If installed as package
```

## 🎯 Interactive REPL Mode

The REPL (Read-Eval-Print Loop) provides a seamless interactive experience for managing your ebook collection. No more typing long commands repeatedly!

### Starting the REPL
```bash
# Using uv (recommended)
uv run ebook-processor repl

# Using Python module
python -m ai_ebook_processor repl

# Using wrapper scripts
~/src/ai-ebook-processor/scripts/ebook-processor repl
```

### REPL Features
- **Session Persistence**: Current directory and command history maintained
- **Tab Completion**: Commands and file paths with intelligent completion
- **Command History**: Navigate previous commands with ↑/↓ arrows
- **Directory Navigation**: Built-in `cd`, `pwd`, `ls` commands
- **Command Aliases**: Short aliases for frequently used commands

### REPL Commands

**File System Navigation:**
```bash
[~] ebook> cd ~/Documents/Books         # Change directory
[Documents/Books] ebook> pwd            # Show current directory
[Documents/Books] ebook> ls             # List contents with ebook highlighting
📁 Fiction/
📁 Non-Fiction/
📚 book1.epub
📚 book2.pdf
```

**RAG Operations:**
```bash
# Add books (supports tab completion)
[Books] ebook> add book1.epub           # Add single book
[Books] ebook> add Fiction/             # Add entire directory  
[Books] ebook> add .                    # Add all books in current directory

# Query your collection
[Books] ebook> ask What are the main themes in my collection?
[Books] ebook> q Who is the protagonist in my fantasy books?  # Short alias

# Search and discover
[Books] ebook> search "time travel"     # Search for specific content
[Books] ebook> list                     # List all books in RAG system
[Books] ebook> l                        # Short alias for list
```

**Convenience Features:**
```bash
[Books] ebook> help                     # Show all commands
[Books] ebook> clear                    # Clear screen
[Books] ebook> exit                     # Exit REPL
```

### REPL Workflow Examples

**Initial Setup:**
```bash
uv run ebook-processor repl

🤖 AI Ebook Processor REPL
Type 'help' for available commands, 'exit' to quit

[~] ebook> cd ~/Documents/Calibre Library
[Calibre Library] ebook> ls
📁 Author Name/
📁 Another Author/
...

[Calibre Library] ebook> add .
Processing 127 books... ✓ Successfully added 115/127 books

[Calibre Library] ebook> list
Books in RAG system (115 total):
──────────────────────────────────────────────────
  1. The Great Gatsby
     Author: F. Scott Fitzgerald
     Chunks: 45

  2. 1984
     Author: George Orwell  
     Chunks: 62
...
```

**Interactive Analysis:**
```bash
[Calibre Library] ebook> ask What genres do I read most?
Answer:
──────────────────────────────────────────────────
Based on your collection, you primarily read:
1. Science Fiction (32% of collection)
2. Mystery/Thriller (28% of collection)
3. Literary Fiction (22% of collection)
...

📚 Sources:
1. Dune - Frank Herbert
2. The Girl with the Dragon Tattoo - Stieg Larsson
3. To Kill a Mockingbird - Harper Lee

[Calibre Library] ebook> search "artificial intelligence"
Search results (8 found):
──────────────────────────────────────────────────
1. Neuromancer (relevance: 0.94)
   The matrix has its roots in primitive arcade games...

2. I, Robot (relevance: 0.89)  
   A robot may not injure a human being or, through inaction...
```

### REPL Aliases
Save time with short command aliases:
- `q` → `ask` (query)
- `a` → `add` 
- `l` → `list`
- `s` → `search`
- `c` → `clear`
- `ll` → `list` (detailed)

### 🆕 4. RAG System - Build Your Knowledge Base

```bash
# Add a book to your searchable knowledge base
python -m ai_ebook_processor rag add-book "/path/to/book.epub"

# Add entire directory
python -m ai_ebook_processor rag add-directory "/path/to/ebooks" --max-files 10

# Ask questions about your collection
python -m ai_ebook_processor rag ask "What are the main themes in my books?"

# Search for specific content
python -m ai_ebook_processor rag search "artificial intelligence"
```

### 5. Using the Python API

```python
from ai_ebook_processor.core.processor import EbookProcessorApp
from ai_ebook_processor.rag.system import EnhancedEbookProcessor

# Traditional processing
app = EbookProcessorApp(model_name="llama2")
result = app.process_single_ebook(
    "path/to/book.epub",
    processing_type="summary",
    output_dir="output"
)

# 🆕 Enhanced processing with RAG
enhanced = EnhancedEbookProcessor(model_name="llama2")

# Process and add to knowledge base
result = enhanced.process_and_store("path/to/book.epub")

# Ask questions about your collection
answer = enhanced.ask_about_collection(
    "What are the main themes across my philosophy books?"
)
print(answer)
```

## Processing Types

- **`summary`**: Creates concise summaries of the content
- **`analysis`**: Analyzes themes, concepts, and key information
- **`extraction`**: Extracts important facts, data, and insights
- **`questions`**: Generates study questions and answers
- **`critique`**: Provides thoughtful critique and analysis
- **`simplify`**: Explains complex concepts in simpler terms

## Command Line Interface

### Basic Commands

```bash
# Show available models
python -m ai_ebook_processor models

# Discover ebooks in a directory
python -m ai_ebook_processor discover /path/to/ebooks

# Works from any directory - uses uv automatically if available
 🎯 Automatically use uv if available, with fallback to virtual env

# Using uv (recommended)
uv run python -m ai_ebook_processor repl

# Using uv (recommended)
uv run python -m ai_ebook_processor repl
  --recursive \
  --max-files 10

# Show configuration
python -m ai_ebook_processor config-show

# Set configuration values
python -m ai_ebook_processor config-set ollama.model "mistral"
python -m ai_ebook_processor config-set processing.chunk_size 5000
```

### Configuration

The application uses a YAML configuration file (`config.yml`) that's automatically created with defaults:

```yaml
ollama:
  model: llama2
  host: http://localhost:11434
  temperature: 0.7

processing:
  chunk_size: 4000
  chunk_overlap: 200
  output_format: markdown
  save_chunks: false
  processing_mode: summary

output:
  directory: output
  create_report: true
```

## Project Structure

```
ai-ebook-processor/
├── ai_ebook_processor/         # Main Python package (all source code)
│   ├── cli/                    # CLI commands and REPL interface
│   │   ├── commands.py         # CLI command definitions
│   │   ├── repl.py             # Interactive REPL shell
│   │   └── ...                 # Other CLI modules
│   ├── core/                   # Core processing logic
│   │   ├── processor.py        # Main processor class
│   │   ├── pipeline.py         # Text processing pipeline
│   │   ├── parallel.py         # Parallel processing utilities
│   │   └── ...                 # Other core modules
│   ├── models/                 # Model integrations (Ollama, etc.)
│   │   └── ollama.py           # Ollama model integration
│   ├── rag/                    # RAG system and logic
│   │   ├── system.py           # RAG system core
│   │   ├── timing.py           # Timing utilities
│   │   └── ...                 # Other RAG modules
│   ├── readers/                # Ebook format readers
│   │   └── ebook_reader.py     # EPUB/PDF/etc. reader
│   ├── utils/                  # Utility modules
│   │   ├── config.py           # Config management
│   │   ├── fast_mode.py        # Fast processing mode
│   │   └── ...                 # Other utilities
│   ├── __main__.py             # Entry point for module execution
│   └── __init__.py             # Package initializer
├── scripts/                    # CLI and convenience scripts
│   ├── ebook-processor         # Bash wrapper script
│   ├── ebook-processor.bat     # Windows batch wrapper
│   ├── ebook-processor.py      # Python wrapper script
│   └── ...                     # Other scripts
├── config/                     # Configuration files
│   └── config.yml              # Main YAML config
├── output/                     # Processed results and reports
├── ebook_db/                   # Vector database for processed books
├── pyproject.toml              # Project metadata and dependencies
├── README.md                   # Project documentation
└── NEXT_FEATURES.md            # Roadmap and upcoming features
```

## Supported File Formats

| Format | Extension | Description |
|--------|-----------|-------------|
| EPUB | `.epub` | Electronic publication format |
| PDF | `.pdf` | Portable Document Format |
| MOBI | `.mobi` | Amazon Kindle format |
| AZW/AZW3 | `.azw`, `.azw3` | Amazon Kindle formats |
| Plain Text | `.txt` | Plain text files |
| Word Document | `.docx` | Microsoft Word documents |

## ⚠️ MOBI, AZW, AZW3 Support (Experimental)

Support for Amazon Kindle formats (.mobi, .azw, .azw3) is **experimental**. Many MOBI files are image-based, DRM-protected, or use complex structures that may not be reliably processed. 

**Best Practice:** For consistent results, convert Kindle files to EPUB or PDF using [Calibre](https://calibre-ebook.com/) or similar tools before processing with AI Ebook Processor.

- DRM-protected files cannot be processed.
- Image-heavy MOBI files may yield little or no text output.
- EPUB and PDF formats are recommended for best results.

## Advanced Usage

### Custom Prompts

You can provide custom prompts for processing:

```python
custom_prompt = """
Please analyze this text for:
1. Main themes and concepts
2. Key arguments or plot points
3. Important quotes or data
4. Overall significance

Text: {text}
"""

result = app.process_single_ebook(
    "book.epub",
    custom_prompt=custom_prompt
)
```

### Processing Configuration

Customize how text is processed:

```python
app.configure_processing(
    chunk_size=3000,         # Maximum characters per chunk
    chunk_overlap=150,       # Overlap between chunks
    output_format='markdown', # json, txt, or markdown
    save_chunks=True         # Save individual chunk results
)
```

### Batch Processing with Filters

```python
# Process only specific formats
results = app.process_directory(
    "/path/to/ebooks",
    file_extensions=['.epub', '.pdf']
)

# Process with custom configuration
app.configure_processing(chunk_size=2000, output_format='json')
results = app.process_multiple_ebooks(ebook_list)
```

## Output

The application creates structured output including:

- **Individual Results**: One file per processed ebook
- **Processing Statistics**: Detailed stats about the processing session
- **Combined Report**: Summary of all processed books
- **Error Logs**: Information about any processing failures

### Output Formats

#### JSON (Default)
```json
{
  "metadata": {
    "title": "Book Title",
    "author": "Author Name",
    "format": "EPUB"
  },
  "chunk_info": {
    "total_chunks": 15,
    "successful_chunks": 15
  },
  "combined_result": "Processed content...",
  "processing_stats": {
    "processing_time": 45.2,
    "success_rate": 1.0
  }
}
```

#### Markdown
```markdown
# Book Title

**Author:** Author Name
**Processed:** 2024-01-15T10:30:00

## Analysis Results

Processed content appears here...
```

## Troubleshooting

### Common Issues

1. **"No Ollama models found"**
   - Make sure Ollama is running: `ollama serve`
   - Install a model: `ollama pull llama2`

2. **"Error connecting to Ollama"**
   - Check if Ollama is running on the correct host/port
   - Verify the model name in configuration

3. **"No text content extracted"**
   - File might be corrupted or DRM-protected
   - Try a different file format
   - Check file permissions

4. **Slow processing**
   - Reduce chunk size in configuration
   - Use a faster model (e.g., `phi` instead of `llama2`)
   - Process fewer files at once

### Performance Tips

- Use smaller chunk sizes for faster processing
- Choose appropriate models for your hardware
- Process files in smaller batches for large collections
- Monitor system resources during processing

## Dependencies

- `ollama`: Ollama Python client
- `ebooklib`: EPUB file processing
- `PyMuPDF`: PDF file processing
- `python-docx`: Word document processing
- `chardet`: Character encoding detection
- `tqdm`: Progress bars
- `click`: Command line interface
- `pyyaml`: YAML configuration files

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is provided as-is for educational and personal use.

## Acknowledgments

- [Ollama](https://ollama.ai) for local AI model hosting
- [ebooklib](https://github.com/aerkalov/ebooklib) for EPUB processing
- [PyMuPDF](https://pymupdf.readthedocs.io/) for PDF processing
- All the open-source contributors who made this possible

---

**Note**: This tool is designed for processing your own ebook collection. Respect copyright laws and DRM restrictions when using this software.