from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy
from typing import Dict, Any

with workflow.unsafe.imports_passed_through():
    from src.activities.vectorization import prepare_vector_text_activity, embed_and_store_activity
    from src.schemas.pipeline_config import VectorizationConfig
    from src.activities.database import (
        update_record_status_activity,
        save_vector_meta_activity,
        mark_record_failed_activity,
    )
    from src.activities.scraping import generate_content_hash_activity


@workflow.defn(name="VectorWorkflow")
class VectorWorkflow:
    @workflow.run
    async def run(
        self,
        record_id: str,
        content_hash: str,
        raw_content: str,
        extracted_json: Dict[str, Any],
        config: VectorizationConfig,
        tenant_id: str = "",
    ) -> dict:
        retry_policy = RetryPolicy(maximum_attempts=3, initial_interval=timedelta(seconds=5))
        db_retry = RetryPolicy(maximum_attempts=5, initial_interval=timedelta(seconds=2))

        # ── 1. Embed edilecek metni hazırla ───────────────────────────────────
        text_to_embed = await workflow.execute_activity(
            prepare_vector_text_activity,
            args=[raw_content, extracted_json, config],
            start_to_close_timeout=timedelta(seconds=10)
        )

        # ── 2. Embed et ve vector DB'ye kaydet ───────────────────────────────
        external_id = await workflow.execute_activity(
            embed_and_store_activity,
            args=[text_to_embed, config, tenant_id],
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=retry_policy
        )

        # ── 3. VectorMeta satırı oluştur ─────────────────────────────────────
        await workflow.execute_activity(
            save_vector_meta_activity,
            args=[
                record_id,
                external_id,
                config.collection_name,
                config.embedding_model,
                content_hash,
                tenant_id,
            ],
            start_to_close_timeout=timedelta(seconds=15),
            retry_policy=db_retry
        )

        # ── 4. Status: VECTORIZED ─────────────────────────────────────────────
        await workflow.execute_activity(
            update_record_status_activity,
            args=[record_id, "VECTORIZED"],
            start_to_close_timeout=timedelta(seconds=15),
            retry_policy=db_retry
        )

        return {
            "status": "VECTORIZED",
            "record_id": record_id,
            "external_vector_id": external_id,
        }
