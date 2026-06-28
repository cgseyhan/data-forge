from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel

class QAResultBase(BaseModel):
    record_id: str
    qa_type: str
    status: str
    score: float = 0.0
    issues_json: Optional[List[Dict[str, Any]]] = None

class QAResultCreate(QAResultBase):
    pass

class QAResultResponse(QAResultBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True
