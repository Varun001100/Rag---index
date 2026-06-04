from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional

class Conversation(BaseModel):
    id: Optional[int] = None
    workspace_id: str
    question: str
    answer: str
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
