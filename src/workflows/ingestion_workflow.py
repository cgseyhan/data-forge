from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from src.activities.scraping import (
        fetch_html_activity,
        parse_html_to_text_activity,
        generate_content_hash_activity
    )
    from src.activities.preprocessing import (
        extract_text_from_pdf_activity,
        transcribe_audio_activity
    )
    from src.activities.database import (
        check_duplicate_activity,
        create_record_activity,
        update_record_status_activity,
        mark_record_failed_activity,
    )


@workflow.defn(name="IngestionWorkflow")
class IngestionWorkflow:
    @workflow.run
    async def run(self, source: str, input_type: str = "url", pipeline_name: str = "default", tenant_id: str = "") -> dict:
        retry_policy = RetryPolicy(
            maximum_attempts=3,
            initial_interval=timedelta(seconds=5),
            backoff_coefficient=2.0
        )
        db_retry = RetryPolicy(maximum_attempts=5, initial_interval=timedelta(seconds=2))

        # ── 1. Ham içeriği al ────────────────────────────────────────────────
        raw_text = ""
        if input_type == "url":
            html_content = await workflow.execute_activity(
                fetch_html_activity,
                source,
                start_to_close_timeout=timedelta(minutes=1),
                retry_policy=retry_policy
            )
            raw_text = await workflow.execute_activity(
                parse_html_to_text_activity,
                html_content,
                start_to_close_timeout=timedelta(seconds=30)
            )
        elif input_type == "pdf_scan":
            raw_text = await workflow.execute_activity(
                extract_text_from_pdf_activity,
                source,
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=retry_policy
            )
        elif input_type == "audio":
            raw_text = await workflow.execute_activity(
                transcribe_audio_activity,
                source,
                start_to_close_timeout=timedelta(minutes=10),
                retry_policy=retry_policy
            )
        else:
            # input_type == "text" veya bilinmeyen; kaynak doğrudan içerik
            raw_text = source

        # ── 2. Content hash üret ─────────────────────────────────────────────
        content_hash = await workflow.execute_activity(
            generate_content_hash_activity,
            raw_text,
            start_to_close_timeout=timedelta(seconds=10)
        )

        # ── 3. Duplicate kontrolü ────────────────────────────────────────────
        existing_record_id = await workflow.execute_activity(
            check_duplicate_activity,
            args=[content_hash, tenant_id],
            start_to_close_timeout=timedelta(seconds=15),
            retry_policy=db_retry
        )
        if existing_record_id:
            return {
                "status": "DUPLICATE",
                "record_id": existing_record_id,
                "source": source,
                "content_hash": content_hash,
            }

        # ── 4. Yeni Record oluştur ───────────────────────────────────────────
        record_id = await workflow.execute_activity(
            create_record_activity,
            args=[source, content_hash, raw_text, pipeline_name, input_type, tenant_id],
            start_to_close_timeout=timedelta(seconds=15),
            retry_policy=db_retry
        )

        # ── 5. Status'u SCRAPED'e yükselt ────────────────────────────────────
        await workflow.execute_activity(
            update_record_status_activity,
            args=[record_id, "SCRAPED"],
            start_to_close_timeout=timedelta(seconds=15),
            retry_policy=db_retry
        )

        return {
            "status": "INGESTED",
            "record_id": record_id,
            "source": source,
            "raw_text": raw_text,
            "content_hash": content_hash,
        }
