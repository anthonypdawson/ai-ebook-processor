#!/usr/bin/env python3
"""
Module execution entry point for AI Ebook Processor CLI

Allows running the CLI via: python -m ai_ebook_processor.cli.commands
"""

from .commands import cli

if __name__ == "__main__":
    cli()