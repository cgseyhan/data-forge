from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy
from typing import Dict, Any

with workflow.unsafe.imports_passed_through():
    from src.schemas.pipeline_config import PipelineConfig
    from src.workflows.ingestion_workflow import IngestionWorkflow
    from src.workflows.extraction_workflow import ExtractionWorkflow
    from src.workflows.qa_workflow import QAWorkflow
    from src.workflows.vector_workflow import VectorWorkflow
    from src.activities.database import mark_record_failed_activity


@workflow.defn(name="FullPipelineWorkflow")
class FullPipelineWorkflow:
    @workflow.run
    async def run(self, source: str, config: PipelineConfig) -> dict:
        """
        DataForge genel AI veri pipeline orkestratörü.

        Adımlar:
            1. Ingest  — Ham içeriği al, DB'ye kaydet (status=SCRAPED)
            2. Extract — LLM ile JSON çıkar (status=EXTRACTED)
            3. QA      — Kural & LLM judge (status=QA_PASSED | QA_FAILED)
            4. Vector  — Embed et ve vector DB'ye göm (status=VECTORIZED)

        Herhangi bir adım başarısız olursa record FAILED olarak işaretlenir.
        """
        child_retry = RetryPolicy(maximum_attempts=3)
        record_id: str | None = None

        # ── 1. Ingestion ──────────────────────────────────────────────────────
        try:
            ingest_result = await workflow.execute_child_workflow(
                IngestionWorkflow.run,
                args=[source, config.input_type, config.name],
                id=f"ingest-{workflow.info().workflow_id}",
                retry_policy=child_retry,
            )
        except Exception as exc:
            # Ingestion başarısız oldu; record oluşturulmadı, sadece hata döndür.
            return {"final_status": "FAILED", "source": source, "error": str(exc)}

        if ingest_result["status"] == "DUPLICATE":
            return {
                "final_status": "DUPLICATE",
                "source": source,
                "record_id": ingest_result["record_id"],
                "content_hash": ingest_result["content_hash"],
            }

        record_id = ingest_result["record_id"]
        raw_text = ingest_result["raw_text"]
        content_hash = ingest_result["content_hash"]

        if not config.extraction:
            return {"final_status": "INGESTED", "record_id": record_id, "source": source}

        # ── 2. Extraction ─────────────────────────────────────────────────────
        try:
            extract_result = await workflow.execute_child_workflow(
                ExtractionWorkflow.run,
                args=[record_id, raw_text, config.extraction],
                id=f"extract-{workflow.info().workflow_id}",
                retry_policy=child_retry,
            )
        except Exception as exc:
            await workflow.execute_activity(
                mark_record_failed_activity,
                args=[record_id, f"Extraction failed: {exc}"],
                start_to_close_timeout=timedelta(seconds=15),
            )
            return {"final_status": "FAILED", "record_id": record_id, "error": str(exc)}

        extracted_json = extract_result["extracted_json"]

        if not config.qa_rules:
            qa_status = "QA_PASSED"
        else:
            # ── 3. QA ─────────────────────────────────────────────────────────
            try:
                qa_result = await workflow.execute_child_workflow(
                    QAWorkflow.run,
                    args=[record_id, raw_text, extracted_json, config.qa_rules],
                    id=f"qa-{workflow.info().workflow_id}",
                    retry_policy=child_retry,
                )
            except Exception as exc:
                await workflow.execute_activity(
                    mark_record_failed_activity,
                    args=[record_id, f"QA failed: {exc}"],
                    start_to_close_timeout=timedelta(seconds=15),
                )
                return {"final_status": "FAILED", "record_id": record_id, "error": str(exc)}

            qa_status = qa_result["status"]
            if qa_status == "QA_FAILED":
                return {
                    "final_status": "QA_FAILED",
                    "record_id": record_id,
                    "issues": qa_result.get("issues"),
                }

        if not config.vectorization or qa_status != "QA_PASSED":
            return {"final_status": qa_status, "record_id": record_id, "source": source}

        # ── 4. Vectorization ──────────────────────────────────────────────────
        try:
            vector_result = await workflow.execute_child_workflow(
                VectorWorkflow.run,
                args=[record_id, content_hash, raw_text, extracted_json, config.vectorization],
                id=f"vector-{workflow.info().workflow_id}",
                retry_policy=child_retry,
            )
        except Exception as exc:
            await workflow.execute_activity(
                mark_record_failed_activity,
                args=[record_id, f"Vectorization failed: {exc}"],
                start_to_close_timeout=timedelta(seconds=15),
            )
            return {"final_status": "FAILED", "record_id": record_id, "error": str(exc)}

        return {
            "final_status": "VECTORIZED",
            "record_id": record_id,
            "source": source,
            "external_vector_id": vector_result["external_vector_id"],
        }
