"""
Ebook Reader Module

This module provides functionality to read and extract text from various ebook formats
including EPUB, PDF, MOBI, TXT, DOCX, and more.
"""

import os
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

# Third-party imports
import fitz  # PyMuPDF
from ebooklib import epub
import chardet
from docx import Document

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EbookReader:
    """Main class for reading various ebook formats"""
    
    SUPPORTED_FORMATS = {'.epub', '.pdf', '.txt', '.docx', '.mobi', '.azw', '.azw3'}
    
    def __init__(self):
        self.text_content = ""
        self.metadata = {}
    
    def read_ebook(self, file_path: str) -> Tuple[str, Dict]:
        """
        Read an ebook and extract its text content and metadata
        
        Args:
            file_path (str): Path to the ebook file
            
        Returns:
            Tuple[str, Dict]: Extracted text content and metadata
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
            
        extension = file_path.suffix.lower()
        
        if extension not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported format: {extension}")
        
        try:
            if extension == '.epub':
                return self._read_epub(file_path)
            elif extension == '.pdf':
                return self._read_pdf(file_path)
            elif extension == '.txt':
                return self._read_txt(file_path)
            elif extension == '.docx':
                return self._read_docx(file_path)
            elif extension in {'.mobi', '.azw', '.azw3'}:
                return self._read_kindle_format(file_path)
            else:
                raise ValueError(f"Handler not implemented for: {extension}")
                
        except Exception as e:
            logger.error(f"Error reading {file_path}: {str(e)}")
            raise
    
    def _read_epub(self, file_path: Path) -> Tuple[str, Dict]:
        """Read EPUB format"""
        try:
            book = epub.read_epub(str(file_path))
            
            # Extract metadata
            metadata = {
                'title': book.get_metadata('DC', 'title')[0][0] if book.get_metadata('DC', 'title') else 'Unknown',
                'author': book.get_metadata('DC', 'creator')[0][0] if book.get_metadata('DC', 'creator') else 'Unknown',
                'language': book.get_metadata('DC', 'language')[0][0] if book.get_metadata('DC', 'language') else 'Unknown',
                'format': 'EPUB',
                'file_path': str(file_path)
            }
            
            # Extract text content
            text_content = []
            for item in book.get_items():
                if item.get_type() == 9:  # XHTML content
                    try:
                        # Parse HTML content and extract text
                        content = item.get_content().decode('utf-8')
                        text = self._extract_text_from_html(content)
                        if text.strip():
                            text_content.append(text)
                    except Exception as e:
                        logger.warning(f"Error extracting text from EPUB item: {e}")
                        continue
            
            return '\n\n'.join(text_content), metadata
            
        except Exception as e:
            logger.error(f"Error reading EPUB file: {e}")
            raise
    
    def _read_pdf(self, file_path: Path) -> Tuple[str, Dict]:
        """Read PDF format"""
        try:
            doc = fitz.open(str(file_path))
            
            # Extract metadata
            metadata = {
                'title': doc.metadata.get('title', 'Unknown'),
                'author': doc.metadata.get('author', 'Unknown'),
                'format': 'PDF',
                'pages': doc.page_count,
                'file_path': str(file_path)
            }
            
            # Extract text content
            text_content = []
            for page_num in range(doc.page_count):
                page = doc[page_num]
                text = page.get_text()
                if text.strip():
                    text_content.append(text)
            
            doc.close()
            return '\n\n'.join(text_content), metadata
            
        except Exception as e:
            logger.error(f"Error reading PDF file: {e}")
            raise
    
    def _read_txt(self, file_path: Path) -> Tuple[str, Dict]:
        """Read plain text format"""
        try:
            # Detect encoding
            with open(file_path, 'rb') as f:
                raw_data = f.read()
                result = chardet.detect(raw_data)
                encoding = result['encoding'] or 'utf-8'
            
            # Read the file with detected encoding
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
            
            metadata = {
                'title': file_path.stem,
                'author': 'Unknown',
                'format': 'TXT',
                'encoding': encoding,
                'file_path': str(file_path)
            }
            
            return content, metadata
            
        except Exception as e:
            logger.error(f"Error reading TXT file: {e}")
            raise
    
    def _read_docx(self, file_path: Path) -> Tuple[str, Dict]:
        """Read DOCX format"""
        try:
            doc = Document(str(file_path))
            
            # Extract metadata
            metadata = {
                'title': doc.core_properties.title or file_path.stem,
                'author': doc.core_properties.author or 'Unknown',
                'format': 'DOCX',
                'file_path': str(file_path)
            }
            
            # Extract text content
            text_content = []
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_content.append(paragraph.text)
            
            return '\n\n'.join(text_content), metadata
            
        except Exception as e:
            logger.error(f"Error reading DOCX file: {e}")
            raise
    
    def _read_kindle_format(self, file_path: Path) -> Tuple[str, Dict]:
        """Read Kindle formats (MOBI, AZW, AZW3)"""
        try:
            # Try to use PyMuPDF which supports some Kindle formats
            doc = fitz.open(str(file_path))
            
            # Try to get metadata from the document
            doc_title = doc.metadata.get('title', '').strip()
            doc_author = doc.metadata.get('author', '').strip()
            
            # If metadata is empty, try to extract from filename
            if not doc_title:
                # Try to extract title from filename (remove author part if present)
                filename = file_path.stem
                # Look for patterns like "Title - Author" or "Title by Author"
                if ' - ' in filename:
                    doc_title = filename.split(' - ')[0].strip()
                elif ' by ' in filename:
                    doc_title = filename.split(' by ')[0].strip()
                else:
                    doc_title = filename
            
            if not doc_author:
                # Try to extract author from filename
                filename = file_path.stem
                if ' - ' in filename and len(filename.split(' - ')) > 1:
                    doc_author = filename.split(' - ')[-1].strip()
                elif ' by ' in filename and len(filename.split(' by ')) > 1:
                    doc_author = filename.split(' by ')[-1].strip()
            
            metadata = {
                'title': doc_title or file_path.stem,
                'author': doc_author or 'Unknown',
                'format': file_path.suffix.upper(),
                'pages': doc.page_count,
                'file_path': str(file_path)
            }
            
            text_content = []
            for page_num in range(doc.page_count):
                page = doc[page_num]
                text = page.get_text()
                if text.strip():
                    text_content.append(text)
            
            doc.close()
            
            if not text_content:
                # If PyMuPDF couldn't extract text, we might need a specialized library
                logger.warning(f"Could not extract text from {file_path}. You might need additional tools for DRM-protected Kindle files.")
                return "", metadata
            
            return '\n\n'.join(text_content), metadata
            
        except Exception as e:
            logger.error(f"Error reading Kindle format: {e}")
            raise
    
    def _extract_text_from_html(self, html_content: str) -> str:
        """Extract plain text from HTML content"""
        try:
            # Simple HTML tag removal (basic approach)
            import re
            # Remove script and style elements
            html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
            html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
            # Remove HTML tags
            text = re.sub(r'<[^>]+>', '', html_content)
            # Clean up whitespace
            text = re.sub(r'\s+', ' ', text)
            return text.strip()
        except Exception as e:
            logger.warning(f"Error extracting text from HTML: {e}")
            return ""
    
    @classmethod
    def find_ebooks(cls, directory: str, recursive: bool = True) -> List[str]:
        """
        Find all supported ebook files in a directory
        
        Args:
            directory (str): Directory to search
            recursive (bool): Whether to search recursively
            
        Returns:
            List[str]: List of ebook file paths
        """
        ebook_files = []
        directory = Path(directory)
        
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        pattern = "**/*" if recursive else "*"
        
        for file_path in directory.glob(pattern):
            if file_path.is_file() and file_path.suffix.lower() in cls.SUPPORTED_FORMATS:
                ebook_files.append(str(file_path))
        
        return sorted(ebook_files)
    
    def get_book_info(self, file_path: str) -> Dict:
        """Get basic information about an ebook without reading full content"""
        file_path = Path(file_path)
        
        basic_info = {
            'file_name': file_path.name,
            'file_size': file_path.stat().st_size,
            'format': file_path.suffix.lower(),
            'file_path': str(file_path)
        }
        
        try:
            # Try to get metadata without reading full content
            if file_path.suffix.lower() == '.epub':
                book = epub.read_epub(str(file_path))
                basic_info.update({
                    'title': book.get_metadata('DC', 'title')[0][0] if book.get_metadata('DC', 'title') else 'Unknown',
                    'author': book.get_metadata('DC', 'creator')[0][0] if book.get_metadata('DC', 'creator') else 'Unknown'
                })
            elif file_path.suffix.lower() == '.pdf':
                doc = fitz.open(str(file_path))
                basic_info.update({
                    'title': doc.metadata.get('title', file_path.stem),
                    'author': doc.metadata.get('author', 'Unknown'),
                    'pages': doc.page_count
                })
                doc.close()
        except Exception as e:
            logger.warning(f"Could not extract metadata from {file_path}: {e}")
        
        return basic_info


# Example usage and testing
if __name__ == "__main__":
    reader = EbookReader()
    
    # Example: Find all ebooks in a directory
    # ebooks = EbookReader.find_ebooks("/path/to/your/ebooks")
    # print(f"Found {len(ebooks)} ebooks")
    
    # Example: Read a specific ebook
    # text, metadata = reader.read_ebook("path/to/your/book.epub")
    # print(f"Title: {metadata['title']}")
    # print(f"Author: {metadata['author']}")
    # print(f"Content length: {len(text)} characters")