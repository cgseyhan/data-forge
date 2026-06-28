import asyncio
import logging
from temporalio.client import Client
from temporalio.worker import Worker

from src.workflows.ingestion_workflow import IngestionWorkflow
from src.workflows.extraction_workflow import ExtractionWorkflow
from src.workflows.qa_workflow import QAWorkflow
from src.workflows.vector_workflow import VectorWorkflow
from src.workflows.full_pipeline_workflow import FullPipelineWorkflow

from src.activities.scraping import fetch_html_activity, parse_html_to_text_activity, generate_content_hash_activity
from src.activities.extraction import extract_data_activity
from src.activities.qa import run_deterministic_qa_activity, run_llm_judge_activity
from src.activities.vectorization import prepare_vector_text_activity, embed_and_store_activity

logging.basicConfig(level=logging.INFO)

async def main():
    client = await Client.connect("localhost:7233")
    
    worker = Worker(
        client,
        task_queue="dataforge-task-queue",
        workflows=[
            IngestionWorkflow,
            ExtractionWorkflow,
            QAWorkflow,
            VectorWorkflow,
            FullPipelineWorkflow
        ],
        activities=[
            fetch_html_activity,
            parse_html_to_text_activity,
            generate_content_hash_activity,
            extract_data_activity,
            run_deterministic_qa_activity,
            run_llm_judge_activity,
            prepare_vector_text_activity,
            embed_and_store_activity
        ]
    )
    
    logging.info("Starting DataForge Generic Worker...")
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())
