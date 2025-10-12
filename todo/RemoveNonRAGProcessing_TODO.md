# TODO: Remove Non-RAG Processing

- Remove all fallback code paths that use non-RAG processing (e.g., process_single_ebook)
- Ensure EnhancedEbookProcessor and related classes only support RAG-based processing
- Update CLI, API, and documentation to reflect RAG-only support
- Refactor or delete any legacy code, methods, or commands related to non-RAG processing
- Test to confirm all ebook processing uses RAG chunking, embedding, and metadata
- Update user-facing messages and docstrings to clarify RAG-only functionality
