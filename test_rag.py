import os
from database.db import initialize_database, execute_query
from services.retrieval_service import RetrievalService
from services.reranker_service import RerankerService
from services.memory_service import MemoryService
from services.citation_service import CitationService
from services.llm_service import LlmService


def test_pipeline():
    print("=== Starting End-to-End RAG Pipeline Integration Test ===")

    # Initialize DB tables
    initialize_database()

    session_id = "sess_test"
    query = "What is the limitation of liability?"

    # Check if we have parent chunks for this session
    parent_count = execute_query(
        "SELECT COUNT(*) as count FROM parent_chunks WHERE session_id = ?",
        (session_id,)
    )[0]["count"]

    print(f"Database setup check: Found {parent_count} parent chunks for session '{session_id}'")

    if parent_count == 0:
        print("WARNING: No parent chunks found in database for session 'sess_test'.")
        print("Please ensure that you run a test upload first or that ingest_document ran successfully.")
        return

    # 1. Test Memory Service
    print("\n--- Testing Memory Service ---")
    history = MemoryService.get_history(session_id, limit=5)
    print(f"Retrieved {len(history)} previous conversation turns.")

    # 2. Test Retrieval Service (Pinecone + SQLite)
    print("\n--- Testing Retrieval Service ---")
    try:
        retrieved_chunks = RetrievalService.retrieve(query, session_id, top_k=10)
        print(f"Retrieved {len(retrieved_chunks)} parent chunks from vector search.")
        for idx, chunk in enumerate(retrieved_chunks[:3], start=1):
            print(f"  [{idx}] File: {chunk['filename']}, Page: {chunk['page_number']}")
            print(f"      Text: {chunk['text'][:120]}...")
    except Exception as e:
        print(f"ERROR in Retrieval Service: {e}")
        return

    # 3. Test Reranker Service
    print("\n--- Testing Reranker Service ---")
    try:
        reranked_chunks = RerankerService.rerank(query, retrieved_chunks, top_n=3)
        print(f"Reranked to {len(reranked_chunks)} top chunks.")
        for idx, chunk in enumerate(reranked_chunks, start=1):
            print(f"  [{idx}] Score: {chunk['score']:.4f} | File: {chunk['filename']}, Page: {chunk['page_number']}")
            print(f"      Text: {chunk['text'][:120]}...")
    except Exception as e:
        print(f"ERROR in Reranker Service: {e}")
        return

    # 4. Test Citation Service
    print("\n--- Testing Citation Service ---")
    citations = CitationService.get_citations(reranked_chunks)
    print("Compiled citations:")
    for cit in citations:
        print(f"  - {cit['filename']} (Page {cit['page_number']})")

    # 5. Test LLM Service (catch key/network errors)
    print("\n--- Testing LLM Service ---")
    print("Generating answer via Gemini model...")
    answer = LlmService.generate_answer(query, reranked_chunks, history)
    print("\nGemini Response:")
    print(answer)

    # 6. Save response back to memory if successful or partial
    if answer and not answer.startswith("Error:"):
        MemoryService.add_message(session_id, query, answer)
        print("\nTurn saved to conversation history.")


if __name__ == "__main__":
    test_pipeline()
