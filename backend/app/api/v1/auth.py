import uuid
import httpx
from app.core.test_state import is_test_mode
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import get_settings
from app.database.connection import get_db
from app.models.identity import User
from app.core.dependencies import get_current_user_or_none
from app.core.security import RequestContext

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["auth"])

class AuthRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None

class AuthLogin(BaseModel):
    email: EmailStr
    password: str

class AuthRefresh(BaseModel):
    refresh_token: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int = 3600

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(payload: AuthRegister, db: AsyncSession = Depends(get_db)):
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"{settings.SUPABASE_URL}/auth/v1/signup",
                json={"email": payload.email, "password": payload.password},
                headers={"apikey": settings.SUPABASE_SECRET_KEY}
            )
            resp.raise_for_status()
            data = resp.json()
            auth_id = data.get("user", {}).get("id")
            if not auth_id:
                raise ValueError("No user ID from Supabase")
                
            user = User(
                email=payload.email,
                full_name=payload.full_name,
                auth_id=auth_id,
                status="active"
            )
            db.add(user)
            await db.commit()
            return {"id": str(user.id), "email": user.email, "message": "Registered successfully"}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

@router.post("/login", response_model=TokenResponse)
async def login(payload: AuthLogin, db: AsyncSession = Depends(get_db)):
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"{settings.SUPABASE_URL}/auth/v1/token?grant_type=password",
                json={"email": payload.email, "password": payload.password},
                headers={"apikey": settings.SUPABASE_SECRET_KEY}
            )
            resp.raise_for_status()
            data = resp.json()
            return TokenResponse(
                access_token=data["access_token"],
                refresh_token=data.get("refresh_token"),
                expires_in=data.get("expires_in", 3600)
            )
        except Exception as e:
            raise HTTPException(status_code=401, detail="Invalid credentials")

@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: AuthRefresh, db: AsyncSession = Depends(get_db)):
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"{settings.SUPABASE_URL}/auth/v1/token?grant_type=refresh_token",
                json={"refresh_token": payload.refresh_token},
                headers={"apikey": settings.SUPABASE_SECRET_KEY}
            )
            resp.raise_for_status()
            data = resp.json()
            return TokenResponse(
                access_token=data["access_token"],
                refresh_token=data.get("refresh_token"),
                expires_in=data.get("expires_in", 3600)
            )
        except Exception as e:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    current_user: User | None = Depends(get_current_user_or_none)
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.get("/me")
async def me(current_user: User | None = Depends(get_current_user_or_none)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "status": current_user.status
    }
