import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    PORT: int = Field(default=5000)
    FLASK_ENV: str = Field(default="development")
    
    DATABASE_PATH: str = Field(default="database/rag.db")
    UPLOAD_DIR: str = Field(default="uploads")
    
    PINECONE_API_KEY: str = Field(default="")
    PINECONE_INDEX_NAME: str = Field(default="")
    GEMINI_API_KEY: str = Field(default="")
    
    CHUNK_SIZE: int = Field(default=1000)
    CHUNK_OVERLAP: int = Field(default=200)
    WORKSPACE_EXPIRATION_HOURS: int = Field(default=24)
    
    @property
    def base_dir(self) -> Path:
        return Path(__file__).resolve().parent.parent
        
    @property
    def get_db_path(self) -> str:
        path = Path(self.DATABASE_PATH)
        if path.is_absolute():
            return str(path)
        return str(self.base_dir / path)
        
    @property
    def get_upload_dir(self) -> str:
        path = Path(self.UPLOAD_DIR)
        if path.is_absolute():
            return str(path)
        return str(self.base_dir / path)

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
