import os
import uuid
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from temporalio.client import Client

from src.schemas.pipeline_config import PipelineConfig
from src.infrastructure.database.session import get_session
from src.infrastructure.database.models import Record, Tenant, User
from src.api.auth import get_current_tenant, get_current_user
from src.api.routers import users, configs, analytics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="DataForge API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(users.router)
app.include_router(configs.router)
app.include_router(analytics.router)

class PipelineRequest(BaseModel):
    source: str

@app.on_event("startup")
async def startup_event():
    logger.info("Starting up API...")

@app.post("/api/v1/pipelines/{config_name}/run")
async def run_pipeline(
    config_name: str,
    request: PipelineRequest,
    tenant: Tenant = Depends(get_current_tenant)
):
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
            args=[request.source, config, tenant.id],
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

@app.get("/api/v1/records/{record_id}")
async def get_record(record_id: str, tenant: Tenant = Depends(get_current_tenant)):
    """
    Fetches the record data and status from the database.
    """
    from sqlalchemy import select
    
    async with get_session() as session:
        result = await session.execute(
            select(Record).where(Record.id == record_id, Record.tenant_id == tenant.id)
        )
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

@app.get("/api/v1/records")
async def list_records(current_user: User = Depends(get_current_user)):
    """
    Fetches the list of records for the dashboard.
    """
    from sqlalchemy import select
    
    async with get_session() as session:
        result = await session.execute(
            select(Record).where(Record.tenant_id == current_user.tenant_id).order_by(Record.created_at.desc()).limit(50)
        )

        records = result.scalars().all()
        
        return [
            {
                "id": r.id,
                "source": r.source_url or r.source_id,
                "pipeline_name": r.pipeline_name,
                "status": r.status,
                "created_at": r.created_at,
                "updated_at": r.updated_at
            } for r in records
        ]
