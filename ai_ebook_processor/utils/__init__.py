"""
Utility functions and helpers

Contains configuration management, logging, and other utilities.
"""

from .config import Config
from .fast_mode import add_book_fast_mode

__all__ = [
    "Config",
    "add_book_fast_mode"
]