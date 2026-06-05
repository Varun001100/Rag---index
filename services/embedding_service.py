from sentence_transformers import SentenceTransformer


class EmbeddingService:

    _model = None

    @classmethod
    def load_model(cls):

        if cls._model is None:

            cls._model = SentenceTransformer(
                "BAAI/bge-small-en-v1.5"
            )

        return cls._model

    @classmethod
    def embed_text(
        cls,
        text
    ):

        model = cls.load_model()

        embedding = model.encode(
            text,
            normalize_embeddings=True
        )

        return embedding.tolist()

    @classmethod
    def embed_batch(
        cls,
        texts
    ):

        model = cls.load_model()

        embeddings = model.encode(
            texts,
            normalize_embeddings=True,
            batch_size=32,
            show_progress_bar=False
        )

        return embeddings.tolist()