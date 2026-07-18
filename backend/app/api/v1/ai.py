from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.dependencies import get_db
from app.schemas.errors import ErrorCode, ErrorResponse
from app.services.ai_service import train_model, predict

router = APIRouter(prefix="/ai", tags=["ai"])

@router.post("/train", status_code=status.HTTP_202_ACCEPTED)
async def train_endpoint(db: AsyncSession = Depends(get_db)):
    try:
        await train_model(db)
        return {"status": "training_started"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse.create(
                code=ErrorCode.INTERNAL_SERVER_ERROR,
                message=str(e)
            ).dict()
        )

@router.post("/predict", response_model=dict)
async def predict_endpoint(payload: dict, db: AsyncSession = Depends(get_db)):
    try:
        result = await predict(db, payload)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse.create(
                code=ErrorCode.INTERNAL_SERVER_ERROR,
                message=str(e)
            ).dict()
        )
