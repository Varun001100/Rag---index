from services.embedding_service import EmbeddingService
from services.pinecone_service import PineconeService
from services.reranker_service import RerankerService
from services.context_service import ContextService
from services.citation_service import CitationService
from services.llm_service import LLMService
from services.memory_service import MemoryService
from services.workspace_service import WorkspaceService
from utils.logger import logger
from typing import Dict, Any

class RetrievalService:
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.pinecone_service = PineconeService()
        self.reranker_service = RerankerService()
        self.llm_service = LLMService()

    def query_workspace(self, workspace_id: str, question: str) -> Dict[str, Any]:
        """
        Orchestrates the entire query-retrieval-reranking-generation pipeline.
        
        Args:
            workspace_id: The active workspace ID context.
            question: The user's query text.
            
        Returns:
            Dict containing the 'answer' string and 'citations' formatted output string.
        """
        logger.info(f"Retrieval Query Execution started for workspace {workspace_id} with query: '{question}'")
        
        # 1. Keep workspace active
        WorkspaceService.update_last_accessed(workspace_id)
        
        # 2. Get recent chat turns (limit to 5)
        history = MemoryService.get_recent_history(workspace_id, limit=5)
        
        # 3. Generate query vector
        query_vector = self.embedding_service.embed_query(question)
        
        # 4. Search Pinecone for top 20 child chunks
        child_hits = []
        try:
            child_hits = self.pinecone_service.search_vectors(query_vector, workspace_id, top_k=20)
        except Exception as e:
            logger.error(f"Pinecone search execution encountered an error: {str(e)}")
            
        # If no child chunks are found in the index
        if not child_hits:
            logger.info("No chunks matched the search vector. Returning context fallback response.")
            fallback_answer = "I could not find that information in the uploaded documents."
            MemoryService.save_message(workspace_id, question, fallback_answer)
            return {
                "answer": fallback_answer,
                "citations": ""
            }
            
        # 5. Rerank top 20 hits to select top 5
        reranked_chunks = self.reranker_service.rerank(question, child_hits, top_n=5)
        
        # 6. Retrieve matching parents and build aggregated context
        context_data = ContextService.build_context(workspace_id, reranked_chunks)
        final_context = context_data["final_context"]
        citations_raw = context_data["citations_raw"]
        
        # 7. Format clean citations
        citations_str = CitationService.generate_citations(citations_raw)
        
        # 8. Invoke LLM generation
        answer = self.llm_service.generate_answer(question, final_context, history)
        
        # 9. Save question-answer turn in memory
        MemoryService.save_message(workspace_id, question, answer)
        
        return {
            "answer": answer,
            "citations": citations_str
        }
