import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, JSON, Text, Float, Integer, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.postgresql import JSONB

Base = declarative_base()

class Tenant(Base):
    """
    SaaS Tenant (Customer) model.
    """
    __tablename__ = "tenants"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    api_key = Column(String, index=True, unique=True, nullable=False)
    company_name = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    
    # SaaS / Billing fields
    subscription_tier = Column(String, default="free")
    stripe_customer_id = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    records = relationship("Record", back_populates="tenant", cascade="all, delete-orphan")
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    configs = relationship("PipelineConfigDB", back_populates="tenant", cascade="all, delete-orphan")

class User(Base):
    """
    Dashboard User model.
    """
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), index=True, nullable=False)
    
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    tenant = relationship("Tenant", back_populates="users")

class PipelineConfigDB(Base):
    """
    Database-backed Pipeline Configuration.
    """
    __tablename__ = "pipeline_configs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), index=True, nullable=False)
    
    name = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    
    config_json = Column(JSONB, nullable=False) # Stores the actual YAML/JSON config structure
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    tenant = relationship("Tenant", back_populates="configs")

class Record(Base):
    """
    Generic Record model for DataForge.
    Follows idempotency and tracks exact pipeline states.
    """
    __tablename__ = "records"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), index=True, nullable=False)
    
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
    
    # Billing / Usage Tracking
    llm_tokens_used = Column(Integer, default=0)
    processing_time_ms = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tenant = relationship("Tenant", back_populates="records")
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
    record_id = Column(String, ForeignKey("records.id"), index=True, nullable=False)
    tenant_id = Column(String, ForeignKey("tenants.id"), index=True, nullable=False)
    
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
    record_id = Column(String, ForeignKey("records.id"), index=True, nullable=False)
    tenant_id = Column(String, ForeignKey("tenants.id"), index=True, nullable=False)
    
    vector_backend = Column(String, default="pgvector")
    collection_name = Column(String, index=True)
    external_vector_id = Column(String, index=True, nullable=True)
    
    embedding_model = Column(String)
    content_hash = Column(String, index=True) # Hash of the text that was actually embedded
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    record = relationship("Record", back_populates="vector_metas")

