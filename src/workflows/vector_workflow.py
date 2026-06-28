from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy
from typing import Dict, Any

with workflow.unsafe.imports_passed_through():
    from src.activities.vectorization import prepare_vector_text_activity, embed_and_store_activity
    from src.schemas.pipeline_config import VectorizationConfig

@workflow.defn(name="VectorWorkflow")
class VectorWorkflow:
    @workflow.run
    async def run(self, raw_content: str, extracted_json: Dict[str, Any], config: VectorizationConfig) -> dict:
        retry_policy = RetryPolicy(maximum_attempts=3, initial_interval=timedelta(seconds=5))
        
        # 1. Prepare text
        text_to_embed = await workflow.execute_activity(
            prepare_vector_text_activity,
            args=[raw_content, extracted_json, config],
            start_to_close_timeout=timedelta(seconds=10)
        )
        
        # 2. Embed and store
        external_id = await workflow.execute_activity(
            embed_and_store_activity,
            args=[text_to_embed, config],
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=retry_policy
        )
        
        return {
            "status": "VECTORIZED",
            "external_vector_id": external_id
        }
