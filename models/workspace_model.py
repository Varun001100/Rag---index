from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional

class Workspace(BaseModel):
    id: Optional[int] = None
    workspace_id: str
    created_at: Optional[datetime] = None
    last_accessed: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
