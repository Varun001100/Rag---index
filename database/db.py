import sqlite3
from contextlib import contextmanager

from config.settings import Config


DATABASE_PATH = Config.DATABASE_PATH


@contextmanager
def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")

    try:
        yield conn
        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def initialize_database():
    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            document_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY(session_id)
            REFERENCES sessions(session_id)
            ON DELETE CASCADE
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS parent_chunks (
            parent_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            document_id TEXT NOT NULL,
            page_number INTEGER,
            chunk_text TEXT NOT NULL,

            FOREIGN KEY(session_id)
            REFERENCES sessions(session_id)
            ON DELETE CASCADE,

            FOREIGN KEY(document_id)
            REFERENCES documents(document_id)
            ON DELETE CASCADE
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY(session_id)
            REFERENCES sessions(session_id)
            ON DELETE CASCADE
        )
        """)

        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_documents_session
        ON documents(session_id)
        """)

        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_parent_session
        ON parent_chunks(session_id)
        """)

        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_parent_document
        ON parent_chunks(document_id)
        """)

        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_conversation_session
        ON conversations(session_id)
        """)

def execute_query(query, params=()):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)

        return cursor.fetchall()


def execute_insert(query, params=()):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)

        return cursor.lastrowid