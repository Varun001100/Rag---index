import os
from flask import Blueprint, request, jsonify
from services.workspace_service import WorkspaceService
from services.ingestion_service import IngestionService
from config.settings import settings
from utils.file_utils import is_allowed_file, get_workspace_upload_dir
from database.db import get_db
from werkzeug.utils import secure_filename
from utils.logger import logger

upload_bp = Blueprint("upload", __name__)
workspace_service = WorkspaceService()
ingestion_service = IngestionService()

@upload_bp.route("/upload", methods=["POST"])
def upload_files():
    """
    Accepts one or more PDF files in the 'files' field.
    Requires workspace_id as a form field.
    """
    # 1. Validate Workspace ID
    workspace_id = request.form.get("workspace_id")
    if not workspace_id:
        logger.warning("API - Upload request received without workspace_id.")
        return jsonify({"error": "workspace_id is required"}), 400
        
    if not workspace_service.workspace_exists(workspace_id):
        logger.warning(f"API - Upload request received for non-existent workspace: {workspace_id}")
        return jsonify({"error": "Workspace does not exist"}), 404
        
    # 2. Check files are in Request
    if "files" not in request.files:
        logger.warning("API - Upload request received without files field.")
        return jsonify({"error": "No file part in the request"}), 400
        
    files = request.files.getlist("files")
    if not files or files[0].filename == "":
        logger.warning("API - Upload request received with empty files selection.")
        return jsonify({"error": "No files selected for upload"}), 400
        
    logger.info(f"API - Uploading {len(files)} files to workspace: {workspace_id}")
    
    upload_dir = get_workspace_upload_dir(workspace_id, settings.get_upload_dir)
    ingested_docs = []
    errors = []
    
    for file in files:
        filename = file.filename
        if not filename:
            continue
            
        if not is_allowed_file(filename):
            errors.append(f"File {filename} is not a valid PDF.")
            logger.warning(f"API - Rejected invalid file format: {filename}")
            continue
            
        # Secure name and build path
        secured_name = secure_filename(filename)
        save_path = os.path.join(upload_dir, secured_name)
        
        try:
            file.save(save_path)
            
            # Ingest PDF content
            doc_id = ingestion_service.ingest_pdf(workspace_id, filename, save_path)
            
            with get_db() as conn:
                row = conn.execute(
                    "SELECT id, filename, total_pages FROM documents WHERE id = ?",
                    (doc_id,)
                ).fetchone()
                if row:
                    ingested_docs.append({
                        "id": row["id"],
                        "filename": row["filename"],
                        "total_pages": row["total_pages"]
                    })
        except Exception as e:
            logger.error(f"API - Failed to ingest file {filename}: {str(e)}")
            errors.append(f"Failed to ingest file {filename}: {str(e)}")
            
    if errors and not ingested_docs:
        return jsonify({"error": "; ".join(errors)}), 500
        
    return jsonify({
        "message": "Ingestion completed.",
        "documents": ingested_docs,
        "warnings": errors
    }), 200

@upload_bp.route("/documents", methods=["GET"])
def get_documents():
    """Returns a list of all documents uploaded to the workspace."""
    workspace_id = request.args.get("workspace_id")
    if not workspace_id:
        return jsonify({"error": "workspace_id is required"}), 400
        
    if not workspace_service.workspace_exists(workspace_id):
        return jsonify({"error": "Workspace does not exist"}), 404
        
    try:
        with get_db() as conn:
            cursor = conn.execute(
                "SELECT id, filename, upload_time, total_pages FROM documents WHERE workspace_id = ? ORDER BY id DESC",
                (workspace_id,)
            )
            rows = cursor.fetchall()
            docs = [
                {
                    "id": row["id"],
                    "filename": row["filename"],
                    "upload_time": row["upload_time"],
                    "total_pages": row["total_pages"]
                }
                for row in rows
            ]
            return jsonify({"documents": docs}), 200
    except Exception as e:
        logger.error(f"API - Failed to retrieve documents for workspace {workspace_id}: {str(e)}")
        return jsonify({"error": "Failed to retrieve documents"}), 500
