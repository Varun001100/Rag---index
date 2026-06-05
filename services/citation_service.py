class CitationService:

    @staticmethod
    def get_citations(chunks):
        """
        Extracts unique citations (filename, page_number) from the retrieved/reranked parent chunks.
        
        Args:
            chunks (list): A list of chunk dictionaries with 'filename' and 'page_number' keys.
            
        Returns:
            list: A list of unique dictionaries, e.g., [{"filename": "ML.pdf", "page_number": 5}]
        """
        citations = []
        seen = set()

        for chunk in chunks:
            filename = chunk.get("filename")
            page_number = chunk.get("page_number")
            
            if filename and page_number is not None:
                key = (filename, page_number)
                if key not in seen:
                    seen.add(key)
                    citations.append({
                        "filename": filename,
                        "page_number": page_number
                    })

        return citations
