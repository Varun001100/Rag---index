import sqlite3
import os
from contextlib import contextmanager
from pathlib import Path
from config.settings import settings
from utils.logger import logger

def get_db_connection():
    """Establish and return a sqlite3 connection with Row factory and foreign keys enabled."""
    db_path = settings.get_db_path
    db_dir = Path(db_path).parent
    db_dir.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

@contextmanager
def get_db():
    """Context manager for managing transactions and connections."""
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database error transaction rollback: {str(e)}")
        raise e
    finally:
        conn.close()

def init_db():
    """Load schema.sql and initialize the database tables."""
    schema_path = settings.base_dir / "database" / "schema.sql"
    if not schema_path.exists():
        logger.error(f"schema.sql not found at {schema_path}")
        raise FileNotFoundError(f"schema.sql not found at {schema_path}")
        
    with schema_path.open("r", encoding="utf-8") as f:
        schema_sql = f.read()
        
    with get_db() as conn:
        conn.executescript(schema_sql)
    logger.info("Database initialized successfully.")
