import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # =========================
    # Flask
    # =========================
    SECRET_KEY = os.getenv("SECRET_KEY")
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "True") == "True"

    # =========================
    # Database
    # =========================
    DATABASE_PATH = os.getenv(
        "DATABASE_PATH",
        "data/rag.db"
    )

    # =========================
    # Uploads
    # =========================
    UPLOAD_FOLDER = os.getenv(
        "UPLOAD_FOLDER",
        "uploads"
    )

    MAX_CONTENT_LENGTH = int(
        os.getenv(
            "MAX_CONTENT_LENGTH",
            52428800
        )
    )


    # =========================
    # Pinecone
    # =========================
    PINECONE_API_KEY = os.getenv(
        "PINECONE_API_KEY"
    )

    PINECONE_INDEX_NAME = os.getenv(
        "PINECONE_INDEX_NAME"
    )

    # =========================
    # Gemini
    # =========================
    GEMINI_API_KEY = os.getenv(
        "GEMINI_API_KEY"
    )

    GEMINI_API_KEYS = os.getenv(
        "GEMINI_API_KEYS"
    )

    GEMINI_MODEL = os.getenv(
        "GEMINI_MODEL",
        "gemini-2.5-flash"
    )

    GEMINI_MODELS = os.getenv(
        "GEMINI_MODELS"
    )

    # =========================
    # Models
    # =========================
    EMBEDDING_MODEL = os.getenv(
        "EMBEDDING_MODEL",
        "BAAI/bge-small-en-v1.5"
    )

    RERANKER_MODEL = os.getenv(
        "RERANKER_MODEL",
        "cross-encoder/ms-marco-MiniLM-L-6-v2"
    )

    # =========================
    # Retrieval
    # =========================
    TOP_K_RETRIEVAL = int(
        os.getenv(
            "TOP_K_RETRIEVAL",
            20
        )
    )

    TOP_K_RERANK = int(
        os.getenv(
            "TOP_K_RERANK",
            5
        )
    )