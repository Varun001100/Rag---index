import pdfplumber
from PyPDF2 import PdfReader


class ParserService:

    @staticmethod
    def extract_text_pdfplumber(pdf_path):

        pages = []

        with pdfplumber.open(pdf_path) as pdf:

            for page_number, page in enumerate(
                pdf.pages,
                start=1
            ):

                text = page.extract_text()

                if not text:
                    continue

                text = text.strip()

                if not text:
                    continue

                pages.append({
                    "page_number": page_number,
                    "text": text
                })

        return pages

    @staticmethod
    def extract_text_pypdf2(pdf_path):

        pages = []

        reader = PdfReader(pdf_path)

        for page_number, page in enumerate(
            reader.pages,
            start=1
        ):

            text = page.extract_text()

            if not text:
                continue

            text = text.strip()

            if not text:
                continue

            pages.append({
                "page_number": page_number,
                "text": text
            })

        return pages

    @staticmethod
    def extract_text(pdf_path):

        try:

            pages = (
                ParserService
                .extract_text_pdfplumber(
                    pdf_path
                )
            )

            if pages:
                return pages

        except Exception as e:

            print(
                f"pdfplumber failed: {e}"
            )

        try:

            pages = (
                ParserService
                .extract_text_pypdf2(
                    pdf_path
                )
            )

            return pages

        except Exception as e:

            print(
                f"PyPDF2 failed: {e}"
            )

            return []