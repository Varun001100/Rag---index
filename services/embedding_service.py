import threading
from typing import List, Union
from sentence_transformers import SentenceTransformer
from utils.logger import logger

class EmbeddingService:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self.model_name = "BAAI/bge-small-en-v1.5"
        self._model = None
        self._initialized = True

    def load_model(self) -> SentenceTransformer:
        """Lazy load the sentence transformer model on demand."""
        if self._model is None:
            with self._lock:
                if self._model is None:
                    logger.info(f"Loading embedding model: {self.model_name}...")
                    # Automatically downloads and caches model files
                    self._model = SentenceTransformer(self.model_name)
                    logger.info(f"Embedding model {self.model_name} loaded successfully.")
        return self._model

    def embed_document(self, texts: Union[str, List[str]]) -> List[List[float]]:
        """
        Generate embeddings for one or more document chunks.
        
        Args:
            texts: A single text chunk or list of text chunks.
            
        Returns:
            List of embedding lists (floats).
        """
        model = self.load_model()
        if isinstance(texts, str):
            texts = [texts]
            
        logger.info(f"Generating embeddings for {len(texts)} chunks.")
        embeddings = model.encode(texts, normalize_embeddings=True)
        if hasattr(embeddings, "tolist"):
            return embeddings.tolist()
        return [list(e) for e in embeddings]

    def embed_query(self, query: str) -> List[float]:
        """
        Generate embedding for a query. Uses query prefix for BGE search relevance.
        
        Args:
            query: The question text.
            
        Returns:
            List of floats representing the embedding vector.
        """
        model = self.load_model()
        logger.info(f"Generating embedding for query: '{query}'")
        # BGE models use a specific prefix to achieve optimal retrieval performance
        query_with_prefix = f"Represent this sentence for searching relevant passages: {query}"
        embedding = model.encode(query_with_prefix, normalize_embeddings=True)
        if hasattr(embedding, "tolist"):
            return embedding.tolist()
        return list(embedding)
