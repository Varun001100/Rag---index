import os
import shutil
from pathlib import Path
from utils.logger import logger

def is_allowed_file(filename: str) -> bool:
    """Check if the file has a .pdf extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() == "pdf"

def get_workspace_upload_dir(workspace_id: str, upload_base_dir: str) -> Path:
    """Get the upload directory for a specific workspace, creating it if necessary."""
    path = Path(upload_base_dir) / workspace_id
    path.mkdir(parents=True, exist_ok=True)
    return path

def delete_workspace_files(workspace_id: str, upload_base_dir: str) -> None:
    """Delete all files and the directory associated with a specific workspace."""
    path = Path(upload_base_dir) / workspace_id
    if path.exists() and path.is_dir():
        try:
            shutil.rmtree(path)
            logger.info(f"Deleted file folder for workspace: {workspace_id}")
        except Exception as e:
            logger.error(f"Failed to delete files for workspace {workspace_id}: {str(e)}")
