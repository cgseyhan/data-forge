import logging
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.session import get_session
from src.infrastructure.database.models import Tenant

logger = logging.getLogger(__name__)

API_KEY_HEADER = APIKeyHeader(name="X-API-KEY", auto_error=True)

async def get_current_tenant(api_key: str = Security(API_KEY_HEADER)) -> Tenant:
    """
    Dependency to validate API key and return the associated tenant.
    """
    async with get_session() as session:
        result = await session.execute(
            select(Tenant).where(Tenant.api_key == api_key, Tenant.is_active == True)
        )
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            logger.warning(f"Failed authentication attempt with API key: {api_key[:4]}...")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or inactive API Key",
                headers={"WWW-Authenticate": "ApiKey"},
            )
        
        return tenant
