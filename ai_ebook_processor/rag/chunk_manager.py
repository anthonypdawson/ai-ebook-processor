class ChunkManager:
    """Handles chunk creation, retrieval, pagination, and page summaries for documents."""

    def __init__(self, collection):
        self.collection = collection

    def get_chunks_efficient(self, document_id: str, limit: int = None, include_page_info: bool = True) -> dict:
        """
        Efficiently retrieve chunks for a specific document using registry offset information.
        Args:
            document_id: Document identifier
            limit: Maximum number of chunks to return
            include_page_info: Whether to include page location metadata
        Returns:
            Dictionary with chunk data, metadata, and page information
        """
        try:
            results = self.collection.get(
                where={"book_id": document_id},
                include=["documents", "metadatas"],
                limit=limit
            )
            if results['metadatas']:
                combined = list(zip(results['documents'], results['metadatas'], results['ids']))
                combined.sort(key=lambda x: x[1].get('chunk_id', 0))
                sorted_docs, sorted_metas, sorted_ids = zip(*combined)
                response = {
                    'document_id': document_id,
                    'chunk_count': len(sorted_docs),
                    'chunks': list(sorted_docs),
                    'metadatas': list(sorted_metas),
                    'ids': list(sorted_ids)
                }
                if include_page_info and sorted_metas:
                    page_info = {
                        'has_page_data': any('page_start' in meta for meta in sorted_metas if meta),
                        'page_range': None,
                        'page_types': set()
                    }
                    page_starts = []
                    page_ends = []
                    for meta in sorted_metas:
                        if meta:
                            if 'page_start' in meta:
                                page_starts.append(meta['page_start'])
                            if 'page_end' in meta:
                                page_ends.append(meta['page_end'])
                            if 'page_type' in meta:
                                page_info['page_types'].add(meta['page_type'])
                    if page_starts and page_ends:
                        page_info['page_range'] = f"Pages {min(page_starts)}-{max(page_ends)}"
                    page_info['page_types'] = list(page_info['page_types'])
                    response['page_info'] = page_info
                return response
            return {
                'document_id': document_id,
                'chunk_count': 0,
                'chunks': [],
                'metadatas': [],
                'ids': []
            }
        except Exception:
            return {'document_id': document_id, 'chunk_count': 0, 'chunks': [], 'metadatas': [], 'ids': []}

    def get_chunks_by_page(self, document_id: str, start_page: int = None, end_page: int = None, page_type: str = None) -> dict:
        """
        Get chunks from a document by page range using stored page metadata.
        Args:
            document_id: Document identifier
            start_page: Starting page number (inclusive)
            end_page: Ending page number (inclusive)
            page_type: Filter by page type ('actual' or 'estimated')
        Returns:
            Dictionary with chunks, their page info, and metadata
        """
        try:
            results = self.collection.get(
                where={"book_id": document_id},
                include=["documents", "metadatas"]
            )
            filtered_results = {'documents': [], 'metadatas': [], 'ids': []}
            if results['metadatas']:
                for doc, meta, doc_id in zip(results['documents'], results['metadatas'], results['ids']):
                    if meta:
                        page_start = meta.get('page_start')
                        page_end = meta.get('page_end')
                        meta_page_type = meta.get('page_type')
                        include_chunk = True
                        if start_page is not None and page_start is not None:
                            if page_start < start_page:
                                include_chunk = False
                        if end_page is not None and page_end is not None:
                            if page_end > end_page:
                                include_chunk = False
                        if page_type and meta_page_type != page_type:
                            include_chunk = False
                        if include_chunk:
                            filtered_results['documents'].append(doc)
                            filtered_results['metadatas'].append(meta)
                            filtered_results['ids'].append(doc_id)
            if filtered_results['metadatas']:
                combined = list(zip(filtered_results['documents'], filtered_results['metadatas'], filtered_results['ids']))
                combined.sort(key=lambda x: x[1].get('page_start', 0))
                sorted_docs, sorted_metas, sorted_ids = zip(*combined)
                return {
                    'document_id': document_id,
                    'chunk_count': len(sorted_docs),
                    'chunks': list(sorted_docs),
                    'metadatas': list(sorted_metas),
                    'ids': list(sorted_ids),
                    'page_range': f"Pages {start_page or 'start'}-{end_page or 'end'}"
                }
            return {'document_id': document_id, 'chunk_count': 0, 'chunks': [], 'metadatas': [], 'ids': []}
        except Exception:
            return {'document_id': document_id, 'chunk_count': 0, 'chunks': [], 'metadatas': [], 'ids': []}

    def get_chunks_paginated(self, document_id: str, page: int = 1, page_size: int = 100) -> dict:
        """
        Get chunks from a document using pagination (chunk-based, not page-based).
        Args:
            document_id: Document identifier
            page: Page number (1-based)
            page_size: Number of chunks per page
        Returns:
            Dictionary with paginated chunks and pagination info
        """
        try:
            all_chunks = self.collection.get(
                where={"book_id": document_id},
                include=["documents", "metadatas"]
            )
            if not all_chunks['metadatas']:
                return {
                    'document_id': document_id,
                    'chunk_count': 0,
                    'chunks': [],
                    'metadatas': [],
                    'ids': [],
                    'pagination': {'current_page': page, 'page_size': page_size, 'total_pages': 0, 'total_chunks': 0}
                }
            combined = list(zip(all_chunks['documents'], all_chunks['metadatas'], all_chunks['ids']))
            combined.sort(key=lambda x: x[1].get('chunk_id', 0))
            total_chunks = len(combined)
            total_pages = (total_chunks + page_size - 1) // page_size
            offset = (page - 1) * page_size
            paginated = combined[offset:offset + page_size]
            if paginated:
                docs, metas, ids = zip(*paginated)
                return {
                    'document_id': document_id,
                    'chunk_count': len(docs),
                    'chunks': list(docs),
                    'metadatas': list(metas),
                    'ids': list(ids),
                    'pagination': {
                        'current_page': page,
                        'page_size': page_size,
                        'total_pages': total_pages,
                        'total_chunks': total_chunks,
                        'has_next': page < total_pages,
                        'has_prev': page > 1
                    }
                }
            return {
                'document_id': document_id,
                'chunk_count': 0,
                'chunks': [],
                'metadatas': [],
                'ids': [],
                'pagination': {'current_page': page, 'page_size': page_size, 'total_pages': 0, 'total_chunks': 0}
            }
        except Exception:
            return {'document_id': document_id, 'chunk_count': 0, 'chunks': [], 'metadatas': [], 'ids': []}

    def get_page_summary(self, document_id: str) -> dict:
        """
        Get a summary of page information for a document.
        Args:
            document_id: Document identifier
        Returns:
            Dictionary with page statistics and ranges
        """
        try:
            results = self.collection.get(
                where={"book_id": document_id},
                include=["metadatas"]
            )
            if not results['metadatas']:
                return {'document_id': document_id, 'error': 'No chunks found'}
            page_starts = []
            page_ends = []
            page_types = set()
            total_pages = 0
            for meta in results['metadatas']:
                if meta:
                    if 'page_start' in meta:
                        page_starts.append(meta['page_start'])
                    if 'page_end' in meta:
                        page_ends.append(meta['page_end'])
                    if 'page_type' in meta:
                        page_types.add(meta['page_type'])
                    if 'total_pages' in meta:
                        total_pages = max(total_pages, meta['total_pages'])
            return {
                'document_id': document_id,
                'chunk_count': len(results['metadatas']),
                'page_range': {
                    'first_page': min(page_starts) if page_starts else None,
                    'last_page': max(page_ends) if page_ends else None,
                    'total_pages': total_pages
                },
                'page_types': list(page_types),
                'coverage': {
                    'chunks_with_page_info': len([m for m in results['metadatas'] if m and 'page_start' in m]),
                    'total_chunks': len(results['metadatas'])
                }
            }
        except Exception as e:
            return {'document_id': document_id, 'error': str(e)}
