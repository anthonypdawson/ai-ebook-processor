# TODO: Refactor EbookRAGSystem

## Areas for Improvement

1. Encoder Property (Model Selection) [COMPLETED]
   - The encoder property now loads the model from config (rag.embedding_model) and includes error handling for model loading failures.

2. Chunking and Page Citations
   - Ensure all context chunks passed to LLMs include page numbers in metadata.
   - Use _create_citation for every chunk in prompt construction.

3. Configurable Chunk Count
   - Read context chunk count from config (rag.context_chunk_count) everywhere relevant.

4. Error Handling and Logging
   - Improve exception logging, including stack traces for easier debugging.

5. Type Annotations
   - Add or improve type annotations for method arguments and return values.

6. Code Duplication
   - Refactor repeated logic for batch insertion and chunk handling into helper methods.

7. Docstrings and Comments
   - Add more detail to docstrings, especially for edge cases and expected input/output.

8. Imports
   - Move imports to the top of the file unless circular dependencies require otherwise.

9. Performance
   - Optimize chunk retrieval and sorting for large collections (consider database-side sorting/filtering).

10. Prompt Construction
    - Improve LLM prompt to explicitly instruct citation of page numbers and sources.
