import pytest
import os
import tempfile
import shutil
from unittest.mock import MagicMock, patch
from database.db import get_db, init_db
from config.settings import settings
from services.chunking_service import ChunkingService
from services.embedding_service import EmbeddingService
from services.reranker_service import RerankerService
from services.context_service import ContextService
from services.citation_service import CitationService
from services.workspace_service import WorkspaceService
from services.cleanup_service import CleanupService

# Setup temporary sqlite database for isolation during test suites run
@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    temp_dir = tempfile.mkdtemp()
    temp_db_path = os.path.join(temp_dir, "test_rag.db")
    
    # Save configuration variables
    orig_db = settings.DATABASE_PATH
    orig_upload = settings.UPLOAD_DIR
    
    # Apply testing configurations
    settings.DATABASE_PATH = temp_db_path
    settings.UPLOAD_DIR = os.path.join(temp_dir, "uploads")
    
    init_db()
    
    yield
    
    # Restore original settings and clear workspace folders
    settings.DATABASE_PATH = orig_db
    settings.UPLOAD_DIR = orig_upload
    shutil.rmtree(temp_dir)

def test_workspace_creation():
    ws_service = WorkspaceService()
    ws_id = ws_service.create_workspace()
    
    assert ws_id.startswith("ws_")
    assert len(ws_id) == 9  # ws_ prefix (3 chars) + 6 hex character length
    assert ws_service.workspace_exists(ws_id) is True

def test_chunk_generation():
    pages = {
        1: "This is paragraph one. It spans multiple lines.\n\nThis is paragraph two. It is distinct.",
        2: "This is page two. Sentence parsing check."
    }
    
    chunks = ChunkingService.generate_chunks(
        pages=pages,
        workspace_id="ws_test",
        document_id=1,
        parent_size=200,
        child_size=50,
        child_overlap=10
    )
    
    parents = [c for c in chunks if c["type"] == "parent"]
    children = [c for c in chunks if c["type"] == "child"]
    
    assert len(parents) > 0
    assert len(children) > 0
    assert all(c["parent_id"] is not None for c in children)

@patch("services.embedding_service.SentenceTransformer")
def test_embedding_generation(mock_transformer):
    mock_model_instance = MagicMock()
    mock_model_instance.encode.return_value = [0.1] * 384
    mock_transformer.return_value = mock_model_instance
    
    embed_service = EmbeddingService()
    embed_service._model = None  # Reset embedding singleton
    
    vec = embed_service.embed_query("Hello RAG")
    assert len(vec) == 384
    mock_model_instance.encode.assert_called_once()

@patch("services.reranker_service.CrossEncoder")
def test_reranking(mock_cross_encoder):
    mock_encoder_instance = MagicMock()
    mock_encoder_instance.predict.return_value = [0.98, 0.40]
    mock_cross_encoder.return_value = mock_encoder_instance
    
    rerank_service = RerankerService()
    rerank_service._model = None
    
    hits = [
        {"content": "Passage A", "parent_id": "p1", "filename": "doc.pdf", "page_number": 1},
        {"content": "Passage B", "parent_id": "p2", "filename": "doc.pdf", "page_number": 2}
    ]
    
    top_results = rerank_service.rerank("Query", hits, top_n=1)
    assert len(top_results) == 1
    assert top_results[0]["content"] == "Passage A"
    assert top_results[0]["rerank_score"] == 0.98

def test_context_building_and_citations():
    ws_service = WorkspaceService()
    ws_id = ws_service.create_workspace()
    
    # Store dummy parents
    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO documents (workspace_id, filename, file_path, total_pages)
            VALUES (?, ?, ?, ?)
            """,
            (ws_id, "MachineLearning.pdf", "dummy_path", 15)
        )
        doc_id = cursor.lastrowid
        
        conn.execute(
            """
            INSERT INTO parent_chunks (parent_id, workspace_id, document_id, page_number, content)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("p_dummy_1", ws_id, doc_id, 12, "This is context from MachineLearning.pdf page 12.")
        )
        conn.execute(
            """
            INSERT INTO parent_chunks (parent_id, workspace_id, document_id, page_number, content)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("p_dummy_2", ws_id, doc_id, 5, "This is context from DeepLearning.pdf page 5.")
        )
        
    reranked = [
        {"parent_id": "p_dummy_1", "filename": "MachineLearning.pdf", "page_number": 12},
        {"parent_id": "p_dummy_2", "filename": "DeepLearning.pdf", "page_number": 5}
    ]
    
    ctx = ContextService.build_context(ws_id, reranked)
    assert "MachineLearning.pdf page 12" in ctx["final_context"]
    
    cits = CitationService.generate_citations(ctx["citations_raw"])
    assert "MachineLearning.pdf (Page 12)" in cits
    assert "DeepLearning.pdf (Page 5)" in cits

@patch("services.pinecone_service.Pinecone")
def test_pinecone_retrieval(mock_pinecone):
    mock_index = MagicMock()
    mock_index.query.return_value = {
        "matches": [
            {
                "id": "c1",
                "score": 0.85,
                "metadata": {
                    "workspace_id": "ws_test",
                    "document_id": 1,
                    "filename": "file.pdf",
                    "page_number": 1,
                    "parent_id": "p1",
                    "content": "Pinecone hit child text content"
                }
            }
        ]
    }
    
    mock_pc_instance = MagicMock()
    mock_pc_instance.Index.return_value = mock_index
    mock_pinecone.return_value = mock_pc_instance
    
    from services.pinecone_service import PineconeService
    p_service = PineconeService()
    p_service._pc = mock_pc_instance
    
    res = p_service.search_vectors([0.1]*384, "ws_test")
    assert len(res) == 1
    assert res[0]["parent_id"] == "p1"
    assert res[0]["content"] == "Pinecone hit child text content"

@patch("google.generativeai.GenerativeModel")
def test_gemini_generation(mock_gen_model):
    mock_model_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Answer generated based on context."
    mock_model_instance.generate_content.return_value = mock_response
    mock_gen_model.return_value = mock_model_instance
    
    from services.llm_service import LLMService
    llm = LLMService()
    llm.api_key = "dummy_gemini_key"
    
    ans = llm.generate_answer("Query", "Context text", [])
    assert ans == "Answer generated based on context."

def test_workspace_cleanup():
    ws_service = WorkspaceService()
    ws_id = ws_service.create_workspace()
    
    # Backdate the last_accessed field to trigger cleanup criteria (>24 hours)
    with get_db() as conn:
        conn.execute(
            "UPDATE workspaces SET last_accessed = datetime('now', '-30 hours') WHERE workspace_id = ?",
            (ws_id,)
        )
        
    cleanup = CleanupService()
    cleaned = cleanup.cleanup_expired_workspaces()
    
    assert cleaned == 1
    assert ws_service.workspace_exists(ws_id) is False
