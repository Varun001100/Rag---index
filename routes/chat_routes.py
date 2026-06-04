from flask import Blueprint, request, jsonify
from services.workspace_service import WorkspaceService
from services.retrieval_service import RetrievalService
from utils.logger import logger

chat_bp = Blueprint("chat", __name__)
workspace_service = WorkspaceService()
retrieval_service = RetrievalService()

@chat_bp.route("/chat", methods=["POST"])
def chat():
    """
    Endpoint to send queries to the workspace assistant.
    Expects JSON body: {"workspace_id": "...", "message": "..."}
    """
    data = request.get_json() or {}
    workspace_id = data.get("workspace_id")
    message = data.get("message")
    
    if not workspace_id or not message:
        logger.warning("API - Chat request received with missing parameters.")
        return jsonify({"error": "workspace_id and message are required"}), 400
        
    if not workspace_service.workspace_exists(workspace_id):
        logger.warning(f"API - Chat request received for non-existent workspace: {workspace_id}")
        return jsonify({"error": "Workspace does not exist"}), 404
        
    try:
        # Run retrieval and answer generation pipeline
        result = retrieval_service.query_workspace(workspace_id, message)
        return jsonify({
            "answer": result["answer"],
            "citations": result["citations"]
        }), 200
    except Exception as e:
        logger.error(f"API - Chat pipeline error in workspace {workspace_id}: {str(e)}")
        return jsonify({"error": f"Failed to generate answer: {str(e)}"}), 500
