class EmbeddingManager:
    """Handles model loading, encoding, and batch embedding."""

    def __init__(self, config):
        self.config = config
        self._encoder = None

    def load_encoder(self):
        """
        Lazy load sentence transformer model only when needed.
        """
        if self._encoder is None:
            try:
                import torch
                from sentence_transformers import SentenceTransformer
                model_name = self.config.get("rag.embedding_model") or "all-MiniLM-L6-v2"
                device = "cuda" if torch.cuda.is_available() else "cpu"
                self._encoder = SentenceTransformer(model_name, device=device)
            except Exception as e:
                raise ImportError(f"Could not load embedding model: {e}")
        return self._encoder

    def encode(self, chunk_texts: list, show_progress_bar: bool = True):
        """
        Centralized embedding logic for chunk texts. Returns list of embeddings.
        """
        encoder = self.load_encoder()
        return encoder.encode(chunk_texts, show_progress_bar=show_progress_bar)
