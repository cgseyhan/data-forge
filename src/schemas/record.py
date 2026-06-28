from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

class RecordBase(BaseModel):
    source_id: Optional[str] = None
    source_url: Optional[str] = None
    raw_content: Optional[str] = None
    content_hash: Optional[str] = None
    extracted_json: Optional[Dict[str, Any]] = None
    schema_version: Optional[str] = None
    pipeline_name: Optional[str] = None
    status: str = "INGESTED"
    error_reason: Optional[str] = None
    retry_count: int = 0

class RecordCreate(RecordBase):
    pass

class RecordResponse(RecordBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
