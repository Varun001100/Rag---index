import time
import threading
from database.db import get_db
from services.workspace_service import WorkspaceService
from config.settings import settings
from utils.logger import logger

class CleanupService:
    def __init__(self):
        self.workspace_service = WorkspaceService()

    def cleanup_expired_workspaces(self) -> int:
        """
        Queries the database for workspaces that have expired (last_accessed > 24 hours)
        and deletes all associated resources (vectors, files, DB rows).
        
        Returns:
            Number of successfully cleaned workspaces.
        """
        logger.info("Executing periodic sweep for expired workspaces.")
        hours = settings.WORKSPACE_EXPIRATION_HOURS
        expired_workspaces = []
        
        try:
            with get_db() as conn:
                # Retrieve workspaces last_accessed older than X hours in UTC
                query = "SELECT workspace_id FROM workspaces WHERE datetime(last_accessed) < datetime('now', ?)"
                cursor = conn.execute(query, (f"-{hours} hours",))
                rows = cursor.fetchall()
                expired_workspaces = [row["workspace_id"] for row in rows]
        except Exception as e:
            logger.error(f"Failed to query database for expired workspaces: {str(e)}")
            return 0
            
        if not expired_workspaces:
            logger.info("Sweep complete. No expired workspaces found.")
            return 0
            
        logger.info(f"Sweep found {len(expired_workspaces)} expired workspaces: {expired_workspaces}")
        
        cleaned_count = 0
        for ws_id in expired_workspaces:
            try:
                self.workspace_service.delete_workspace(ws_id)
                cleaned_count += 1
            except Exception as e:
                logger.error(f"Failed to clean up expired workspace {ws_id}: {str(e)}")
                
        logger.info(f"Sweep finished. Successfully purged {cleaned_count} workspaces.")
        return cleaned_count

    def run_scheduler(self, interval_seconds: int = 3600) -> None:
        """Loop running the workspace cleanup sweep on the defined interval."""
        logger.info(f"Starting cleanup scheduler loop (interval: {interval_seconds}s).")
        while True:
            try:
                self.cleanup_expired_workspaces()
            except Exception as e:
                logger.error(f"Error in cleanup scheduler loop: {str(e)}")
            time.sleep(interval_seconds)

def start_cleanup_scheduler(interval_seconds: int = 3600) -> threading.Thread:
    """
    Spawns and starts a daemon thread to run the workspace cleanup loop.
    
    Args:
        interval_seconds: Frequency of the sweeps in seconds. Defaults to 3600 (hourly).
        
    Returns:
        The running threading.Thread object.
    """
    service = CleanupService()
    thread = threading.Thread(
        target=service.run_scheduler,
        args=(interval_seconds,),
        daemon=True,
        name="workspace-cleanup-thread"
    )
    thread.start()
    return thread
