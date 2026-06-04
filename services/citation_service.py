from typing import List, Dict, Any
from utils.logger import logger

class CitationService:
    @staticmethod
    def generate_citations(citations_raw: List[Dict[str, Any]]) -> str:
        """
        Deduplicates raw citation data and builds a clean string citation output.
        
        Example Output:
            Sources:
            * MachineLearning.pdf (Page 12)
            * DeepLearning.pdf (Page 5)
        """
        logger.info("Generating formatted citations from raw metadata.")
        if not citations_raw:
            return ""
            
        unique_citations = []
        seen = set()
        
        for citation in citations_raw:
            filename = citation.get("filename", "Unknown Document")
            page_number = citation.get("page_number", 0)
            key = (filename, page_number)
            if key not in seen:
                seen.add(key)
                unique_citations.append(key)
                
        # Sort by filename (alphabetically) and page number (numerically)
        unique_citations.sort(key=lambda x: (x[0], x[1]))
        
        citation_lines = []
        for filename, page_number in unique_citations:
            citation_lines.append(f"* {filename} (Page {page_number})")
            
        if not citation_lines:
            return ""
            
        citations_str = "Sources:\n\n" + "\n".join(citation_lines)
        return citations_str
