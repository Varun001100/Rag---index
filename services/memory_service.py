from database.db import get_db
from models.conversation_model import Conversation
from utils.logger import logger
from typing import List

class MemoryService:
    @staticmethod
    def save_message(workspace_id: str, question: str, answer: str) -> None:
        """Saves a chat history entry (question and answer) for the workspace."""
        logger.info(f"Saving conversation history for workspace: {workspace_id}")
        try:
            with get_db() as conn:
                conn.execute(
                    "INSERT INTO conversations (workspace_id, question, answer) VALUES (?, ?, ?)",
                    (workspace_id, question, answer)
                )
        except Exception as e:
            logger.error(f"Failed to save conversation entry to database: {str(e)}")
            raise e

    @staticmethod
    def get_recent_history(workspace_id: str, limit: int = 5) -> List[Conversation]:
        """
        Retrieves the last N conversations for a workspace, ordered chronologically.
        
        Args:
            workspace_id: The active workspace ID filter.
            limit: Maximum number of chat turns to load.
            
        Returns:
            List of Conversation Pydantic models.
        """
        logger.info(f"Retrieving recent chat history for workspace: {workspace_id} (limit: {limit})")
        try:
            with get_db() as conn:
                cursor = conn.execute(
                    """
                    SELECT id, workspace_id, question, answer, created_at 
                    FROM conversations 
                    WHERE workspace_id = ? 
                    ORDER BY id DESC LIMIT ?
                    """,
                    (workspace_id, limit)
                )
                rows = cursor.fetchall()
                # Reverse list to ensure older messages appear first in the prompt
                return [Conversation.model_validate(row) for row in reversed(rows)]
        except Exception as e:
            logger.error(f"Failed to load conversation history from database: {str(e)}")
            raise e
