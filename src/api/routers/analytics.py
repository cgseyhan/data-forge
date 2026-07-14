from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func

from src.infrastructure.database.session import get_session
from src.infrastructure.database.models import Record, User, PipelineConfigDB
from src.api.auth import get_current_user

router = APIRouter(
    prefix="/api/v1/analytics",
    tags=["analytics"]
)

@router.get("/summary")
async def get_analytics_summary(current_user: User = Depends(get_current_user)):
    """
    Returns analytics summary for the dashboard:
    - total_pipelines: Number of distinct pipeline runs
    - records_processed: Total records
    - llm_tokens_used: Total tokens used
    """
    async with get_session() as session:
        # Total distinct pipelines run
        pipeline_count_result = await session.execute(
            select(func.count(func.distinct(Record.pipeline_name)))
            .where(Record.tenant_id == current_user.tenant_id)
        )
        total_pipelines = pipeline_count_result.scalar() or 0

        # Total records
        records_count_result = await session.execute(
            select(func.count(Record.id))
            .where(Record.tenant_id == current_user.tenant_id)
        )
        records_processed = records_count_result.scalar() or 0

        # Total tokens
        tokens_result = await session.execute(
            select(func.sum(Record.llm_tokens_used))
            .where(Record.tenant_id == current_user.tenant_id)
        )
        llm_tokens_used = tokens_result.scalar() or 0

        return {
            "total_pipelines": total_pipelines,
            "records_processed": records_processed,
            "llm_tokens_used": llm_tokens_used
        }
