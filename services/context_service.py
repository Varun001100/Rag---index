from database.db import get_db
from utils.logger import logger
from typing import List, Dict, Any

class ContextService:
    @staticmethod
    def build_context(workspace_id: str, reranked_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Retrieves parent chunks from SQLite for top-scoring child chunks,
        removes duplicates, aggregates text, and compiles metadata for citations.
        
        Args:
            workspace_id: The active workspace ID filter.
            reranked_chunks: List of reranked child chunk dictionaries.
            
        Returns:
            Dict containing 'final_context' (str) and 'citations_raw' (list of dicts).
        """
        if not reranked_chunks:
            return {"final_context": "", "citations_raw": []}
            
        logger.info(f"Building context for {len(reranked_chunks)} reranked chunks in workspace: {workspace_id}")
        
        # Track unique parent IDs and maintain relevance order
        parent_ids = []
        parent_metadata_map = {}
        
        for chunk in reranked_chunks:
            p_id = chunk["parent_id"]
            if p_id not in parent_metadata_map:
                parent_ids.append(p_id)
                parent_metadata_map[p_id] = {
                    "filename": chunk["filename"],
                    "page_number": chunk["page_number"]
                }
                
        if not parent_ids:
            return {"final_context": "", "citations_raw": []}
            
        parent_chunks_db = {}
        try:
            with get_db() as conn:
                placeholders = ",".join(["?"] * len(parent_ids))
                query = f"""
                    SELECT parent_id, page_number, content 
                    FROM parent_chunks 
                    WHERE workspace_id = ? AND parent_id IN ({placeholders})
                """
                params = [workspace_id] + parent_ids
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()
                
                for row in rows:
                    parent_chunks_db[row["parent_id"]] = {
                        "content": row["content"],
                        "page_number": row["page_number"]
                    }
        except Exception as e:
            logger.error(f"Failed to retrieve parent chunks from database: {str(e)}")
            raise e
            
        final_context_parts = []
        citations_data = []
        
        for p_id in parent_ids:
            if p_id in parent_chunks_db:
                p_data = parent_chunks_db[p_id]
                c_meta = parent_metadata_map[p_id]
                
                final_context_parts.append(p_data["content"])
                citations_data.append({
                    "filename": c_meta["filename"],
                    "page_number": p_data["page_number"]
                })
                
        final_context = "\n\n---\n\n".join(final_context_parts)
        
        return {
            "final_context": final_context,
            "citations_raw": citations_data
        }
