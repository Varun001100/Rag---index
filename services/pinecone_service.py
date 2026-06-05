from pinecone import Pinecone
from config.settings import Config


class PineconeService:

    _index = None

    @classmethod
    def get_index(cls):

        if cls._index is None:

            pc = Pinecone(
                api_key=Config.PINECONE_API_KEY
            )

            cls._index = pc.Index(
                Config.PINECONE_INDEX_NAME
            )

        return cls._index

    @classmethod
    def upsert_child_chunks(
        cls,
        vectors,
        batch_size=50
    ):

        index = cls.get_index()

        for i in range(
            0,
            len(vectors),
            batch_size
        ):

            batch = vectors[
                i:i + batch_size
            ]

            index.upsert(
                vectors=batch
            )

    @classmethod
    def search(
        cls,
        query_embedding,
        session_id,
        top_k=20
    ):

        index = cls.get_index()

        results = index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True,
            filter={
                "session_id": {
                    "$eq": session_id
                }
            }
        )

        return results

    @classmethod
    def delete_session_vectors(
        cls,
        session_id
    ):

        index = cls.get_index()

        index.delete(
            filter={
                "session_id": {
                    "$eq": session_id
                }
            }
        )

    @classmethod
    def delete_document_vectors(
        cls,
        document_id
    ):
        """
        Deletes all vector embeddings associated with a specific document ID.
        """
        index = cls.get_index()

        index.delete(
            filter={
                "document_id": {
                    "$eq": document_id
                }
            }
        )