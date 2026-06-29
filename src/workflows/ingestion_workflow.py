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

@workflow.defn(name="IngestionWorkflow")
class IngestionWorkflow:
    @workflow.run
    async def run(self, source: str, input_type: str = "url") -> dict:
        retry_policy = RetryPolicy(
            maximum_attempts=3,
            initial_interval=timedelta(seconds=5),
            backoff_coefficient=2.0
        )
        
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
            raw_text = source
            
        content_hash = await workflow.execute_activity(
            generate_content_hash_activity,
            raw_text,
            start_to_close_timeout=timedelta(seconds=10)
        )
        
        return {
            "status": "INGESTED",
            "source": source,
            "raw_text": raw_text,
            "content_hash": content_hash
        }
