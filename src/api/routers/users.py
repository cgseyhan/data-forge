from datetime import timedelta
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.future import select
from pydantic import BaseModel, EmailStr

from src.infrastructure.database.session import get_session
from src.infrastructure.database.models import User, Tenant
from src.api.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    get_current_user
)

router = APIRouter(prefix="/api/v1/users", tags=["Users"])

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    company_name: str # For creating the tenant

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    tenant_id: str

    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str

@router.post("/register", response_model=UserResponse)
async def register_user(user_in: UserCreate):
    async with get_session() as session:
        # Check if user exists
        result = await session.execute(select(User).where(User.email == user_in.email))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create a Tenant for this new user
        # In a real SaaS, maybe you invite users to existing tenants, but for now we create a tenant per new sign up
        new_tenant = Tenant(
            company_name=user_in.company_name,
            api_key=str(uuid.uuid4()) # Generate a default API Key
        )
        session.add(new_tenant)
        await session.flush() # To get new_tenant.id
        
        new_user = User(
            email=user_in.email,
            hashed_password=get_password_hash(user_in.password),
            full_name=user_in.full_name,
            tenant_id=new_tenant.id
        )
        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)
        
        return new_user

@router.post("/login", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    async with get_session() as session:
        result = await session.execute(select(User).where(User.email == form_data.username))
        user = result.scalar_one_or_none()
        
        if not user or not verify_password(form_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.id}, expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user
