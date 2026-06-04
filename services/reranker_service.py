import threading
from typing import List, Dict, Any
from sentence_transformers import CrossEncoder
from utils.logger import logger

class RerankerService:
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
        self.model_name = "cross-encoder/ms-marco-MiniLM-L-6-v2"
        self._model = None
        self._initialized = True

    def load_model(self) -> CrossEncoder:
        """Lazy load the CrossEncoder reranker model on demand."""
        if self._model is None:
            with self._lock:
                if self._model is None:
                    logger.info(f"Loading reranker model: {self.model_name}...")
                    self._model = CrossEncoder(self.model_name)
                    logger.info(f"Reranker model {self.model_name} loaded successfully.")
        return self._model

    def rerank(self, query: str, results: List[Dict[str, Any]], top_n: int = 5) -> List[Dict[str, Any]]:
        """
        Reranks a list of Pinecone search results using MS-Marco MiniLM CrossEncoder.
        
        Args:
            query: The user's query string.
            results: List of retrieved child chunk dictionaries.
            top_n: Number of results to return after sorting.
            
        Returns:
            Top N reranked result dictionaries.
        """
        if not results:
            return []
            
        logger.info(f"Reranking {len(results)} search results for query: '{query}'")
        model = self.load_model()
        
        # Build query-document input pairs for Cross-Encoder evaluation
        pairs = [[query, r["content"]] for r in results]
        
        # MS-Marco outputs a logit representing relevance likelihood
        scores = model.predict(pairs)
        
        for idx, score in enumerate(scores):
            results[idx]["rerank_score"] = float(score)
            
        # Sort results by the Cross-Encoder score descending
        sorted_results = sorted(results, key=lambda x: x["rerank_score"], reverse=True)
        top_results = sorted_results[:top_n]
        
        logger.info(f"Completed reranking. Returning top {len(top_results)} results.")
        return top_results
