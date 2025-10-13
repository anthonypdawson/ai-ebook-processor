class DocumentRegistry:
    """Manages document registration, deduplication, and metadata."""

    def __init__(self, registry):
        self.registry = registry

    def register_document(self, document_id: str, metadata: dict, chunk_ids: list = None) -> bool:
        """
        Register a document in the registry for fast lookup.
        Args:
            document_id: Unique document identifier
            metadata: Document metadata dictionary
            chunk_ids: List of chunk IDs for this document
        Returns:
            True if successful, False otherwise
        """
        try:
            enhanced_metadata = metadata.copy()
            if chunk_ids:
                enhanced_metadata.update({
                    'chunk_count': len(chunk_ids),
                    'first_chunk_id': chunk_ids[0] if chunk_ids else '',
                    'last_chunk_id': chunk_ids[-1] if chunk_ids else '',
                    'chunk_id_pattern': f"{document_id}_chunk_*",
                    'chunk_range': f"{chunk_ids[0]} to {chunk_ids[-1]}" if chunk_ids else ''
                })
            elif 'chunks' in metadata:
                enhanced_metadata['chunk_count'] = metadata['chunks']
            existing = self.registry.get(ids=[document_id])
            if existing['ids']:
                self.registry.update(
                    ids=[document_id],
                    metadatas=[enhanced_metadata]
                )
            else:
                self.registry.add(
                    ids=[document_id],
                    documents=[f"Document: {metadata.get('title', 'Unknown')} ({len(chunk_ids or [])} chunks)"],
                    metadatas=[enhanced_metadata]
                )
            return True
        except Exception:
            return False

    def update_registry_with_chunk_info(self, document_id: str = None) -> bool:
        """
        Update registry entries with chunk offset information for efficient retrieval.
        Args:
            document_id: Specific document to update, or None to update all documents
        Returns:
            True if successful
        """
        try:
            if document_id:
                document_ids_to_update = [document_id]
            else:
                registry_results = self.registry.get(include=["metadatas"])
                document_ids_to_update = []
                for i, metadata in enumerate(registry_results.get('metadatas', [])):
                    if metadata and not metadata.get('first_chunk_id'):
                        doc_id = metadata.get('book_id')
                        if doc_id:
                            document_ids_to_update.append(doc_id)
            for doc_id in document_ids_to_update:
                chunk_results = self.registry.get(
                    where={"book_id": doc_id},
                    include=[]
                )
                if chunk_results['ids']:
                    chunk_ids = sorted(chunk_results['ids'])
                    registry_doc = self.registry.get(ids=[doc_id])
                    if registry_doc['metadatas']:
                        existing_metadata = registry_doc['metadatas'][0].copy()
                        existing_metadata.update({
                            'chunk_count': len(chunk_ids),
                            'first_chunk_id': chunk_ids[0],
                            'last_chunk_id': chunk_ids[-1],
                            'chunk_id_pattern': f"{doc_id}_chunk_*",
                            'chunk_range': f"{chunk_ids[0]} to {chunk_ids[-1]}"
                        })
                        self.registry.update(
                            ids=[doc_id],
                            metadatas=[existing_metadata]
                        )
            return True
        except Exception:
            return False

    def document_exists(self, document_id: str) -> bool:
        """
        Check if document already exists in the registry.
        Args:
            document_id: Unique identifier for the document
        Returns:
            True if document exists, False otherwise
        """
        try:
            registry_results = self.registry.get(ids=[document_id])
            if registry_results['ids']:
                return True
            return False
        except Exception:
            return False

    def list_documents(self) -> list:
        """
        List all documents in the registry.
        Returns:
            List of dictionaries with document information
        """
        try:
            registry_results = self.registry.get(include=["metadatas"])
            documents = []
            for metadata in registry_results.get('metadatas', []):
                if metadata:
                    chunk_count = metadata.get('chunk_count', metadata.get('chunks', 0))
                    documents.append({
                        'document_id': metadata.get('book_id', 'Unknown'),
                        'title': metadata.get('title', 'Unknown'),
                        'author': metadata.get('author', 'Unknown'),
                        'format': metadata.get('format', 'Unknown'),
                        'file_hash': metadata.get('file_hash', ''),
                        'chunks': chunk_count,
                        'chunk_range': metadata.get('chunk_range', ''),
                        'first_chunk_id': metadata.get('first_chunk_id', ''),
                        'last_chunk_id': metadata.get('last_chunk_id', '')
                    })
            return documents
        except Exception:
            return []
