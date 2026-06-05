from sentence_transformers import CrossEncoder
from config.settings import Config


class RerankerService:

    _model = None

    @classmethod
    def load_model(cls):
        """
        Loads and caches the CrossEncoder model.
        """
        if cls._model is None:
            # Load the cross-encoder model specified in the settings
            cls._model = CrossEncoder(Config.RERANKER_MODEL)
        return cls._model

    @classmethod
    def rerank(cls, query, chunks, top_n=None):
        """
        Reranks parent chunks based on query relevance.
        
        Args:
            query (str): The search query.
            chunks (list): A list of parent chunk dicts containing 'text' keys.
            top_n (int): The number of top chunks to return. Defaults to Config.TOP_K_RERANK.
            
        Returns:
            list: The reranked list of chunks, sorted by score descending, limited to top_n.
        """
        if not chunks:
            return []

        if top_n is None:
            top_n = Config.TOP_K_RERANK

        model = cls.load_model()

        # Build pairs of [query, doc_text]
        pairs = [[query, chunk["text"]] for chunk in chunks]

        # Predict relevance scores (higher is more relevant)
        scores = model.predict(pairs)

        # Attach scores to the chunks
        scored_chunks = []
        for chunk, score in zip(chunks, scores):
            # Convert numpy float to native float
            chunk_with_score = dict(chunk)
            chunk_with_score["score"] = float(score)
            scored_chunks.append(chunk_with_score)

        # Sort descending by score
        scored_chunks.sort(key=lambda x: x["score"], reverse=True)

        return scored_chunks[:top_n]
