from flask import Blueprint, jsonify
from services.workspace_service import WorkspaceService
from utils.logger import logger

workspace_bp = Blueprint("workspace", __name__)
workspace_service = WorkspaceService()

@workspace_bp.route("/workspace/create", methods=["POST"])
def create_workspace():
    """Endpoint to create a new isolated workspace."""
    try:
        ws_id = workspace_service.create_workspace()
        logger.info(f"API - Created workspace: {ws_id}")
        return jsonify({"workspace_id": ws_id}), 201
    except Exception as e:
        logger.error(f"API - Error creating workspace: {str(e)}")
        return jsonify({"error": "Failed to create workspace"}), 500

@workspace_bp.route("/workspace/<workspace_id>", methods=["DELETE"])
def delete_workspace(workspace_id):
    """Endpoint to delete an existing workspace and all its data."""
    try:
        if not workspace_service.workspace_exists(workspace_id):
            logger.warning(f"API - Delete failed: Workspace {workspace_id} does not exist.")
            return jsonify({"error": "Workspace not found"}), 404
            
        workspace_service.delete_workspace(workspace_id)
        logger.info(f"API - Deleted workspace: {workspace_id}")
        return jsonify({"message": "Workspace deleted successfully"}), 200
    except Exception as e:
        logger.error(f"API - Error deleting workspace {workspace_id}: {str(e)}")
        return jsonify({"error": f"Failed to delete workspace: {str(e)}"}), 500
