from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.future import select
from pydantic import BaseModel

from src.infrastructure.database.session import get_session
from src.infrastructure.database.models import PipelineConfigDB, User
from src.api.auth import get_current_user

router = APIRouter(prefix="/api/v1/configs", tags=["Configs"])

class ConfigCreate(BaseModel):
    name: str
    description: str = None
    config_json: Dict[str, Any]

class ConfigResponse(BaseModel):
    id: str
    name: str
    description: str = None
    config_json: Dict[str, Any]

    class Config:
        orm_mode = True

@router.post("/", response_model=ConfigResponse)
async def create_config(config_in: ConfigCreate, current_user: User = Depends(get_current_user)):
    async with get_session() as session:
        new_config = PipelineConfigDB(
            tenant_id=current_user.tenant_id,
            name=config_in.name,
            description=config_in.description,
            config_json=config_in.config_json
        )
        session.add(new_config)
        await session.commit()
        await session.refresh(new_config)
        return new_config

@router.get("/", response_model=List[ConfigResponse])
async def list_configs(current_user: User = Depends(get_current_user)):
    async with get_session() as session:
        result = await session.execute(
            select(PipelineConfigDB).where(PipelineConfigDB.tenant_id == current_user.tenant_id)
        )
        return result.scalars().all()

@router.get("/{config_id}", response_model=ConfigResponse)
async def get_config(config_id: str, current_user: User = Depends(get_current_user)):
    async with get_session() as session:
        result = await session.execute(
            select(PipelineConfigDB).where(
                PipelineConfigDB.id == config_id,
                PipelineConfigDB.tenant_id == current_user.tenant_id
            )
        )
        config = result.scalar_one_or_none()
        if not config:
            raise HTTPException(status_code=404, detail="Config not found")
        return config
