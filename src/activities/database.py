"""
DB Activities for DataForge.

All database write/read operations are wrapped as Temporal activities.
Workflows must never perform I/O directly — only activities may.

Available activities:
    - check_duplicate_activity     : content_hash ile duplicate kontrol
    - create_record_activity       : Yeni Record satırı oluşturma
    - update_record_status_activity: Status + opsiyonel alan güncelleme
    - save_qa_result_activity      : QAResult satırı kaydetme
    - save_vector_meta_activity    : VectorMeta satırı kaydetme
    - mark_record_failed_activity  : Hata durumunda FAILED + error_reason yazma
"""
import uuid
import logging
from typing import Any, Dict, List, Optional

from temporalio import activity

from src.infrastructure.database.session import get_session
from src.infrastructure.database.models import Record, QAResult, VectorMeta
from sqlalchemy import select

logger = logging.getLogger(__name__)


@activity.defn
async def check_duplicate_activity(content_hash: str, tenant_id: str) -> Optional[str]:
    """
    Verilen content_hash ile DB'de eşleşen bir Record var mı kontrol eder.

    Returns:
        Mevcut record'un ID'si — duplicate ise.
        None — yeni kayıt oluşturulabilir.
    """

    activity.logger.info(f"Checking for duplicate with hash: {content_hash[:16]} for tenant {tenant_id}...")
    async with get_session() as session:
        result = await session.execute(
            select(Record.id).where(Record.content_hash == content_hash).where(Record.tenant_id == tenant_id).limit(1)
        )
        row = result.scalar_one_or_none()
        if row:
            activity.logger.info(f"Duplicate found: record_id={row}")
            return str(row)
        return None


@activity.defn
async def create_record_activity(
    source: str,
    content_hash: str,
    raw_content: str,
    pipeline_name: str,
    input_type: str,
    tenant_id: str,
) -> str:
    """
    Yeni bir Record satırı oluşturur ve ID'sini döndürür.

    Args:
        source       : Kaynak URL veya dosya yolu.
        content_hash : SHA-256 hash (idempotency için).
        raw_content  : Ham içerik metni.
        pipeline_name: Pipeline adı (PipelineConfig.name).
        input_type   : Giriş tipi (url, text, pdf_scan, audio...).

    Returns:
        Oluşturulan Record'un UUID string ID'si.
    """
    record_id = str(uuid.uuid4())
    record = Record(
        id=record_id,
        tenant_id=tenant_id,
        source_url=source if input_type == "url" else None,
        source_id=source if input_type != "url" else None,
        content_hash=content_hash,
        raw_content=raw_content,
        pipeline_name=pipeline_name,
        status="INGESTED",
    )
    activity.logger.info(f"Creating record: id={record_id}, pipeline={pipeline_name}")
    async with get_session() as session:
        session.add(record)
    return record_id


@activity.defn
async def update_record_status_activity(
    record_id: str,
    status: str,
    extra_fields: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Bir Record'un status'unu ve opsiyonel ek alanları günceller.

    Args:
        record_id   : Güncellenecek Record ID'si.
        status      : Yeni durum (SCRAPED, EXTRACTED, QA_PENDING, QA_PASSED, ...).
        extra_fields: Güncellenecek ek alanlar.
                      Desteklenen anahtarlar: raw_content, extracted_json,
                      schema_version, error_reason, retry_count.
    """

    activity.logger.info(f"Updating record {record_id} → status={status}")
    async with get_session() as session:
        result = await session.execute(
            select(Record).where(Record.id == record_id)
        )
        record = result.scalar_one_or_none()
        if record is None:
            raise ValueError(f"Record not found: {record_id}")

        record.status = status
        if extra_fields:
            allowed = {"raw_content", "extracted_json", "schema_version", "error_reason", "retry_count", "llm_tokens_used", "processing_time_ms"}
            for key, val in extra_fields.items():
                if key in allowed:
                    setattr(record, key, val)
                else:
                    activity.logger.warning(f"Ignoring unknown field in update: {key}")


@activity.defn
async def save_qa_result_activity(
    record_id: str,
    qa_type: str,
    status: str,
    score: float,
    tenant_id: str,
    issues: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """
    Bir QAResult satırı oluşturur ve ID'sini döndürür.

    Args:
        record_id: İlgili Record ID'si.
        qa_type  : QA tipi ('deterministic' veya 'llm_judge').
        status   : QA sonucu ('PASSED' veya 'FAILED').
        score    : 0.0–100.0 arası puan.
        issues   : Tespit edilen sorunların listesi.

    Returns:
        Oluşturulan QAResult'ın UUID string ID'si.
    """
    qa_id = str(uuid.uuid4())
    qa_result = QAResult(
        id=qa_id,
        record_id=record_id,
        tenant_id=tenant_id,
        qa_type=qa_type,
        status=status,
        score=score,
        issues_json=issues or [],
    )
    activity.logger.info(f"Saving QA result for record {record_id}: type={qa_type}, status={status}")
    async with get_session() as session:
        session.add(qa_result)
    return qa_id


@activity.defn
async def save_vector_meta_activity(
    record_id: str,
    external_vector_id: str,
    collection_name: str,
    embedding_model: str,
    content_hash: str,
    tenant_id: str,
    vector_backend: str = "pgvector",
) -> str:
    """
    Bir VectorMeta satırı oluşturur ve ID'sini döndürür.

    Args:
        record_id         : İlgili Record ID'si.
        external_vector_id: Vector DB'deki dış ID.
        collection_name   : Vector DB koleksiyon/tablo adı.
        embedding_model   : Kullanılan embedding modeli.
        content_hash      : Embed edilen metnin hash'i (idempotency için).
        vector_backend    : Backend adı ('pgvector', 'qdrant', ...).

    Returns:
        Oluşturulan VectorMeta'nın UUID string ID'si.
    """
    meta_id = str(uuid.uuid4())
    meta = VectorMeta(
        id=meta_id,
        record_id=record_id,
        tenant_id=tenant_id,
        vector_backend=vector_backend,
        collection_name=collection_name,
        external_vector_id=external_vector_id,
        embedding_model=embedding_model,
        content_hash=content_hash,
    )
    activity.logger.info(f"Saving vector meta for record {record_id}: collection={collection_name}")
    async with get_session() as session:
        session.add(meta)
    return meta_id


@activity.defn
async def mark_record_failed_activity(record_id: str, error_reason: str) -> None:
    """
    Hata durumunda bir Record'u FAILED statüsüne alır ve error_reason'ı kaydeder.

    Args:
        record_id   : Hata alan Record ID'si.
        error_reason: Hata açıklaması (exception message, vs.).
    """

    activity.logger.error(f"Marking record {record_id} as FAILED: {error_reason[:200]}")
    async with get_session() as session:
        result = await session.execute(
            select(Record).where(Record.id == record_id)
        )
        record = result.scalar_one_or_none()
        if record is None:
            activity.logger.warning(f"Cannot mark as failed — record not found: {record_id}")
            return
        record.status = "FAILED"
        record.error_reason = error_reason
