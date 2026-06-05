import threading

from services.parser_service import ParserService
from services.chunking_service import ChunkingService
from services.embedding_service import EmbeddingService
from services.pinecone_service import PineconeService

from database.db import execute_insert, execute_query


class IngestionService:

    _status = {}  # In-memory dictionary to track ingestion status of documents

    @classmethod
    def get_status(cls, document_id):
        """
        Retrieves the current status of a document's background ingestion.
        If not found in-memory, checks the SQLite database as a fallback.
        """
        # If active in-memory record exists, return it
        if document_id in cls._status:
            return cls._status[document_id]

        # Check in database
        try:
            doc_records = execute_query(
                "SELECT filename FROM documents WHERE document_id = ?",
                (document_id,)
            )
            if doc_records:
                # Document is present in DB, meaning it has successfully completed ingestion in the past
                pages_res = execute_query(
                    "SELECT COUNT(DISTINCT page_number) as count FROM parent_chunks WHERE document_id = ?",
                    (document_id,)
                )
                parents_res = execute_query(
                    "SELECT COUNT(*) as count FROM parent_chunks WHERE document_id = ?",
                    (document_id,)
                )
                
                pages = pages_res[0]["count"] if pages_res else 0
                parents = parents_res[0]["count"] if parents_res else 0
                
                return {
                    "status": "completed",
                    "message": "Ingestion completed successfully!",
                    "pages": pages,
                    "parents": parents,
                    "children": parents  # Rough estimate
                }
        except Exception as e:
            print(f"Error checking database fallback status for {document_id}: {e}")

        return {
            "status": "unknown",
            "message": "No ingestion record found."
        }

    @classmethod
    def set_status(cls, document_id, status_dict):
        """
        Updates the status dictionary of a document.
        """
        cls._status[document_id] = status_dict

    @classmethod
    def ingest_document(
        cls,
        session_id,
        document_id,
        filename,
        file_path
    ):
        """
        Launches the document ingestion process in a background thread
        and returns immediately with a tracking status.
        """
        cls.set_status(document_id, {
            "status": "processing",
            "message": "Extracting text from PDF...",
            "pages": 0,
            "parents": 0,
            "children": 0
        })

        def run_pipeline():
            try:
                # 1. Parse text from PDF
                pages = ParserService.extract_text(file_path)

                if not pages:
                    cls.set_status(document_id, {
                        "status": "failed",
                        "message": "No text could be extracted. Check if PDF is empty or scanned."
                    })
                    return

                cls.set_status(document_id, {
                    "status": "processing",
                    "message": f"Parsed {len(pages)} pages. Storing document record...",
                    "pages": len(pages),
                    "parents": 0,
                    "children": 0
                })

                # 2. Store document record in SQLite (required for foreign key constraints)
                execute_insert(
                    """
                    INSERT OR IGNORE INTO documents (
                        document_id,
                        session_id,
                        filename,
                        file_path
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        document_id,
                        session_id,
                        filename,
                        file_path
                    )
                )

                # 3. Create parent-child chunks
                result = (
                    ChunkingService
                    .create_parent_child_chunks(
                        pages
                    )
                )

                parent_chunks = result["parents"]
                child_chunks = result["children"]

                cls.set_status(document_id, {
                    "status": "processing",
                    "message": f"Created {len(parent_chunks)} parent chunks. Storing in DB...",
                    "pages": len(pages),
                    "parents": len(parent_chunks),
                    "children": len(child_chunks)
                })

                # 4. Store parent chunks in SQLite
                for parent in parent_chunks:
                    execute_insert(
                        """
                        INSERT INTO parent_chunks (
                            parent_id,
                            session_id,
                            document_id,
                            page_number,
                            chunk_text
                        )
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            parent["parent_id"],
                            session_id,
                            document_id,
                            parent["page_number"],
                            parent["text"]
                        )
                    )

                cls.set_status(document_id, {
                    "status": "processing",
                    "message": f"Generating embeddings for {len(child_chunks)} chunks...",
                    "pages": len(pages),
                    "parents": len(parent_chunks),
                    "children": len(child_chunks)
                })

                # 5. Create vectors for Pinecone
                vectors = []
                child_texts = [
                    child["text"]
                    for child in child_chunks
                ]

                embeddings = (
                    EmbeddingService
                    .embed_batch(
                        child_texts
                    )
                )

                for child, embedding in zip(
                    child_chunks,
                    embeddings
                ):
                    vectors.append({
                        "id":
                            child["child_id"],

                        "values":
                            embedding,

                        "metadata": {
                            "session_id":
                                session_id,

                            "document_id":
                                document_id,

                            "filename":
                                filename,

                            "page_number":
                                child["page_number"],

                            "parent_id":
                                child["parent_id"],
                        }
                    })

                cls.set_status(document_id, {
                    "status": "processing",
                    "message": f"Uploading vectors to Pinecone...",
                    "pages": len(pages),
                    "parents": len(parent_chunks),
                    "children": len(child_chunks)
                })

                # 6. Upload vectors to Pinecone
                PineconeService.upsert_child_chunks(
                    vectors
                )

                # Set success status
                cls.set_status(document_id, {
                    "status": "completed",
                    "message": "Ingestion completed successfully!",
                    "pages": len(pages),
                    "parents": len(parent_chunks),
                    "children": len(child_chunks)
                })

            except Exception as e:
                print(f"Ingestion error on document {document_id}: {e}")
                cls.set_status(document_id, {
                    "status": "failed",
                    "message": f"Ingestion failed: {str(e)}",
                    "pages": 0,
                    "parents": 0,
                    "children": 0
                })

        # Launch run_pipeline inside a daemon background thread
        threading.Thread(target=run_pipeline, daemon=True).start()

        # Return the initial processing status immediately
        return cls.get_status(document_id)