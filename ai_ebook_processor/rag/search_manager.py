class SearchManager:
    """Manages search queries, related term generation, and citation formatting."""

    def __init__(self, collection, config):
        self.collection = collection
        self.config = config

    def search(self, query: str, n_results: int = None) -> dict:
        if n_results is None:
            n_results = self.config.get('rag.context_chunk_count', 5)
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
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
                citation_info = self.format_citation(meta)
                result_item = {
                    'content': doc,
                    'metadata': meta,
                    'distance': dist,
                    'similarity_score': 1 - dist,
                    'citation': citation_info
                }
                search_results['results'].append(result_item)
        return search_results

    def format_citation(self, metadata: dict) -> str:
        book_title = metadata.get('book_title', 'Unknown Title')
        author = metadata.get('author', 'Unknown Author')
        page_start = metadata.get('page_start')
        page_end = metadata.get('page_end')
        page_type = metadata.get('page_type', 'estimated')
        citation = f"{author}. \"{book_title}\""
        if page_start and page_end:
            if page_start == page_end:
                page_indicator = "(est. p." if page_type == 'estimated' else "(p."
                citation += f" {page_indicator} {page_start})"
            else:
                page_indicator = "(est. pp." if page_type == 'estimated' else "(pp."
                citation += f" {page_indicator} {page_start}-{page_end})"
        return citation

    def generate_related_terms(self, question: str, ollama_processor) -> list:
        prompt = f"Given this question about books: \"{question}\"\nGenerate 3-5 related search terms or phrases that would help find relevant content in a book collection. Return only the search terms, one per line, without explanations or numbering."
        response = ollama_processor.client.chat(
            model=ollama_processor.model_name,
            messages=[
                {'role': 'system', 'content': 'You are a helpful assistant that generates search terms for book content retrieval.'},
                {'role': 'user', 'content': prompt}
            ],
            options={'temperature': 0.3}
        )
        terms_text = response['message']['content'].strip()
        terms = [term.strip() for term in terms_text.split('\n') if term.strip()]
        clean_terms = []
        for term in terms[:5]:
            clean_term = term.replace('•', '').replace('-', '').strip()
            if clean_term and len(clean_term) > 2:
                clean_terms.append(clean_term)
        return clean_terms
