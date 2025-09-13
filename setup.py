#!/usr/bin/env python3
"""
Setup script for AI Ebook Processor
"""

from setuptools import setup, find_packages
import os

# Read the README file
def read_readme():
    with open("README.md", "r", encoding="utf-8") as fh:
        return fh.read()

# Read requirements
def read_requirements():
    with open("requirements.txt", "r", encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="ai-ebook-processor",
    version="1.0.0",
    author="Anthony Dawson",
    author_email="anthony@example.com",
    description="AI-powered ebook processor with RAG capabilities",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/anthonypdawson/ai-ebook-processor",
    py_modules=[
        "cli",
        "main", 
        "ebook_reader",
        "text_pipeline",
        "ollama_processor",
        "rag_system",
        "fast_mode",
        "custom_model_creator"
    ],
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest",
            "pytest-cov", 
            "black",
            "isort",
            "flake8",
        ]
    },
    entry_points={
        "console_scripts": [
            "ebook-processor=cli:cli",
            "ebook-rag=cli:rag",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Text Processing",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.8",
    keywords="ebook ai ollama rag nlp text-processing",
)