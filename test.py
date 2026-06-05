from services.ingestion_service import IngestionService

result = IngestionService.ingest_document(
    session_id="sess_test",
    document_id="doc_test",
    filename="COI.pdf",
    file_path=r"uploads\sess_253336f8\doc_8b391de5437c_COI.pdf"
)

print(result)