from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional

class Document(BaseModel):
    id: Optional[int] = None
    workspace_id: str
    filename: str
    file_path: str
    upload_time: Optional[datetime] = None
    total_pages: int

    model_config = ConfigDict(from_attributes=True)
