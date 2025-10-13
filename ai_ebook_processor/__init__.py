"""
AI Ebook Processor

A comprehensive system for processing ebooks with AI models and RAG capabilities.
"""

__version__ = "0.1.0"
__author__ = "AI Ebook Processor Team"

# Main package exports
from .core.processor import EbookProcessorApp
__all__ = [
    "EbookProcessorApp",
    # "EbookRAGSystem", 
    # "EnhancedEbookProcessor"
]