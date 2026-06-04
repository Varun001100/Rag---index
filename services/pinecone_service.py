from pinecone import Pinecone, ServerlessSpec
from config.settings import settings
from utils.logger import logger
from typing import List, Dict, Any

class PineconeService:
    def __init__(self):
        self.api_key = settings.PINECONE_API_KEY
        self.index_name = settings.PINECONE_INDEX_NAME
        self._pc = None
        self._index = None

    def _get_client(self) -> Pinecone:
        if not self._pc:
            if not self.api_key:
                raise ValueError("PINECONE_API_KEY environment variable is not set.")
            self._pc = Pinecone(api_key=self.api_key)
        return self._pc

    def get_index(self):
        if not self._index:
            pc = self._get_client()
            if not self.index_name:
                raise ValueError("PINECONE_INDEX_NAME environment variable is not set.")
            self._index = pc.Index(self.index_name)
        return self._index

    def initialize_index(self, dimension: int = 384, metric: str = "cosine") -> None:
        """Checks if the index exists. If not, creates it serverless on AWS."""
        logger.info(f"Initializing Pinecone index: '{self.index_name}'")
        try:
            pc = self._get_client()
            existing_indexes = [idx.name for idx in pc.list_indexes()]
            if self.index_name not in existing_indexes:
                logger.info(f"Index '{self.index_name}' does not exist. Creating serverless index...")
                pc.create_index(
                    name=self.index_name,
                    dimension=dimension,
                    metric=metric,
                    spec=ServerlessSpec(
                        cloud="aws",
                        region="us-east-1"
                    )
                )
                logger.info(f"Index '{self.index_name}' created successfully.")
            else:
                logger.info(f"Index '{self.index_name}' already exists.")
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone index: {str(e)}")
            raise e

    def upsert_vectors(self, vectors: List[Dict[str, Any]]) -> None:
        """
        Upserts vectors to the active Pinecone index.
        
        Args:
            vectors: List of dicts, each with keys 'id', 'values', 'metadata'.
        """
        index = self.get_index()
        logger.info(f"Upserting {len(vectors)} vectors to Pinecone index '{self.index_name}'")
        try:
            batch_size = 100
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i:i + batch_size]
                formatted_batch = [
                    (v["id"], v["values"], v["metadata"]) for v in batch
                ]
                index.upsert(vectors=formatted_batch)
            logger.info("Pinecone upsert batch execution complete.")
        except Exception as e:
            logger.error(f"Pinecone upsert failed: {str(e)}")
            raise e

    def search_vectors(self, query_vector: List[float], workspace_id: str, top_k: int = 20) -> List[Dict[str, Any]]:
        """
        Search Pinecone vectors with metadata filtering on workspace_id.
        
        Args:
            query_vector: The float-list query vector embedding.
            workspace_id: The active workspace context filter.
            top_k: Number of elements to return.
            
        Returns:
            List of parsed hit result dictionaries.
        """
        index = self.get_index()
        logger.info(f"Searching vectors in workspace {workspace_id} (top_k={top_k})")
        try:
            response = index.query(
                vector=query_vector,
                top_k=top_k,
                filter={"workspace_id": {"$eq": workspace_id}},
                include_metadata=True
            )
            
            results = []
            for match in response.get("matches", []):
                metadata = match.get("metadata", {})
                results.append({
                    "id": match.get("id"),
                    "score": match.get("score"),
                    "workspace_id": metadata.get("workspace_id"),
                    "document_id": int(metadata.get("document_id", 0)),
                    "filename": metadata.get("filename"),
                    "page_number": int(metadata.get("page_number", 0)),
                    "parent_id": metadata.get("parent_id"),
                    "content": metadata.get("content", "")
                })
            return results
        except Exception as e:
            logger.error(f"Pinecone search failed: {str(e)}")
            raise e

    def delete_workspace_vectors(self, workspace_id: str) -> None:
        """Deletes all vectors that match the workspace_id filter."""
        index = self.get_index()
        logger.info(f"Deleting all vectors for workspace {workspace_id}")
        try:
            index.delete(filter={"workspace_id": {"$eq": workspace_id}})
            logger.info(f"Deleted vectors for workspace {workspace_id} from Pinecone.")
        except Exception as e:
            logger.error(f"Failed to delete workspace vectors for {workspace_id}: {str(e)}")
            raise e
