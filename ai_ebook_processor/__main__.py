#!/usr/bin/env python3
"""
Module execution entry point for AI Ebook Processor

Allows running the main CLI via: python -m ai_ebook_processor
"""

from .cli.commands import cli

if __name__ == "__main__":
    cli()