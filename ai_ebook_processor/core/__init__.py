"""
Core processing logic for AI Ebook Processor

Contains the main processing pipeline and orchestration logic.
"""

from .processor import EbookProcessorApp
from .pipeline import TextChunker, ProcessingPipeline, ProcessingConfig

__all__ = [
    "EbookProcessorApp",
    "TextChunker",
    "ProcessingPipeline", 
    "ProcessingConfig"
]