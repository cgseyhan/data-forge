import os
import uuid
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from temporalio.client import Client

from src.schemas.pipeline_config import PipelineConfig
from src.infrastructure.database.session import AsyncSessionLocal
from src.infrastructure.database.models import Record

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="DataForge API", version="1.0.0")

class PipelineRequest(BaseModel):
    source: str

@app.on_event("startup")
async def startup_event():
    logger.info("Starting up API...")

@app.post("/pipelines/{config_name}/run")
async def run_pipeline(config_name: str, request: PipelineRequest):
    """
    Triggers a new DataForge pipeline based on the specified config_name.
    """
    config_path = Path("src/configs") / f"{config_name}.yaml"
    if not config_path.exists():
        raise HTTPException(status_code=404, detail=f"Configuration '{config_name}.yaml' not found.")
    
    try:
        config = PipelineConfig.from_yaml(str(config_path))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error parsing YAML: {str(e)}")

    try:
        client = await Client.connect(os.getenv("TEMPORAL_HOST", "localhost:7233"))
        
        # generate a unique business id to track the workflow
        workflow_id = f"dataforge-{config_name}-{uuid.uuid4()}"
        
        # start workflow asynchronously
        handle = await client.start_workflow(
            "FullPipelineWorkflow",
            args=[request.source, config],
            id=workflow_id,
            task_queue="dataforge-task-queue",
        )
        
        return {
            "message": "Pipeline started successfully",
            "workflow_id": workflow_id,
            "run_id": handle.result_run_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting workflow: {str(e)}")

@app.get("/records/{record_id}")
async def get_record(record_id: str):
    """
    Fetches the record data and status from the database.
    """
    from sqlalchemy import select
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Record).where(Record.id == record_id))
        record = result.scalars().first()
        
        if not record:
            raise HTTPException(status_code=404, detail="Record not found")
            
        return {
            "id": record.id,
            "source": record.source,
            "pipeline_name": record.pipeline_name,
            "status": record.status,
            "raw_content_preview": record.raw_content[:200] + "..." if record.raw_content else None,
            "extracted_data": record.extracted_data,
            "created_at": record.created_at,
            "updated_at": record.updated_at
        }
