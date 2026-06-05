import os
import shutil
from flask import Blueprint, request, jsonify

from services.session_service import SessionService
from services.retrieval_service import RetrievalService
from services.reranker_service import RerankerService
from services.memory_service import MemoryService
from services.citation_service import CitationService
from services.llm_service import LlmService
from services.pinecone_service import PineconeService
from config.settings import Config
from database.db import execute_query

chat_bp = Blueprint(
    "chat",
    __name__,
    url_prefix="/api/chat"
)


@chat_bp.route("/health", methods=["GET"])
def chat_health():
    return jsonify({
        "status": "success",
        "service": "chat_routes"
    }), 200


@chat_bp.route("/message", methods=["POST"])
def chat_message():
    """
    Core RAG chatbot endpoint: retrieves context, reranks chunks,
    generates response with citations, and saves turn memory.
    """
    data = request.get_json() or {}
    session_id = data.get("session_id")
    message = data.get("message")

    if not session_id or not message:
        return jsonify({
            "success": False,
            "message": "session_id and message are required"
        }), 400

    # 1. Verify session exists
    if not SessionService.session_exists(session_id):
        return jsonify({
            "success": False,
            "message": "Invalid or expired session"
        }), 404

    try:
        # 2. Retrieve parent chunks from vector db and SQLite
        parent_chunks = RetrievalService.retrieve(
            query=message,
            session_id=session_id,
            top_k=Config.TOP_K_RETRIEVAL
        )

        # 3. Rerank parent chunks to top N using cross-encoder
        reranked_chunks = RerankerService.rerank(
            query=message,
            chunks=parent_chunks,
            top_n=Config.TOP_K_RERANK
        )

        # 4. Extract citations
        citations = CitationService.get_citations(reranked_chunks)

        # 5. Retrieve recent conversation history
        history = MemoryService.get_history(session_id, limit=5)

        # 6. Generate answer using Gemini
        answer = LlmService.generate_answer(
            query=message,
            chunks=reranked_chunks,
            history=history
        )

        # 7. Save conversation turn to memory
        MemoryService.add_message(session_id, message, answer)

        return jsonify({
            "success": True,
            "answer": answer,
            "citations": citations
        }), 200

    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        return jsonify({
            "success": False,
            "message": f"An error occurred: {str(e)}"
        }), 500


@chat_bp.route("/history/<session_id>", methods=["GET"])
def chat_history(session_id):
    """
    Fetches the conversation history for a given session.
    """
    if not SessionService.session_exists(session_id):
        return jsonify({
            "success": False,
            "message": "Invalid or expired session"
        }), 404

    try:
        history = MemoryService.get_history(session_id, limit=20)
        return jsonify({
            "success": True,
            "history": history
        }), 200
    except Exception as e:
        print(f"Error fetching chat history: {e}")
        return jsonify({
            "success": False,
            "message": f"Failed to retrieve chat history: {str(e)}"
        }), 500


@chat_bp.route("/session/<session_id>", methods=["DELETE"])
def delete_session(session_id):
    """
    Purges a session: deletes SQLite records, physical files, and Pinecone vectors.
    """
    if not SessionService.session_exists(session_id):
        return jsonify({
            "success": False,
            "message": "Session does not exist"
        }), 404

    try:
        # 1. Clean Pinecone vectors
        PineconeService.delete_session_vectors(session_id)

        # 2. Delete database records (cascade will delete docs, parent chunks, conversations)
        SessionService.delete_session(session_id)

        # 3. Delete physical uploaded files and the session directory
        session_folder = os.path.join(Config.UPLOAD_FOLDER, session_id)
        if os.path.exists(session_folder):
            shutil.rmtree(session_folder)

        return jsonify({
            "success": True,
            "message": "Session and all associated data cleared successfully."
        }), 200

    except Exception as e:
        print(f"Error cleaning up session: {e}")
        return jsonify({
            "success": False,
            "message": f"Failed to clean up session: {str(e)}"
        }), 500