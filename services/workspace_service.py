import uuid
from database.db import get_db
from models.workspace_model import Workspace
from utils.logger import logger
from utils.file_utils import delete_workspace_files
from services.pinecone_service import PineconeService
from config.settings import settings

class WorkspaceService:
    def __init__(self):
        self.pinecone_service = PineconeService()

    @staticmethod
    def create_workspace() -> str:
        """Generates and inserts a new unique workspace ID in the format 'ws_xxxxxx'."""
        ws_id = f"ws_{uuid.uuid4().hex[:6]}"
        logger.info(f"Creating new workspace record: {ws_id}")
        
        try:
            with get_db() as conn:
                conn.execute(
                    "INSERT INTO workspaces (workspace_id) VALUES (?)",
                    (ws_id,)
                )
            return ws_id
        except Exception as e:
            logger.error(f"Failed to create workspace in database: {str(e)}")
            raise e

    @staticmethod
    def update_last_accessed(workspace_id: str) -> None:
        """Updates the workspace last_accessed column to current timestamp."""
        logger.info(f"Updating last_accessed timestamp for workspace: {workspace_id}")
        try:
            with get_db() as conn:
                conn.execute(
                    "UPDATE workspaces SET last_accessed = CURRENT_TIMESTAMP WHERE workspace_id = ?",
                    (workspace_id,)
                )
        except Exception as e:
            logger.error(f"Failed to update workspace last_accessed: {str(e)}")
            raise e

    @staticmethod
    def workspace_exists(workspace_id: str) -> bool:
        """Returns True if the workspace exists in database, False otherwise."""
        try:
            with get_db() as conn:
                cursor = conn.execute(
                    "SELECT 1 FROM workspaces WHERE workspace_id = ?",
                    (workspace_id,)
                )
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Failed to check workspace existence: {str(e)}")
            return False

    def delete_workspace(self, workspace_id: str) -> None:
        """
        Deletes a workspace. Clears vectors in Pinecone, files on disk,
        and cascades deletion across documents, parent chunks, and chat history in database.
        """
        logger.info(f"Initiating deletion sequence for workspace: {workspace_id}")
        
        # 1. Delete Pinecone vectors
        try:
            self.pinecone_service.delete_workspace_vectors(workspace_id)
        except Exception as e:
            logger.warning(f"Error purging Pinecone vectors during workspace {workspace_id} deletion: {str(e)}")
            
        # 2. Delete files from disk
        delete_workspace_files(workspace_id, settings.get_upload_dir)
        
        # 3. Delete SQLite workspace record (CASCADE removes related documents, chunks, conversations)
        try:
            with get_db() as conn:
                conn.execute(
                    "DELETE FROM workspaces WHERE workspace_id = ?",
                    (workspace_id,)
                )
            logger.info(f"Workspace {workspace_id} fully deleted.")
        except Exception as e:
            logger.error(f"Failed to delete workspace {workspace_id} from SQLite: {str(e)}")
            raise e
