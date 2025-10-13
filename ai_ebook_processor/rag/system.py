This file has been removed as it is obsolete and all logic is now handled by modular classes.

                    
                    if show_progress:
                        logger.debug(f"Batch {batch_idx + 1}/{total_batches} completed ({len(batch_docs)} docs)")
                        
                except Exception as e:
                    logger.error(f"Error inserting batch {batch_idx + 1}/{total_batches}: {e}")
                    return False
            
            if show_progress:
                logger.info(f"Successfully inserted all {total_docs} documents")
            
            return True
            
        except Exception as e:
            logger.error(f"Error in batch insert: {e}")
            return False

    def book_exists(self, book_id: str) -> bool:
        """
        Check if book already exists in the database
        
        Args:

                file_hash = self.get_file_hash(file_path)
                book_id = f"{base_book_id}_{file_hash[:8]}"  # Use first 8 chars of hash
            else:
                book_id = base_book_id
            
            # Check if book already exists
            if self.book_exists(book_id):
                if not overwrite:
                    msg = f"Book {book_id} already exists, skipped"
                    logger.warning(msg)
                    return self._build_add_result(False, 'add_processed', book_id, metadata.get('title'), metadata.get('author'), 0, msg, skipped=True, metadata=metadata)
                else:
                    # Remove existing book
                    self.remove_book(book_id)
                    logger.info(f"Overwriting existing book {book_id}")
            
            # Prefer raw canonical text (list of original chunk texts) over LLM combined summaries
            raw_chunks = result.get('raw_chunks') or []
            if raw_chunks:
                chunks = raw_chunks
            else:
                content = result.get('raw_text') or result.get('combined_result', '')
                if not content:
                    msg = f"No content found for {book_id}"
                    logger.warning(msg)
                    return self._build_add_result(False, 'add_processed', book_id, metadata.get('title'), metadata.get('author'), 0, msg, error=msg, metadata=metadata)
                chunks = self._chunk_content(content, chunk_size=self.config.get('processing.chunk_size', 4000))
            
            if not chunks:
                msg = f"No chunks created for {book_id}"
                logger.warning(msg)
                return self._build_add_result(False, 'add_processed', book_id, metadata.get('title'), metadata.get('author'), 0, msg, error=msg, metadata=metadata)
            
            # Prepare batch data for efficient insertion
            all_documents = []
            all_metadatas = []
            all_ids = []
            for i, chunk in enumerate(chunks):
                doc_id = f"{book_id}_chunk_{i}"
                chunk_metadata = {
                    'book_title': metadata.get('title', 'Unknown'),
                    'author': metadata.get('author', 'Unknown'),
                    'format': metadata.get('format', 'Unknown'),
                    'chunk_id': i,
                    'book_id': book_id
                }
                # Add file hash to metadata if available
                if file_hash:
                    chunk_metadata['file_hash'] = file_hash
                if file_path:
                    chunk_metadata['file_path'] = str(file_path)
                all_documents.append(chunk)
                all_metadatas.append(chunk_metadata)
                all_ids.append(doc_id)

            # Calculate optimal batch size based on available memory
            sample_doc = all_documents[0] if all_documents else None
            sample_meta = all_metadatas[0] if all_metadatas else None
            batch_size = self._calculate_optimal_batch_size(
                sample_doc=sample_doc,
                sample_metadata=sample_meta,
                total_items=len(all_documents)
            )
            total_batches = (len(all_documents) + batch_size - 1) // batch_size

            logger.info(f"Inserting {len(chunks)} chunks in {total_batches} batches of {batch_size} (auto-calculated)")

            # Import click for progress display
            import click
            click.echo(f"Storing {len(chunks)} chunks in database...")

            click.echo("Encoding chunks to embeddings...")
            try:
                embeddings = self.embed_chunks(all_documents, show_progress_bar=True)
            except Exception as e:
                click.echo(f"Error encoding embeddings: {e}")
                return self._build_add_result(False, 'add_processed', book_id, metadata.get('title'), metadata.get('author'), 0, "Embedding error", error=str(e), metadata=metadata)
            
            # Calculate optimal batch size based on available memory
            sample_doc = all_documents[0] if all_documents else None
            sample_meta = all_metadatas[0] if all_metadatas else None
            batch_size = self._calculate_optimal_batch_size(
                sample_doc=sample_doc,
                sample_metadata=sample_meta,
                total_items=len(all_documents)
            )
            total_batches = (len(all_documents) + batch_size - 1) // batch_size
            
            logger.info(f"Inserting {len(chunks)} chunks in {total_batches} batches of {batch_size} (auto-calculated)")
            
            # Import click for progress display
            import click
            click.echo(f"Storing {len(chunks)} chunks in database...")
            
            for batch_idx in range(total_batches):
                start_idx = batch_idx * batch_size
                end_idx = min(start_idx + batch_size, len(all_documents))
                
                batch_docs = all_documents[start_idx:end_idx]
                batch_metas = all_metadatas[start_idx:end_idx]
                batch_ids = all_ids[start_idx:end_idx]
                
                try:
                    self.collection.add(
                        documents=batch_docs,
                        metadatas=batch_metas,
                        ids=batch_ids
                    )
                    # Show progress like add_ebook_with_pages does
                    progress = min(end_idx, len(chunks))
                    click.echo(f"  Stored batch {batch_idx + 1}/{total_batches} - {progress}/{len(chunks)} chunks")
                except Exception as e:
                    logger.error(f"Error inserting batch {batch_idx + 1}: {e}")
                    click.echo(f"  ❌ Error in batch {batch_idx + 1}/{total_batches}: {e}")
                    # Continue with next batch rather than failing completely
                    continue
            
            # Register the book in the registry for fast listing with chunk tracking
            book_registry_metadata = {
                'book_id': book_id,
                'title': metadata.get('title', 'Unknown'),
                'author': metadata.get('author', 'Unknown'),
                'format': metadata.get('format', 'Unknown'),
                'file_hash': file_hash,
                'file_path': str(file_path) if file_path else '',
                'chunks': len(chunks)
            }
            self.register_book(book_id, book_registry_metadata, all_ids)

            elapsed_time = time.time() - start_time
            success_msg = f"Added {len(chunks)} chunks for '{metadata.get('title')}' to RAG database in {elapsed_time:.2f}s"
            logger.info(f"✅ {success_msg}")
            click.echo(success_msg)  # Show user-visible success message
            return self._build_add_result(True, 'add_processed', book_id, metadata.get('title'), metadata.get('author'), len(chunks), success_msg, metadata=metadata)
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            error_msg = f"Error adding ebook to RAG database after {elapsed_time:.2f}s: {e}"
            logger.error(f"❌ {error_msg}")
            return self._build_add_result(False, 'add_processed', message=error_msg, error=str(e))
    
    def add_multiple_ebooks(self, results: List[Dict]) -> None:
        """Add multiple processed ebooks to the database.

        Returns list of standardized result dicts for each add attempt.
        """
        added_results = []
        for result in results:
            try:
                added_results.append(self.add_processed_ebook(result))
            except Exception as e:
                added_results.append(self._build_add_result(False, 'add_processed', message=f"Unhandled error: {e}", error=str(e)))
        return added_results
    
    def add_multiple_ebooks_batch(self, results: List[Dict], batch_size: int = None) -> Dict[str, Any]:
        """
        Add multiple processed ebooks to the database with batch optimization.
        
        Args:
            results: List of processed ebook results
            batch_size: Number of chunks to batch together (None for auto-calculation)
            
        Returns:
            Dictionary with batch processing statistics
        """
        stats = {
            'total_books': len(results),
            'successful_books': 0,
            'failed_books': 0,
            'total_chunks': 0,
            'processing_time': 0,
            'errors': []
        }
        
        import time
        start_time = time.time()
        
        try:
            # Collect all chunks from all books for batch processing
            all_texts = []
            all_metadatas = []
            all_ids = []
            book_chunk_counts = {}
            books_to_register = {}  # Track books for registry registration
            book_chunk_ids = {}  # Track chunk IDs for each book
            
            for result in results:
                raw_chunks = result.get('raw_chunks')
                metadata = result.get('metadata', {})
                base_book_id = f"{metadata.get('title', 'unknown')}_{metadata.get('author', 'unknown')}"
                base_book_id = base_book_id.replace(' ', '_').replace('/', '_').replace('\\', '_')
                file_hash = ""
                if result.get('file_path') and os.path.exists(result.get('file_path')):
                    file_hash = self.get_file_hash(result['file_path'])
                    book_id = f"{base_book_id}_{file_hash[:8]}"
                else:
                    book_id = base_book_id
                    
                if not raw_chunks:
                    stats['failed_books'] += 1
                    stats['errors'].append(f"No raw chunks in result for {metadata.get('title', 'unknown')}")
                    continue
                    
                chunk_count = len(raw_chunks)
                stats['successful_books'] += 1
                stats['total_chunks'] += chunk_count
                book_chunk_counts[book_id] = chunk_count
                
                # Prepare book for registry registration
                books_to_register[book_id] = {
                    'book_id': book_id,
                    'title': metadata.get('title', 'Unknown'),
                    'author': metadata.get('author', 'Unknown'),
                    'format': metadata.get('format', 'Unknown'),
                    'file_hash': file_hash,
                    'file_path': str(result.get('file_path', '')),
                    'chunks': chunk_count
                }
                
                # Track chunk IDs for this book
                book_chunk_ids[book_id] = []
                
                for i, chunk in enumerate(raw_chunks):
                    doc_id = f"{book_id}_chunk_{i}"
                    chunk_metadata = {
                        'book_title': metadata.get('title', 'Unknown'),
                        'author': metadata.get('author', 'Unknown'),
                        'format': metadata.get('format', 'Unknown'),
                        'chunk_id': i,
                        'book_id': book_id
                    }
                    if file_hash:
                        chunk_metadata['file_hash'] = file_hash
                    if result.get('file_path'):
                        chunk_metadata['file_path'] = str(result['file_path'])
                    all_texts.append(chunk)
                    all_metadatas.append(chunk_metadata)
                    all_ids.append(doc_id)
                    
                    # Track this chunk ID for the book
                    book_chunk_ids[book_id].append(doc_id)
            
            # Calculate optimal batch size if not provided
            if batch_size is None:
                sample_doc = all_texts[0] if all_texts else None
                sample_meta = all_metadatas[0] if all_metadatas else None
                batch_size = self._calculate_optimal_batch_size(
                    sample_doc=sample_doc,
                    sample_metadata=sample_meta,
                    total_items=len(all_texts)
                )
                logger.info(f"Parallel processing: Auto-calculated batch size {batch_size} for {len(all_texts)} total chunks")
            
            # Batch add chunks to database
            total_batches = (len(all_texts) + batch_size - 1) // batch_size
            logger.info(f"Processing {len(all_texts)} chunks in {total_batches} batches of {batch_size}")
            
            # Import click for progress display
            import click
            click.echo(f"Batch processing {stats['successful_books']} books with {len(all_texts)} total chunks...")
            
            for i in range(0, len(all_texts), batch_size):
                batch_num = (i // batch_size) + 1
                end_idx = min(i + batch_size, len(all_texts))
                batch_texts = all_texts[i:end_idx]
                batch_metadatas = all_metadatas[i:end_idx]
                batch_ids = all_ids[i:end_idx]
                
                self.collection.add(
                    documents=batch_texts,
                    metadatas=batch_metadatas,
                    ids=batch_ids
                )
                
                # Show progress
                click.echo(f"  Processed batch {batch_num}/{total_batches} - {end_idx}/{len(all_texts)} chunks")
                
            # Register all books in the registry after successful batch processing
            for book_id, book_metadata in books_to_register.items():
                chunk_ids = book_chunk_ids.get(book_id, [])
                self.register_book(book_id, book_metadata, chunk_ids)
                
            stats['processing_time'] = time.time() - start_time
            logger.info(f"✅ Successfully added {stats['successful_books']} books with {stats['total_chunks']} chunks in {stats['processing_time']:.2f}s")
            
        except Exception as e:
            stats['processing_time'] = time.time() - start_time
            error_msg = f"Error in batch processing after {stats['processing_time']:.2f}s: {e}"
            stats['errors'].append(error_msg)
            logger.error(f"❌ {error_msg}")
        
        return stats
    
    def add_ebooks_parallel_batch(self, file_paths: List[str], max_workers: int = 3) -> Dict[str, Any]:
        """
        Process multiple ebooks in parallel and add them to the database in batches.
        
        Args:
            file_paths: List of ebook file paths
            max_workers: Number of parallel processing workers
            
        Returns:
            Dictionary with processing statistics
        """
        from concurrent.futures import ThreadPoolExecutor
        import time
        
        start_time = time.time()
        stats = {
            'total_files': len(file_paths),
            'successful_files': 0,
            'failed_files': 0,
            'total_chunks': 0,
            'processing_time': 0,
            'errors': []
        }
        
        def process_single_file(file_path: str) -> Dict[str, Any]:
            """Process a single ebook file and return standardized result wrapper."""
            try:
                add_result = self.add_ebook_with_pages(file_path, overwrite=False)
                return {
                    'success': add_result.get('success', False),
                    'file_path': file_path,
                    'add_result': add_result,
                    'skipped': add_result.get('skipped', False),
                    'error': add_result.get('error')
                }
            except Exception as e:
                return {'success': False, 'file_path': file_path, 'error': str(e), 'add_result': None}
        
        # Process files in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(process_single_file, file_paths))
        
        # Collect statistics
        for r in results:
            if r.get('success'):
                stats['successful_files'] += 1
            else:
                if r.get('skipped'):
                    # treat skipped separately
                    pass
                else:
                    stats['failed_files'] += 1
                    stats['errors'].append(f"Failed to process {r.get('file_path')}: {r.get('error')}")
        
        stats['processing_time'] = time.time() - start_time
        logger.info(f"Parallel batch processing complete: {stats['successful_files']}/{stats['total_files']} files processed in {stats['processing_time']:.2f}s")
        
        return stats
    
    @timing_decorator("Search Books")
    def search_books(self, query: str, n_results: int = None) -> Dict:
        """
        Search for relevant content in your ebook collection
        
        Args:
            query: Search query
            n_results: Number of results to return
            
        Returns:
            Dictionary with search results including page citations
        """
        try:
            if n_results is None:
                n_results = self.config.get('rag.context_chunk_count', 5)
            with Timer(f"ChromaDB Query (n={n_results})"):
                results = self.collection.query(
                    query_texts=[query],
                    n_results=n_results
                )
            
            with Timer("Processing Search Results"):
                search_results = {
                    'query': query,
                    'results': []
                }
                
                if results['documents'] and results['documents'][0]:
                    for doc, meta, dist in zip(
                        results['documents'][0],
                        results['metadatas'][0], 
                        results['distances'][0]
                    ):
                        # Create citation information
                        citation_info = self._create_citation(meta)
                        
                        result_item = {
                            'content': doc,
                            'metadata': meta,
                            'distance': dist,
                            'similarity_score': 1 - dist,  # Convert distance to similarity
                            'citation': citation_info
                        }
                        search_results['results'].append(result_item)
            
            return search_results
            
        except Exception as e:
            logger.error(f"Error searching books: {e}")
            return {'query': query, 'results': []}
    
    def _create_citation(self, metadata: Dict) -> str:
        """
        Create a citation string from chunk metadata
        
        Args:
            metadata: Chunk metadata containing page and book information
            
        Returns:
            Formatted citation string
        """
        book_title = metadata.get('book_title', 'Unknown Title')
        author = metadata.get('author', 'Unknown Author')
        page_start = metadata.get('page_start')
        page_end = metadata.get('page_end')
        page_type = metadata.get('page_type', 'estimated')
        
        # Format basic citation
        citation = f"{author}. \"{book_title}\""
        
        # Add page information if available
        if page_start and page_end:
            if page_start == page_end:
                page_indicator = "(est. p." if page_type == 'estimated' else "(p."
                citation += f" {page_indicator} {page_start})"
            else:
                page_indicator = "(est. pp." if page_type == 'estimated' else "(pp."
                citation += f" {page_indicator} {page_start}-{page_end})"
        
        return citation
    
    @timing_decorator("Ask Question (Total)")
    def ask_question(self, question: str, ollama_processor, context_chunks: int = None, verbose: bool = False, book_filter: str = None) -> str:
        """
        Ask a question about your book collection using RAG
        
        Args:
            question: Question to ask
            ollama_processor: OllamaProcessor instance
            context_chunks: Number of relevant chunks to include
            verbose: If True, print debug info about retrieved context and prompt
            book_filter: If provided, limit search to chunks from this specific book_id
            
        Returns:
            AI response based on your books
        """
        if context_chunks is None:
            context_chunks = self.config.get('rag.context_chunk_count', 5)
        # Try multiple search strategies to get better context
        if book_filter:
            # Search only within the specified book
            try:
                book_results = self.collection.query(
                    query_texts=[question],
                    n_results=context_chunks,
                    where={"book_id": book_filter}
                )
                search_results = {
                    'query': question,
                    'results': []
                }
                
                if book_results['documents'] and book_results['documents'][0]:
                    for doc, meta, dist in zip(
                        book_results['documents'][0],
                        book_results['metadatas'][0], 
                        book_results['distances'][0]
                    ):
                        citation_info = self._create_citation(meta)
                        result_item = {
                            'content': doc,
                            'metadata': meta,
                            'distance': dist,
                            'similarity_score': 1 - dist,
                            'citation': citation_info
                        }
                        search_results['results'].append(result_item)
            except Exception as e:
                logger.error(f"Error searching focused book {book_filter}: {e}")
                # Fallback to regular search
                search_results = self.search_books(question, context_chunks)
        else:
            # Regular search across all books
            search_results = self.search_books(question, context_chunks)
        
        # If we don't have many results, try to expand the search with related terms
        if len(search_results.get('results', [])) < context_chunks:
            # Generate AI-powered related terms
            related_terms = self._generate_related_search_terms(question, ollama_processor)
            for term in related_terms:
                additional_results = self.search_books(term, max(1, context_chunks - len(search_results['results'])))
                if additional_results['results']:
                    # Merge results, avoiding duplicates using composite key (book_id, chunk_id)
                    existing_ids = {
                        (r.get('metadata', {}).get('book_id', ''), r.get('metadata', {}).get('chunk_id', '')) 
                        for r in search_results['results']
                    }
                    for result in additional_results['results']:
                        composite_key = (
                            result.get('metadata', {}).get('book_id', ''), 
                            result.get('metadata', {}).get('chunk_id', '')
                        )
                        if composite_key not in existing_ids:
                            search_results['results'].append(result)
                            existing_ids.add(composite_key)
                            if len(search_results['results']) >= context_chunks:
                                break
                if len(search_results['results']) >= context_chunks:
                    break
        
        if not search_results['results']:
            if verbose:
                print(f"\\n🔍 DEBUG: No relevant chunks found for query: '{question}'")
            return "I couldn't find relevant information in your book collection to answer that question."
        
        # Build context from search results
        context_parts = []
        book_metadata_summary = {}  # Collect unique book metadata
        
        for result in search_results['results']:
            book_title = result['metadata'].get('book_title', '').strip()
            author = result['metadata'].get('author', '').strip()
            content = result['content']
            book_id = result['metadata'].get('book_id', '')
            
            # Collect book metadata for summary
            if book_id and book_id not in book_metadata_summary:
                book_metadata_summary[book_id] = {
                    'title': book_title,
                    'author': author,
                    'format': result['metadata'].get('format', 'Unknown'),
                    'total_pages': result['metadata'].get('total_pages', 'Unknown'),
                    'file_hash': result['metadata'].get('file_hash', '')[:8] if result['metadata'].get('file_hash') else '',
                }
            
            # Create a better source attribution with page info
            if book_title and author:
                source = f"From '{book_title}' by {author}"
            elif book_title:
                source = f"From '{book_title}'"
            elif author:
                source = f"From a book by {author}"
            else:
                # Try to extract title/author from content or use file info
                format_info = result['metadata'].get('format', '')
                if format_info:
                    source = f"From your {format_info} book"
                else:
                    source = "From your book collection"
            
            # Add page information if available
            page_start = result['metadata'].get('page_start')
            page_end = result['metadata'].get('page_end')
            page_type = result['metadata'].get('page_type', 'estimated')
            
            if page_start and page_end:
                if page_start == page_end:
                    page_indicator = "est. p." if page_type == 'estimated' else "p."
                    source += f" ({page_indicator} {page_start})"
                else:
                    page_indicator = "est. pp." if page_type == 'estimated' else "pp."
                    source += f" ({page_indicator} {page_start}-{page_end})"
            
            context_parts.append(f"{source}:\\n{content}")
        
        if verbose:
            print(f"\\n🔍 DEBUG: Retrieved {len(search_results['results'])} context chunks:")
            for i, result in enumerate(search_results['results'], 1):
                print(f"\\n--- Chunk {i} (similarity: {result.get('similarity_score', 0):.3f}) ---")
                print(f"Source: {result['citation']}")
                print(f"Book ID: {result['metadata'].get('book_id', 'Unknown')}")
                print(f"Format: {result['metadata'].get('format', 'Unknown')}")
                print(f"Pages: {result['metadata'].get('page_start', '?')}-{result['metadata'].get('page_end', '?')} ({result['metadata'].get('page_type', 'estimated')})")
                print(f"Content: {result['content'][:200]}{'...' if len(result['content']) > 200 else ''}")
            
            if book_metadata_summary:
                print(f"\\n📚 DEBUG: Book metadata summary:")
                for book_id, meta in book_metadata_summary.items():
                    pages_info = f", {meta['total_pages']} pages" if meta['total_pages'] != 'Unknown' else ""
                    print(f"  - '{meta['title']}' by {meta['author']} ({meta['format']}{pages_info})")
        
        context = "\\n\\n---\\n\\n".join(context_parts)
        
        # Build book metadata summary for additional context
        metadata_context = ""
        if book_metadata_summary:
            metadata_context = "\\n\\nBOOK METADATA SUMMARY:\\n"
            for book_id, meta in book_metadata_summary.items():
                pages_info = f", {meta['total_pages']} pages" if meta['total_pages'] != 'Unknown' else ""
                metadata_context += f"- '{meta['title']}' by {meta['author']} ({meta['format']} format{pages_info})\\n"
        
        # Create prompt with context and metadata
        prompt = f"""Based on the following information from the user's book collection, please answer their question:

CONTEXT FROM BOOKS:
{context}

{metadata_context}
USER QUESTION: {question}

Please provide a helpful answer based on the information above. When relevant, reference specific books, authors, or page numbers. If the context doesn't fully answer the question, mention what information might be missing."""
        
        if verbose:
            print(f"\\n🤖 DEBUG: Full prompt being sent to AI model:")
            print(f"{'='*60}")
            print(prompt)
            print(f"{'='*60}\\n")
        
        try:
            # Suppress httpx INFO logging for cleaner output
            import logging as log_module
            httpx_logger = log_module.getLogger("httpx")
            original_level = httpx_logger.level
            httpx_logger.setLevel(log_module.WARNING)
            
            try:
                with Timer("AI Response Generation", verbose=verbose):
                    # Call ollama directly since we don't need the text formatting
                    response = ollama_processor.client.chat(
                        model=ollama_processor.model_name,
                        messages=[
                            {'role': 'system', 'content': 'You are a knowledgeable assistant helping someone understand their book collection.'},
                            {'role': 'user', 'content': prompt}
                        ],
                        options={'temperature': ollama_processor.temperature}
                    )
                return response['message']['content']
            finally:
                # Restore original logging level
                httpx_logger.setLevel(original_level)
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return f"Error generating response: {e}"
    
    def _generate_related_search_terms(self, question: str, ollama_processor) -> List[str]:
        """
        Use AI to generate contextually relevant search terms to improve retrieval
        
        Args:
            question: The original user question
            ollama_processor: OllamaProcessor instance for generating terms
            
        Returns:
            List of related search terms
        """
        try:
            prompt = f"""Given this question about books: "{question}"

Generate 3-5 related search terms or phrases that would help find relevant content in a book collection. 
Focus on:
- Synonyms and alternative phrasings
- Related concepts and themes  
- Key terms that might appear in book content
- Broader or more specific versions of the question

Return only the search terms, one per line, without explanations or numbering.

Examples:
For "What are the main themes?" you might suggest:
central ideas
key messages  
underlying concepts
moral lessons

For "Who are the protagonists?" you might suggest:
main characters
heroes
central figures
lead character"""

            response = ollama_processor.client.chat(
                model=ollama_processor.model_name,
                messages=[
                    {'role': 'system', 'content': 'You are a helpful assistant that generates search terms for book content retrieval.'},
                    {'role': 'user', 'content': prompt}
                ],
                options={'temperature': 0.3}  # Lower temperature for more focused results
            )
            
            # Extract terms from response
            terms_text = response['message']['content'].strip()
            terms = [term.strip() for term in terms_text.split('\n') if term.strip()]
            
            # Clean up terms and limit to 5
            clean_terms = []
            for term in terms[:5]:
                # Remove numbering, bullets, or other artifacts
                clean_term = term.replace('•', '').replace('-', '').strip()
                if clean_term and len(clean_term) > 2:
                    clean_terms.append(clean_term)
            
            logger.info(f"Generated {len(clean_terms)} related search terms for: {question}")
            return clean_terms
            
        except Exception as e:
            logger.error(f"Error generating related search terms: {e}")
            # Fallback to simple keyword extraction from the question
            return self._fallback_term_extraction(question)
    
    def _fallback_term_extraction(self, question: str) -> List[str]:
        """
        Fallback method for generating search terms when AI generation fails
        
        Args:
            question: The original question
            
        Returns:
            List of basic search terms extracted from the question
        """
        # Simple fallback: extract meaningful words from the question
        import re
        
        # Remove common question words and extract meaningful terms
        stop_words = {'what', 'who', 'when', 'where', 'why', 'how', 'is', 'are', 'the', 'a', 'an', 'and', 'or', 'but'}
        words = re.findall(r'\b\w+\b', question.lower())
        meaningful_words = [word for word in words if word not in stop_words and len(word) > 2]
        
        # Take up to 3 meaningful words
        return meaningful_words[:3]
    
    def get_collection_stats(self) -> Dict:
        """Get statistics about the RAG database"""
        try:
            # Use a more efficient count if available
            count = self.collection.count()
            return {
                'total_chunks': count,
                'database_path': self.db_path
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {'total_chunks': 0, 'database_path': self.db_path}
    
    def _chunk_content(self, content: str, chunk_size: int = 1000) -> List[str]:
        """Split content into chunks for vector storage"""
        words = content.split()
        chunks = []
        current_chunk = []
        current_length = 0
        
        for word in words:
            if current_length + len(word) > chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = [word]
                current_length = len(word)
            else:
                current_chunk.append(word)
                current_length += len(word) + 1  # +1 for space
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks

