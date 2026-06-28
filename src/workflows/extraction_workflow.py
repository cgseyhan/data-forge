from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy
from typing import Dict, Any

with workflow.unsafe.imports_passed_through():
    from src.activities.extraction import extract_data_activity
    from src.schemas.pipeline_config import ExtractionConfig

@workflow.defn(name="ExtractionWorkflow")
class ExtractionWorkflow:
    @workflow.run
    async def run(self, raw_content: str, config: ExtractionConfig) -> dict:
        retry_policy = RetryPolicy(
            maximum_attempts=3,
            initial_interval=timedelta(seconds=10)
        )
        
        extracted_json = await workflow.execute_activity(
            extract_data_activity,
            args=[raw_content, config],
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=retry_policy
        )
        
        return {
            "status": "EXTRACTED",
            "extracted_json": extracted_json
        }
