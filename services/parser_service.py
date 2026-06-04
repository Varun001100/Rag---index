from pathlib import Path
from typing import Dict
import pdfplumber
import PyPDF2
from utils.logger import logger

class ParserService:
    @staticmethod
    def extract_text(file_path: str) -> Dict[int, str]:
        """
        Extracts text from a PDF file page by page.
        Returns a dictionary mapping page numbers (1-indexed) to text content.
        """
        logger.info(f"Starting text extraction for file: {file_path}")
        pages_content = {}
        
        # Primary method: pdfplumber
        try:
            with pdfplumber.open(file_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    page_num = i + 1
                    try:
                        text = page.extract_text()
                        if text:
                            pages_content[page_num] = text
                    except Exception as page_err:
                        logger.warning(f"pdfplumber failed on page {page_num}: {str(page_err)}. Will attempt PyPDF2 fallback.")
        except Exception as e:
            logger.error(f"pdfplumber failed to open {file_path}: {str(e)}. Attempting PyPDF2 fallback for whole document.")

        # Fallback method: PyPDF2
        try:
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                num_pages = len(reader.pages)
                for page_num in range(1, num_pages + 1):
                    # If this page text is empty or missing, retrieve using PyPDF2
                    if page_num not in pages_content or not pages_content[page_num].strip():
                        try:
                            page = reader.pages[page_num - 1]
                            text = page.extract_text()
                            if text:
                                pages_content[page_num] = text
                        except Exception as page_err:
                            logger.error(f"PyPDF2 fallback also failed on page {page_num}: {str(page_err)}")
        except Exception as e:
            logger.error(f"PyPDF2 fallback failed to read {file_path}: {str(e)}")

        # Post-process and sanitize text slightly
        cleaned_pages = {}
        for page_num, text in pages_content.items():
            if text:
                lines = [line.strip() for line in text.splitlines()]
                cleaned_text = "\n".join(line for line in lines if line)
                cleaned_pages[page_num] = cleaned_text
                
        logger.info(f"Completed text extraction for {file_path}. Extracted {len(cleaned_pages)} pages.")
        return cleaned_pages
