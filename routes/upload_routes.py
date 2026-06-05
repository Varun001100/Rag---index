import os
import uuid

from flask import (
    Blueprint,
    request,
    jsonify
)

from services.session_service import SessionService
from config.settings import Config
from services.ingestion_service import IngestionService
from services.pinecone_service import PineconeService
from database.db import execute_query, execute_insert

upload_bp = Blueprint(
    "upload",
    __name__,
    url_prefix="/api/upload"
)


ALLOWED_EXTENSIONS = {"pdf"}


def allowed_file(filename):
    return (
        "." in filename and
        filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


@upload_bp.route(
    "/create-session",
    methods=["POST"]
)
def create_session():

    session_id = SessionService.create_session()

    session_folder = os.path.join(
        Config.UPLOAD_FOLDER,
        session_id
    )

    os.makedirs(
        session_folder,
        exist_ok=True
    )

    return jsonify({
        "success": True,
        "session_id": session_id
    }), 201


@upload_bp.route(
    "/pdfs",
    methods=["POST"]
)
def upload_pdfs():

    session_id = request.form.get(
        "session_id"
    )

    if not session_id:
        return jsonify({
            "success": False,
            "message": "session_id required"
        }), 400

    if not SessionService.session_exists(
        session_id
    ):
        return jsonify({
            "success": False,
            "message": "Invalid session"
        }), 404

    files = request.files.getlist(
        "files"
    )

    if not files:
        return jsonify({
            "success": False,
            "message": "No files uploaded"
        }), 400

    session_folder = os.path.join(
        Config.UPLOAD_FOLDER,
        session_id
    )

    os.makedirs(
        session_folder,
        exist_ok=True
    )

    uploaded_files = []

    for file in files:

        if not file.filename:
            continue

        if not allowed_file(
            file.filename
        ):
            continue

        document_id = (
            f"doc_{uuid.uuid4().hex[:12]}"
        )

        filename = file.filename

        saved_filename = (
            f"{document_id}_{filename}"
        )

        file_path = os.path.join(
            session_folder,
            saved_filename
        )

        file.save(file_path)

        ingestion_result = (
            IngestionService
            .ingest_document(
                session_id=session_id,
                document_id=document_id,
                filename=filename,
                file_path=file_path
            )
        )

        uploaded_files.append({
            "document_id": document_id,
            "filename": filename,
            "ingestion": ingestion_result
        })

    return jsonify({
        "success": True,
        "session_id": session_id,
        "uploaded_count": len(
            uploaded_files
        ),
        "documents": uploaded_files
    }), 201


@upload_bp.route(
    "/status/<document_id>",
    methods=["GET"]
)
def get_ingestion_status(document_id):
    """
    Returns the background ingestion status of a document.
    """
    status = IngestionService.get_status(document_id)
    return jsonify(status), 200


@upload_bp.route("/documents/<session_id>", methods=["GET"])
def get_session_documents(session_id):
    """
    Retrieves all ingested documents for a given session.
    """
    if not SessionService.session_exists(session_id):
        return jsonify({
            "success": False,
            "message": "Invalid session"
        }), 404

    try:
        results = execute_query(
            """
            SELECT document_id, filename, file_path
            FROM documents
            WHERE session_id = ?
            """,
            (session_id,)
        )

        documents = []
        for r in results:
            doc_id = r["document_id"]
            status = IngestionService.get_status(doc_id)
            documents.append({
                "document_id": doc_id,
                "filename": r["filename"],
                "file_path": r["file_path"],
                "ingestion": status
            })

        return jsonify({
            "success": True,
            "documents": documents
        }), 200
    except Exception as e:
        print(f"Error listing documents for session {session_id}: {e}")
        return jsonify({
            "success": False,
            "message": f"Failed to list documents: {str(e)}"
        }), 500


@upload_bp.route("/document/<document_id>", methods=["DELETE"])
def delete_document(document_id):
    """
    Clears a single document: deletes vectors from Pinecone, deletes records from SQLite,
    and removes the physical file from local uploads folder.
    """
    try:
        # 1. Fetch document metadata
        results = execute_query(
            """
            SELECT session_id, file_path, filename
            FROM documents
            WHERE document_id = ?
            """,
            (document_id,)
        )
        if not results:
            return jsonify({
                "success": False,
                "message": "Document not found"
            }), 404

        record = results[0]
        session_id = record["session_id"]
        file_path = record["file_path"]

        # 2. Delete vectors from Pinecone
        PineconeService.delete_document_vectors(document_id)

        # 3. Delete database record (cascade deletes parent chunks)
        execute_insert(
            """
            DELETE FROM documents
            WHERE document_id = ?
            """,
            (document_id,)
        )

        # 4. Remove physical file
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as fe:
                print(f"Warning: Failed to delete physical file {file_path}: {fe}")

        return jsonify({
            "success": True,
            "message": f"Document '{record['filename']}' deleted successfully."
        }), 200

    except Exception as e:
        print(f"Error deleting document {document_id}: {e}")
        return jsonify({
            "success": False,
            "message": f"Failed to delete document: {str(e)}"
        }), 500