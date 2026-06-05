import uuid
import re


class ChunkingService:

    PARENT_CHUNK_SIZE = 1500

    CHILD_CHUNK_SIZE = 400

    CHILD_OVERLAP = 100

    @staticmethod
    def clean_text(text):

        text = re.sub(
            r"\s+",
            " ",
            text
        )

        return text.strip()

    @staticmethod
    def split_text(
        text,
        chunk_size,
        overlap
    ):

        chunks = []

        start = 0

        while start < len(text):

            end = start + chunk_size

            chunk = text[start:end]

            chunks.append(chunk)

            start += (
                chunk_size -
                overlap
            )

        return chunks

    @staticmethod
    def create_parent_child_chunks(
        pages
    ):

        parent_chunks = []

        child_chunks = []

        for page in pages:

            page_number = page[
                "page_number"
            ]

            text = (
                ChunkingService
                .clean_text(
                    page["text"]
                )
            )

            parent_parts = (
                ChunkingService
                .split_text(
                    text,
                    chunk_size=1500,
                    overlap=0
                )
            )

            for parent_text in parent_parts:

                parent_id = (
                    f"parent_"
                    f"{uuid.uuid4().hex}"
                )

                parent_chunks.append({
                    "parent_id":
                        parent_id,

                    "page_number":
                        page_number,

                    "text":
                        parent_text
                })

                child_parts = (
                    ChunkingService
                    .split_text(
                        parent_text,
                        chunk_size=400,
                        overlap=100
                    )
                )

                for index, child_text in enumerate(
                    child_parts,
                    start=1
                ):

                    child_id = (
                        f"child_"
                        f"{uuid.uuid4().hex}"
                    )

                    child_chunks.append({
                        "child_id":
                            child_id,

                        "parent_id":
                            parent_id,

                        "page_number":
                            page_number,

                        "child_index":
                            index,

                        "text":
                            child_text
                    })

        return {
            "parents":
                parent_chunks,

            "children":
                child_chunks
        }