# TODO: Refactor RAG System File

## Class Decomposition
- Identify logical groupings of methods (e.g., chunk management, book registry, embedding, search, batch operations).
- Create new classes:
	- `ChunkManager`: Handles chunk creation, retrieval, pagination, and page summaries.
	- `BookRegistry`: Manages book registration, deduplication, and metadata.
	- `EmbeddingManager`: Handles model loading, encoding, and batch embedding.
	- `SearchManager`: Manages search queries, related term generation, and citation formatting.
	- `BatchProcessor`: Handles batch and parallel processing of ebooks.
- Move related methods and attributes to their respective classes.

## Interface Design
- Define clear interfaces for each class (e.g., `add_book`, `get_chunks`, `search`, `embed`).
- Use dependency injection for shared resources (e.g., ChromaDB client, config, logger).

## File Organization
- Split the large file into multiple modules (e.g., `chunk_manager.py`, `book_registry.py`, `embedding_manager.py`, `search_manager.py`, `batch_processor.py`).
- Create an `__init__.py` to expose a clean API.

## EnhancedEbookProcessor Refactor
- Refactor `EnhancedEbookProcessor` to use the new modular classes.
- Remove direct method calls to the monolithic `EbookRAGSystem`.

## Testing
- Add or update unit tests for each new class.
- Ensure coverage for edge cases (e.g., empty books, failed embeddings, search errors).

## Documentation
- Update docstrings for all new classes and methods.
- Add usage examples for the new modular API.
- Update README and developer docs to reflect the new structure.

## Legacy Code Cleanup
- Remove or refactor any legacy, redundant, or unused code.
- Deprecate old methods with clear warnings if needed.

## Performance & Maintainability
- Profile critical paths (e.g., batch insert, search) and optimize as needed.
- Ensure each class is single-responsibility and easy to maintain.

## Migration Plan
- Plan for a staged migration: first split classes, then update usage, then remove old code.
- Communicate changes to collaborators and update any integration points.
