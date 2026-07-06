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
from src.activities.preprocessing import extract_text_from_pdf_activity, transcribe_audio_activity
from src.activities.extraction import extract_data_activity
from src.activities.qa import run_deterministic_qa_activity, run_llm_judge_activity
from src.activities.vectorization import prepare_vector_text_activity, embed_and_store_activity
from src.activities.database import (
    check_duplicate_activity,
    create_record_activity,
    update_record_status_activity,
    save_qa_result_activity,
    save_vector_meta_activity,
    mark_record_failed_activity,
)

from src.infrastructure.database.session import init_db

logging.basicConfig(level=logging.INFO)


async def main():
    # DB tablolarını başlatma (dev/test için; prod'da Alembic kullan)
    await init_db()

    client = await Client.connect("localhost:7233")

    worker = Worker(
        client,
        task_queue="dataforge-task-queue",
        workflows=[
            IngestionWorkflow,
            ExtractionWorkflow,
            QAWorkflow,
            VectorWorkflow,
            FullPipelineWorkflow,
        ],
        activities=[
            # Scraping
            fetch_html_activity,
            parse_html_to_text_activity,
            generate_content_hash_activity,
            # Preprocessing
            extract_text_from_pdf_activity,
            transcribe_audio_activity,
            # Extraction
            extract_data_activity,
            # QA
            run_deterministic_qa_activity,
            run_llm_judge_activity,
            # Vectorization
            prepare_vector_text_activity,
            embed_and_store_activity,
            # Database
            check_duplicate_activity,
            create_record_activity,
            update_record_status_activity,
            save_qa_result_activity,
            save_vector_meta_activity,
            mark_record_failed_activity,
        ],
    )

    logging.info("Starting DataForge Generic Worker...")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
