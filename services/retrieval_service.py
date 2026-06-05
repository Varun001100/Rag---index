from services.embedding_service import EmbeddingService
from services.pinecone_service import PineconeService
from database.db import execute_query


class RetrievalService:

    @staticmethod
    def retrieve(query, session_id, top_k=20):
        """
        Embeds the query and searches Pinecone for the top_k child chunks,
        then retrieves the corresponding parent chunks from SQLite.
        """
        # Step 1: Embed query text
        query_embedding = EmbeddingService.embed_text(query)

        # Step 2: Search Pinecone for top matches
        search_results = PineconeService.search(
            query_embedding=query_embedding,
            session_id=session_id,
            top_k=top_k
        )

        matches = getattr(search_results, "matches", [])
        if not matches:
            return []

        # Step 3: Extract unique parent IDs while preserving Pinecone order
        parent_ids = []
        parent_id_set = set()
        
        # We also keep track of Pinecone metadata (like score and child_id) if needed
        for match in matches:
            metadata = getattr(match, "metadata", {})
            parent_id = metadata.get("parent_id")
            if parent_id and parent_id not in parent_id_set:
                parent_id_set.add(parent_id)
                parent_ids.append(parent_id)

        if not parent_ids:
            return []

        # Step 4: Retrieve parent chunks and associated filenames from SQLite
        placeholders = ",".join(["?"] * len(parent_ids))
        query_sql = f"""
            SELECT p.parent_id, p.page_number, p.chunk_text, d.filename
            FROM parent_chunks p
            JOIN documents d ON p.document_id = d.document_id
            WHERE p.parent_id IN ({placeholders})
        """
        
        rows = execute_query(query_sql, tuple(parent_ids))

        # Convert query rows to dicts
        parent_chunks = []
        for row in rows:
            parent_chunks.append({
                "parent_id": row["parent_id"],
                "page_number": row["page_number"],
                "text": row["chunk_text"],
                "filename": row["filename"]
            })

        # Order the database rows to match the initial Pinecone relevance order
        parent_chunk_by_id = {chunk["parent_id"]: chunk for chunk in parent_chunks}
        ordered_parent_chunks = [
            parent_chunk_by_id[pid]
            for pid in parent_ids
            if pid in parent_chunk_by_id
        ]

        return ordered_parent_chunks
