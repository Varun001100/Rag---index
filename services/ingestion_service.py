from database.db import get_db
from services.parser_service import ParserService
from services.chunking_service import ChunkingService
from services.embedding_service import EmbeddingService
from services.pinecone_service import PineconeService
from services.workspace_service import WorkspaceService
from utils.logger import logger

class IngestionService:
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.pinecone_service = PineconeService()
        
    def ingest_pdf(self, workspace_id: str, filename: str, file_path: str) -> int:
        """
        Orchestrates the entire PDF ingestion pipeline.
        
        Steps:
        1. Extract text page-by-page.
        2. Record document metadata in database.
        3. Break text into Parent and Child chunks.
        4. Insert Parent chunks into local SQLite.
        5. Embed Child chunks.
        6. Upsert Child chunk vectors and metadata into Pinecone.
        
        Args:
            workspace_id: The ID of the current workspace.
            filename: The original PDF filename.
            file_path: The absolute path to the stored PDF file on disk.
            
        Returns:
            The primary key integer (document_id) of the newly created document record.
        """
        logger.info(f"Initiating PDF Ingestion Pipeline for: {filename} in workspace: {workspace_id}")
        
        # Keep workspace activity fresh
        WorkspaceService.update_last_accessed(workspace_id)
        
        # 1. Text Extraction
        pages = ParserService.extract_text(file_path)
        if not pages:
            raise ValueError(f"PDF Parsing Failed: No text extracted from {filename}")
            
        total_pages = len(pages)
        document_id = None
        
        try:
            # 2. Database Insertion (transactional context)
            with get_db() as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO documents (workspace_id, filename, file_path, total_pages)
                    VALUES (?, ?, ?, ?)
                    """,
                    (workspace_id, filename, file_path, total_pages)
                )
                document_id = cursor.lastrowid
                
                # 3. Chunks generation
                chunks = ChunkingService.generate_chunks(pages, workspace_id, document_id)
                
                parent_chunks = [c for c in chunks if c["type"] == "parent"]
                child_chunks = [c for c in chunks if c["type"] == "child"]
                
                # 4. Save Parent Chunks in SQLite
                for parent in parent_chunks:
                    conn.execute(
                        """
                        INSERT INTO parent_chunks (parent_id, workspace_id, document_id, page_number, content)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            parent["parent_id"],
                            parent["workspace_id"],
                            parent["document_id"],
                            parent["page_number"],
                            parent["content"]
                        )
                    )
                    
            # 5. Embedding and Pinecone Upsert
            if child_chunks:
                child_texts = [child["content"] for child in child_chunks]
                embeddings = self.embedding_service.embed_document(child_texts)
                
                pinecone_vectors = []
                for idx, (child, vector) in enumerate(zip(child_chunks, embeddings)):
                    vector_id = f"{workspace_id}_{document_id}_c{idx}"
                    pinecone_vectors.append({
                        "id": vector_id,
                        "values": vector,
                        "metadata": {
                            "workspace_id": workspace_id,
                            "document_id": document_id,
                            "filename": filename,
                            "page_number": child["page_number"],
                            "parent_id": child["parent_id"],
                            "content": child["content"]
                        }
                    })
                    
                # 6. Upsert vectors to Pinecone
                self.pinecone_service.upsert_vectors(pinecone_vectors)
                
            logger.info(f"Ingestion pipeline completed for: {filename} (Document ID: {document_id}).")
            return document_id
            
        except Exception as e:
            logger.error(f"Ingestion pipeline failed for document {filename}: {str(e)}")
            raise e
