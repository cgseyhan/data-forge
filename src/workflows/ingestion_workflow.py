from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from src.activities.scraping import (
        fetch_html_activity,
        parse_html_to_text_activity,
        generate_content_hash_activity
    )

@workflow.defn(name="IngestionWorkflow")
class IngestionWorkflow:
    @workflow.run
    async def run(self, url: str) -> dict:
        retry_policy = RetryPolicy(
            maximum_attempts=3,
            initial_interval=timedelta(seconds=5),
            backoff_coefficient=2.0
        )
        
        # 1. Fetch HTML
        html_content = await workflow.execute_activity(
            fetch_html_activity,
            url,
            start_to_close_timeout=timedelta(minutes=1),
            retry_policy=retry_policy
        )
        
        # 2. Parse text
        raw_text = await workflow.execute_activity(
            parse_html_to_text_activity,
            html_content,
            start_to_close_timeout=timedelta(seconds=30)
        )
        
        # 3. Generate hash
        content_hash = await workflow.execute_activity(
            generate_content_hash_activity,
            raw_text,
            start_to_close_timeout=timedelta(seconds=10)
        )
        
        return {
            "status": "SCRAPED",
            "url": url,
            "raw_text": raw_text,
            "content_hash": content_hash
        }
