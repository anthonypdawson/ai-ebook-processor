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
1. **Python 3.8+** installed on your system
2. **Ollama** installed and running
3. At least one Ollama model downloaded

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

### Step 3: Install the Ebook Processor

**Option A: Package Installation (Recommended)**
```bash
# Clone the repository
git clone https://github.com/anthonypdawson/ai-ebook-processor.git
cd ai-ebook-processor

# Install the package
pip install -e .

# Now you can use clean CLI commands:
python -m cli --help
python -m cli rag add-book "path/to/book.epub"
```

**Option B: Direct Usage**
```bash
# Install dependencies only
pip install -r requirements.txt

# Run directly
python cli.py --help
python cli.py rag add-book "path/to/book.epub"
```

### Step 4: Convenience Wrappers (Optional)
For even easier usage, wrapper scripts are included:

**Windows:**
```cmd
ebook-processor.bat --help
ebook-processor.bat rag add-book "book.epub"
```

**Linux/Mac:**
```bash
./ebook-processor --help
./ebook-processor rag add-book "book.epub"
```

## 🚀 Quick Start

### 1. Start Ollama
```bash
ollama serve
```

### 2. Import Books to RAG System (Recommended)
```bash
# Import a single book
python -m cli rag add-book "path/to/your/book.epub"

# Import entire directory
python -m cli rag add-directory "path/to/ebooks/"

# Ask questions about your books
python -m cli rag ask "What are the main themes in my collection?"
```

### 3. Traditional Processing (Alternative)
```bash
# Process a single ebook
python -m cli process-file "path/to/your/book.epub"

# Process all ebooks in a directory  
python -m cli process-directory "path/to/ebooks/"
```

## 🖥️ CLI Commands Reference

### Main Commands
```bash
# Show all available commands
python -m cli --help

# Configuration management
python -m cli config-show                    # Show current config
python -m cli config-set ollama.model llama2 # Set default model  
python -m cli models                         # List available models

# Discover books without processing
python -m cli discover "path/to/ebooks/"     # Find all ebooks in directory
```

### RAG System Commands
```bash
# Import books
python -m cli rag add-book "book.epub"       # Add single book
python -m cli rag add-book "book.pdf" --fast # Fast import (skip AI analysis)
python -m cli rag add-directory "path/"      # Add entire directory

# Query your collection
python -m cli rag ask "What themes appear in my books?"
python -m cli rag search "artificial intelligence"
python -m cli rag stats                      # Show database statistics
```

### Alternative Usage
```bash
# Use wrapper scripts (after installation)
ebook-processor.bat rag add-book "book.epub"     # Windows
./ebook-processor rag add-book "book.epub"       # Linux/Mac

# Traditional method
python cli.py rag add-book "book.epub"           # Direct file execution
```

### 🆕 4. RAG System - Build Your Knowledge Base

```bash
# Add a book to your searchable knowledge base
python cli.py rag add-book "/path/to/book.epub"

# Add entire directory
python cli.py rag add-directory "/path/to/ebooks" --max-files 10

# Ask questions about your collection
python cli.py rag ask "What are the main themes in my books?"

# Search for specific content
python cli.py rag search "artificial intelligence"
```

### 5. Using the Python API

```python
from main import EbookProcessorApp
from rag_system import EnhancedEbookProcessor

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
python cli.py models

# Discover ebooks in a directory
python cli.py discover /path/to/ebooks

# Process a single file
python cli.py process-file book.epub --type analysis

# Process directory with custom settings
python cli.py process-directory /path/to/ebooks \
  --type summary \
  --output results \
  --recursive \
  --max-files 10

# Show configuration
python cli.py config-show

# Set configuration values
python cli.py config-set ollama.model "mistral"
python cli.py config-set processing.chunk_size 5000
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
ebook-processor/
├── main.py              # Main application class
├── cli.py               # Command line interface
├── ebook_reader.py      # Ebook format readers
├── ollama_processor.py  # Ollama integration
├── text_pipeline.py     # Text processing pipeline
├── example.py           # Usage examples
├── config.yml           # Configuration file (auto-generated)
├── requirements.txt     # Python dependencies
└── README.md           # This file
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