from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy
from typing import Dict, Any

with workflow.unsafe.imports_passed_through():
    from src.activities.extraction import extract_data_activity
    from src.schemas.pipeline_config import ExtractionConfig
    from src.activities.database import (
        update_record_status_activity,
        mark_record_failed_activity,
    )


@workflow.defn(name="ExtractionWorkflow")
class ExtractionWorkflow:
    @workflow.run
    async def run(self, record_id: str, raw_content: str, config: ExtractionConfig) -> dict:
        retry_policy = RetryPolicy(
            maximum_attempts=3,
            initial_interval=timedelta(seconds=10)
        )
        db_retry = RetryPolicy(maximum_attempts=5, initial_interval=timedelta(seconds=2))

        # ── 1. Status: EXTRACTION_PENDING ────────────────────────────────────
        await workflow.execute_activity(
            update_record_status_activity,
            args=[record_id, "EXTRACTION_PENDING"],
            start_to_close_timeout=timedelta(seconds=15),
            retry_policy=db_retry
        )

        # ── 2. LLM ile extraction yap ────────────────────────────────────────
        extracted_json = await workflow.execute_activity(
            extract_data_activity,
            args=[raw_content, config],
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=retry_policy
        )

        # ── 3. Status: EXTRACTED + extracted_json kaydet ─────────────────────
        await workflow.execute_activity(
            update_record_status_activity,
            args=[record_id, "EXTRACTED", {"extracted_json": extracted_json}],
            start_to_close_timeout=timedelta(seconds=15),
            retry_policy=db_retry
        )

        return {
            "status": "EXTRACTED",
            "record_id": record_id,
            "extracted_json": extracted_json,
        }
