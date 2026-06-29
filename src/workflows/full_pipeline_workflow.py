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

@workflow.defn(name="FullPipelineWorkflow")
class FullPipelineWorkflow:
    @workflow.run
    async def run(self, source: str, config: PipelineConfig) -> dict:
        """
        The orchestrator for the entire generic AI data pipeline.
        1. Ingest
        2. Extract
        3. QA
        4. Vectorize
        """
        # Note: In a real implementation, you would update the DB state at each step.
        
        # 1. Ingestion
        ingest_result = await workflow.execute_child_workflow(
            IngestionWorkflow.run,
            args=[source, config.input_type],
            id=f"ingest-{source[:50]}",
            retry_policy=RetryPolicy(maximum_attempts=3)
        )
        
        raw_text = ingest_result["raw_text"]
        
        if not config.extraction:
            return {"final_status": "INGESTED", "source": source}
            
        # 2. Extraction
        extract_result = await workflow.execute_child_workflow(
            ExtractionWorkflow.run,
            args=[raw_text, config.extraction],
            id=f"extract-{source[:50]}",
            retry_policy=RetryPolicy(maximum_attempts=3)
        )
        
        extracted_json = extract_result["extracted_json"]
        
        if not config.qa_rules:
            # If no QA, just proceed to vectorization
            qa_status = "QA_PASSED"
        else:
            # 3. QA
            qa_result = await workflow.execute_child_workflow(
                QAWorkflow.run,
                args=[raw_text, extracted_json, config.qa_rules],
                id=f"qa-{source[:50]}",
                retry_policy=RetryPolicy(maximum_attempts=3)
            )
            
            qa_status = qa_result["status"]
            if qa_status == "QA_FAILED":
                return {"final_status": "QA_FAILED", "issues": qa_result.get("issues")}
                
        if not config.vectorization or qa_status != "QA_PASSED":
            return {"final_status": qa_status, "source": source}
            
        # 4. Vectorization
        vector_result = await workflow.execute_child_workflow(
            VectorWorkflow.run,
            args=[raw_text, extracted_json, config.vectorization],
            id=f"vector-{source[:50]}",
            retry_policy=RetryPolicy(maximum_attempts=3)
        )
        
        return {
            "final_status": "VECTORIZED",
            "source": source,
            "external_vector_id": vector_result["external_vector_id"]
        }
