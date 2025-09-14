"""
LLM model integrations

Contains interfaces for various language models (Ollama, etc.).
"""

from .ollama import OllamaProcessor

__all__ = ["OllamaProcessor"]