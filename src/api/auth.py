import os
import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Security, HTTPException, status, Depends
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from sqlalchemy.future import select
from jose import JWTError, jwt
from passlib.context import CryptContext

from src.infrastructure.database.session import get_session
from src.infrastructure.database.models import Tenant, User

logger = logging.getLogger(__name__)

# API Key config
API_KEY_HEADER = APIKeyHeader(name="X-API-KEY", auto_error=False)

# JWT config
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "super-secret-key-for-dev")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 7 days

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/users/login")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_tenant(api_key: str = Security(API_KEY_HEADER)) -> Tenant:
    """
    Dependency to validate API key and return the associated tenant.
    For Machine-to-Machine communication.
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API Key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

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


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """
    Dependency to validate JWT and return the associated user.
    For Dashboard / Frontend communication.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    async with get_session() as session:
        result = await session.execute(
            select(User).where(User.id == user_id, User.is_active == True)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise credentials_exception
        return user
