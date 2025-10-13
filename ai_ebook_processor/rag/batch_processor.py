class BatchProcessor:
    """Handles batch and parallel processing of documents."""

    def __init__(self, collection, config, has_psutil=False):
        self.collection = collection
        self.config = config
        self.has_psutil = has_psutil

    def calculate_optimal_batch_size(self, sample_doc=None, sample_metadata=None, total_items=1000, target_memory_usage_mb=100):
        override = self.config.get("rag.batch_size_override")
        if override is not None:
            return int(override)
        import sys
        if self.has_psutil:
            import psutil
            memory = psutil.virtual_memory()
            available_mb = memory.available / (1024 * 1024)
            safe_memory_mb = min(target_memory_usage_mb, available_mb * 0.1)
        else:
            available_mb = 2048
            safe_memory_mb = min(target_memory_usage_mb, 200)
        if sample_doc and sample_metadata:
            doc_size = sys.getsizeof(sample_doc)
            meta_size = sys.getsizeof(str(sample_metadata))
            embedding_size = 384 * 4
            overhead = 200
            item_size_bytes = doc_size + meta_size + embedding_size + overhead
            item_size_mb = item_size_bytes / (1024 * 1024)
        else:
            item_size_mb = 0.002
        if item_size_mb > 0:
            memory_based_batch = int(safe_memory_mb / item_size_mb)
        else:
            memory_based_batch = 500
        batch_size = max(50, min(2000, memory_based_batch))
        if total_items < 200:
            batch_size = min(batch_size, max(10, total_items // 2))
        return batch_size

    def batch_insert(self, documents, metadatas, ids, batch_size=None, show_progress=False):
        if len(documents) != len(metadatas) or len(documents) != len(ids):
            return False
        total_docs = len(documents)
        if batch_size is None:
            batch_size = 500
        total_batches = (total_docs + batch_size - 1) // batch_size
        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, total_docs)
            batch_docs = documents[start_idx:end_idx]
            batch_metas = metadatas[start_idx:end_idx]
            batch_ids = ids[start_idx:end_idx]
            try:
                self.collection.add(
                    documents=batch_docs,
                    metadatas=batch_metas,
                    ids=batch_ids
                )
            except Exception:
                return False
        return True
