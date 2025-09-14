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
    
    def _find_and_parse_opf(self, file_path: Path) -> Dict:
        """
        Look for and parse metadata.opf file in the same directory
        
        Args:
            file_path: Path to the ebook file
            
        Returns:
            Dictionary with OPF metadata or empty dict if not found
        """
        opf_metadata = {}
        
        try:
            # Look for metadata.opf in the same directory
            opf_path = file_path.parent / "metadata.opf"
            
            if opf_path.exists():
                logger.info(f"Found OPF metadata file: {opf_path}")
                opf_metadata = self._parse_opf_file(opf_path)
            else:
                # Also look for any .opf file in the directory
                opf_files = list(file_path.parent.glob("*.opf"))
                if opf_files:
                    logger.info(f"Found OPF file: {opf_files[0]}")
                    opf_metadata = self._parse_opf_file(opf_files[0])
                    
        except Exception as e:
            logger.warning(f"Error looking for OPF metadata: {e}")
        
        return opf_metadata
    
    def _parse_opf_file(self, opf_path: Path) -> Dict:
        """
        Parse an OPF (Open Packaging Format) metadata file
        
        Args:
            opf_path: Path to the OPF file
            
        Returns:
            Dictionary with parsed metadata
        """
        metadata = {}
        
        try:
            tree = ET.parse(opf_path)
            root = tree.getroot()
            
            # OPF files use namespaces, so we need to handle them
            namespaces = {
                'opf': 'http://www.idpf.org/2007/opf',
                'dc': 'http://purl.org/dc/elements/1.1/',
                'dcterms': 'http://purl.org/dc/terms/',
                'calibre': 'http://calibre.kovidgoyal.net/2009/metadata'
            }
            
            # Find metadata section
            metadata_elem = root.find('.//opf:metadata', namespaces)
            if metadata_elem is None:
                # Try without namespace
                metadata_elem = root.find('.//metadata')
            
            if metadata_elem is not None:
                # Extract standard Dublin Core metadata
                title = metadata_elem.find('.//dc:title', namespaces)
                if title is not None:
                    metadata['title'] = title.text.strip()
                
                # Authors (there can be multiple)
                authors = metadata_elem.findall('.//dc:creator', namespaces)
                if authors:
                    author_names = [author.text.strip() for author in authors if author.text]
                    metadata['author'] = ', '.join(author_names)
                
                # Other metadata
                description = metadata_elem.find('.//dc:description', namespaces)
                if description is not None:
                    metadata['description'] = description.text.strip()
                
                publisher = metadata_elem.find('.//dc:publisher', namespaces)
                if publisher is not None:
                    metadata['publisher'] = publisher.text.strip()
                
                language = metadata_elem.find('.//dc:language', namespaces)
                if language is not None:
                    metadata['language'] = language.text.strip()
                
                # Publication date
                date = metadata_elem.find('.//dc:date', namespaces)
                if date is not None:
                    metadata['publication_date'] = date.text.strip()
                
                # ISBN
                isbn = metadata_elem.find('.//dc:identifier[@opf:scheme="ISBN"]', namespaces)
                if isbn is not None:
                    metadata['isbn'] = isbn.text.strip()
                
                # Subject/Tags
                subjects = metadata_elem.findall('.//dc:subject', namespaces)
                if subjects:
                    tags = [subject.text.strip() for subject in subjects if subject.text]
                    metadata['tags'] = tags
                    metadata['genre'] = ', '.join(tags[:3])  # First few tags as genre
                
                # Calibre-specific metadata
                series = metadata_elem.find('.//meta[@name="calibre:series"]', namespaces)
                if series is not None:
                    metadata['series'] = series.get('content', '').strip()
                
                series_index = metadata_elem.find('.//meta[@name="calibre:series_index"]', namespaces)
                if series_index is not None:
                    metadata['series_index'] = series_index.get('content', '').strip()
                
                rating = metadata_elem.find('.//meta[@name="calibre:rating"]', namespaces)
                if rating is not None:
                    metadata['rating'] = rating.get('content', '').strip()
                
                logger.info(f"Parsed OPF metadata: {len(metadata)} fields")
                
        except ET.ParseError as e:
            logger.error(f"Error parsing OPF file {opf_path}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error parsing OPF file {opf_path}: {e}")
        
        return metadata
    
    def read_ebook_with_pages(self, file_path: str) -> Tuple[str, Dict, List[Dict]]:
        """
        Read ebook with page-aware content extraction for citations
        
        Args:
            file_path (str): Path to the ebook file
            
        Returns:
            Tuple[str, Dict, List[Dict]]: (full_text, metadata, page_info)
                page_info is a list of dicts with 'page_num', 'content', 'start_pos', 'end_pos'
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        format_type = file_path.suffix.lower()
        
        if format_type not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported format: {format_type}")
        
        logger.info(f"Reading ebook with page tracking: {file_path}")
        
        # Read with page awareness
        if format_type == '.epub':
            text, metadata, pages = self._read_epub_with_pages(file_path)
        elif format_type == '.pdf':
            text, metadata, pages = self._read_pdf_with_pages(file_path)
        elif format_type in ['.txt']:
            text, metadata, pages = self._read_txt_with_pages(file_path)
        elif format_type == '.docx':
            text, metadata, pages = self._read_docx_with_pages(file_path)
        elif format_type in ['.mobi', '.azw', '.azw3']:
            text, metadata, pages = self._read_mobi_with_pages(file_path)
        else:
            raise ValueError(f"Format {format_type} not yet supported for page tracking")
        
        # Merge with OPF metadata if available
        opf_metadata = self._find_and_parse_opf(file_path)
        if opf_metadata:
            # Merge OPF metadata with extracted metadata, preferring extracted metadata
            merged_metadata = {**opf_metadata, **metadata}
            logger.info(f"Merged OPF metadata for {merged_metadata.get('title', 'Unknown')}")
            metadata = merged_metadata
        
        self.text_content = text
        self.metadata = metadata
        
        return text, metadata, pages

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
            # Read format-specific content and metadata
            if extension == '.epub':
                text, format_metadata = self._read_epub(file_path)
            elif extension == '.pdf':
                text, format_metadata = self._read_pdf(file_path)
            elif extension == '.txt':
                text, format_metadata = self._read_txt(file_path)
            elif extension == '.docx':
                text, format_metadata = self._read_docx(file_path)
            elif extension in {'.mobi', '.azw', '.azw3'}:
                text, format_metadata = self._read_kindle_format(file_path)
            else:
                raise ValueError(f"Handler not implemented for: {extension}")
            
            # Look for OPF metadata in the same directory
            opf_metadata = self._find_and_parse_opf(file_path)
            
            # Merge metadata, with OPF taking precedence for richer data
            final_metadata = format_metadata.copy()
            if opf_metadata:
                # OPF metadata has priority, but don't overwrite with empty values
                for key, value in opf_metadata.items():
                    if value and value.strip():  # Only use non-empty values
                        final_metadata[key] = value
                logger.info(f"Enhanced metadata with OPF data: {list(opf_metadata.keys())}")
            
            return text, final_metadata
                
        except Exception as e:
            logger.error(f"Error reading {file_path}: {str(e)}")
            raise
    
    def _read_epub_with_pages(self, file_path: Path) -> Tuple[str, Dict, List[Dict]]:
        """Read EPUB format with estimated page tracking based on content length"""
        try:
            book = epub.read_epub(str(file_path))
            
            # Extract metadata
            title = book.get_metadata('DC', 'title')
            author = book.get_metadata('DC', 'creator')
            
            metadata = {
                'title': title[0][0] if title else file_path.stem,
                'author': author[0][0] if author else 'Unknown',
                'format': 'EPUB',
                'file_path': str(file_path)
            }
            
            # Extract text content from all readable items
            text_content = []
            page_info = []
            current_pos = 0
            estimated_page = 1
            
            # Estimate characters per page (typical book page ~2000-2500 chars)
            chars_per_page = 2200
            chars_in_current_page = 0
            current_page_content = []
            
            for item in book.get_items():
                if item.get_type() == ebooklib.ITEM_DOCUMENT:
                    try:
                        content = item.get_content().decode('utf-8')
                        
                        # Parse HTML content
                        from bs4 import BeautifulSoup
                        soup = BeautifulSoup(content, 'html.parser')
                        
                        # Remove script and style elements
                        for script in soup(["script", "style"]):
                            script.decompose()
                        
                        # Get text content
                        text = soup.get_text()
                        
                        # Clean up text
                        lines = (line.strip() for line in text.splitlines())
                        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                        text = '\n'.join(chunk for chunk in chunks if chunk)
                        
                        if text.strip():
                            # Add to current page or create new pages based on length
                            remaining_text = text
                            
                            while remaining_text:
                                # How much space left in current page?
                                space_left = chars_per_page - chars_in_current_page
                                
                                if len(remaining_text) <= space_left:
                                    # All remaining text fits in current page
                                    current_page_content.append(remaining_text)
                                    chars_in_current_page += len(remaining_text)
                                    remaining_text = ""
                                else:
                                    # Split text at word boundary near page limit
                                    split_point = space_left
                                    # Find good break point (word boundary)
                                    while split_point > space_left * 0.8 and split_point > 0:
                                        if remaining_text[split_point] in ' \n\t.':
                                            break
                                        split_point -= 1
                                    
                                    if split_point <= space_left * 0.8:
                                        split_point = space_left  # Force split
                                    
                                    # Add chunk to current page
                                    chunk = remaining_text[:split_point]
                                    current_page_content.append(chunk)
                                    
                                    # Finalize current page
                                    page_content = '\n'.join(current_page_content)
                                    page_info.append({
                                        'page_num': estimated_page,
                                        'content': page_content,
                                        'start_pos': current_pos,
                                        'end_pos': current_pos + len(page_content),
                                        'page_type': 'estimated'  # This is an estimated page
                                    })
                                    
                                    text_content.append(page_content)
                                    current_pos += len(page_content) + 2
                                    
                                    # Start new page
                                    estimated_page += 1
                                    chars_in_current_page = 0
                                    current_page_content = []
                                    remaining_text = remaining_text[split_point:].lstrip()
                    
                    except Exception as e:
                        logger.warning(f"Error processing EPUB item {item.get_name()}: {e}")
                        continue
            
            # Add final page if there's remaining content
            if current_page_content:
                page_content = '\n'.join(current_page_content)
                page_info.append({
                    'page_num': estimated_page,
                    'content': page_content,
                    'start_pos': current_pos,
                    'end_pos': current_pos + len(page_content),
                    'page_type': 'estimated'
                })
                text_content.append(page_content)
            
            # Update metadata with estimated page count
            metadata['pages'] = len(page_info)
            
            full_text = '\n\n'.join(text_content)
            return full_text, metadata, page_info
            
        except ImportError:
            logger.error("BeautifulSoup4 not installed. Run: pip install beautifulsoup4")
            raise
        except Exception as e:
            logger.error(f"Error reading EPUB file with pages: {e}")
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
    
    def _read_pdf_with_pages(self, file_path: Path) -> Tuple[str, Dict, List[Dict]]:
        """Read PDF format with page-by-page content tracking"""
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
            
            # Extract text content with page tracking
            text_content = []
            page_info = []
            current_pos = 0
            
            for page_num in range(doc.page_count):
                page = doc[page_num]
                text = page.get_text()
                
                if text.strip():
                    page_info.append({
                        'page_num': page_num + 1,  # 1-based page numbers
                        'content': text,
                        'start_pos': current_pos,
                        'end_pos': current_pos + len(text) + 2,  # +2 for page break
                        'page_type': 'actual'  # This is a real page number
                    })
                    text_content.append(text)
                    current_pos += len(text) + 2  # Account for page separator
                else:
                    # Empty page, but still track it
                    page_info.append({
                        'page_num': page_num + 1,
                        'content': '',
                        'start_pos': current_pos,
                        'end_pos': current_pos,
                        'page_type': 'actual'
                    })
            
            doc.close()
            full_text = '\n\n'.join(text_content)
            return full_text, metadata, page_info
            
        except Exception as e:
            logger.error(f"Error reading PDF file with pages: {e}")
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
    
    def _read_txt_with_pages(self, file_path: Path) -> Tuple[str, Dict, List[Dict]]:
        """Read plain text format with estimated page tracking"""
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
            
            # Estimate pages based on content length
            chars_per_page = 2200  # Typical book page
            page_info = []
            current_pos = 0
            estimated_page = 1
            
            while current_pos < len(content):
                end_pos = min(current_pos + chars_per_page, len(content))
                
                # Try to break at paragraph or sentence boundary
                if end_pos < len(content):
                    # Look for good break points
                    break_chars = ['\n\n', '\n', '.', ' ']
                    for break_char in break_chars:
                        last_break = content.rfind(break_char, current_pos, end_pos)
                        if last_break > current_pos + chars_per_page * 0.8:
                            end_pos = last_break + len(break_char)
                            break
                
                page_content = content[current_pos:end_pos]
                page_info.append({
                    'page_num': estimated_page,
                    'content': page_content,
                    'start_pos': current_pos,
                    'end_pos': end_pos,
                    'page_type': 'estimated'
                })
                
                current_pos = end_pos
                estimated_page += 1
            
            metadata['pages'] = len(page_info)
            return content, metadata, page_info
            
        except Exception as e:
            logger.error(f"Error reading TXT file with pages: {e}")
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
    
    def _read_docx_with_pages(self, file_path: Path) -> Tuple[str, Dict, List[Dict]]:
        """Read DOCX format with estimated page tracking"""
        # For now, use the regular DOCX reader and estimate pages
        text, metadata = self._read_docx(file_path)
        
        # Estimate pages (similar to TXT)
        chars_per_page = 2200
        page_info = []
        current_pos = 0
        estimated_page = 1
        
        while current_pos < len(text):
            end_pos = min(current_pos + chars_per_page, len(text))
            
            # Try to break at paragraph boundary
            if end_pos < len(text):
                last_para = text.rfind('\n\n', current_pos, end_pos)
                if last_para > current_pos + chars_per_page * 0.8:
                    end_pos = last_para + 2
            
            page_content = text[current_pos:end_pos]
            page_info.append({
                'page_num': estimated_page,
                'content': page_content,
                'start_pos': current_pos,
                'end_pos': end_pos,
                'page_type': 'estimated'
            })
            
            current_pos = end_pos
            estimated_page += 1
        
        metadata['pages'] = len(page_info)
        return text, metadata, page_info
    
    def _read_mobi_with_pages(self, file_path: Path) -> Tuple[str, Dict, List[Dict]]:
        """Read MOBI format with estimated page tracking"""
        # For now, use the regular MOBI reader and estimate pages
        text, metadata = self._read_mobi(file_path)
        
        # Estimate pages (similar to TXT)
        chars_per_page = 2200
        page_info = []
        current_pos = 0
        estimated_page = 1
        
        while current_pos < len(text):
            end_pos = min(current_pos + chars_per_page, len(text))
            
            # Try to break at paragraph boundary
            if end_pos < len(text):
                last_para = text.rfind('\n\n', current_pos, end_pos)
                if last_para > current_pos + chars_per_page * 0.8:
                    end_pos = last_para + 2
            
            page_content = text[current_pos:end_pos]
            page_info.append({
                'page_num': estimated_page,
                'content': page_content,
                'start_pos': current_pos,
                'end_pos': end_pos,
                'page_type': 'estimated'
            })
            
            current_pos = end_pos
            estimated_page += 1
        
        metadata['pages'] = len(page_info)
        return text, metadata, page_info

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
            
            # Check for OPF metadata to enhance the information
            opf_metadata = self._find_and_parse_opf(file_path)
            if opf_metadata:
                # Merge OPF metadata, giving it priority for richer data
                for key, value in opf_metadata.items():
                    if value and value.strip():
                        basic_info[key] = value
                logger.info(f"Enhanced book info with OPF metadata: {list(opf_metadata.keys())}")
                
        except Exception as e:
            logger.warning(f"Could not extract metadata from {file_path}: {e}")
        
        return basic_info


# Example usage and testing
if __name__ == "__main__":
    reader = EbookReader()
    
    # Example: Find all ebooks in a directory
    # ebooks = EbookReader.find_ebooks("/path/to/your/ebooks")
    # print(f"Found {len(ebooks)} ebooks")
    
    # Example: Read a specific ebook with automatic OPF metadata enhancement
    # text, metadata = reader.read_ebook("path/to/your/book.epub")
    # print(f"Title: {metadata['title']}")
    # print(f"Author: {metadata['author']}")
    # print(f"Description: {metadata.get('description', 'N/A')[:100]}...")
    # print(f"Tags: {metadata.get('tags', [])}")
    # print(f"Series: {metadata.get('series', 'N/A')}")
    # print(f"Content length: {len(text)} characters")
    
    # Example: Get enhanced book info without reading full content
    # info = reader.get_book_info("path/to/your/book.epub")
    # print(f"Enhanced metadata fields: {list(info.keys())}")
    
    print("EbookReader supports:")
    print("- Formats: EPUB, PDF, MOBI, AZW, AZW3, DOCX, TXT")
    print("- Automatic OPF metadata.opf file detection and parsing")
    print("- Rich metadata: titles, authors, descriptions, ISBN, tags, series, ratings")
    print("- Calibre library compatibility")