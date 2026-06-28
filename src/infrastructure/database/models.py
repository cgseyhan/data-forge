import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, JSON, Text, Float, Integer, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.postgresql import JSONB

Base = declarative_base()

class Record(Base):
    """
    Generic Record model for DataForge.
    Follows idempotency and tracks exact pipeline states.
    """
    __tablename__ = "records"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    source_id = Column(String, index=True, nullable=True)
    source_url = Column(String, index=True, nullable=True)
    
    raw_content = Column(Text, nullable=True)
    content_hash = Column(String, index=True, nullable=True) # For idempotency
    
    extracted_json = Column(JSONB, nullable=True)
    schema_version = Column(String, nullable=True)
    pipeline_name = Column(String, index=True, nullable=True)
    
    status = Column(String, index=True, default="INGESTED")
    # Statuses: INGESTED, SCRAPED, EXTRACTION_PENDING, EXTRACTED, QA_PENDING, QA_PASSED, QA_REVIEW, QA_FAILED, VECTORIZED, FAILED
    
    error_reason = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    qa_results = relationship("QAResult", back_populates="record", cascade="all, delete-orphan")
    vector_metas = relationship("VectorMeta", back_populates="record", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Record(id={self.id}, status={self.status}, hash={self.content_hash})>"


class QAResult(Base):
    """
    Tracks results of various QA activities on a specific record.
    """
    __tablename__ = "qa_results"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    record_id = Column(String, ForeignKey("records.id"), index=True)
    
    qa_type = Column(String, index=True) # e.g., 'deterministic', 'llm_judge'
    status = Column(String, index=True) # e.g., 'PASSED', 'FAILED', 'NEEDS_REVIEW'
    score = Column(Float, default=0.0)
    
    issues_json = Column(JSONB, nullable=True) # Details of what failed
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    record = relationship("Record", back_populates="qa_results")


class VectorMeta(Base):
    """
    References the vector representation stored in an external DB (like pgvector or Qdrant).
    """
    __tablename__ = "vector_metas"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    record_id = Column(String, ForeignKey("records.id"), index=True)
    
    vector_backend = Column(String, default="pgvector")
    collection_name = Column(String, index=True)
    external_vector_id = Column(String, index=True, nullable=True)
    
    embedding_model = Column(String)
    content_hash = Column(String, index=True) # Hash of the text that was actually embedded
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    record = relationship("Record", back_populates="vector_metas")

