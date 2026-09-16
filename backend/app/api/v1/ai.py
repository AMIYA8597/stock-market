from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_rate_limiter
from app.services.ai_service import ServiceUnavailableError, predict, train_model

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/train", status_code=status.HTTP_202_ACCEPTED)
async def train_endpoint(
    db: AsyncSession = Depends(get_db),
    _rate_limit: None = Depends(get_rate_limiter(requests=5, window=60)),
) -> dict[str, str]:
    """Launch model training. Returns 503 if engine not available."""
    try:
        await train_model(db)
        return {"status": "training_started"}
    except ServiceUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        ) from exc


from pydantic import BaseModel, Field


class PredictRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=15, description="Stock ticker symbol")
    # Add any other required fields for inference based on backend structure


@router.post("/predict", response_model=dict)
async def predict_endpoint(
    payload: PredictRequest,
    db: AsyncSession = Depends(get_db),
    _rate_limit: None = Depends(get_rate_limiter(requests=5, window=60)),
) -> dict:
    """Run inference. Returns 503 if model not trained."""
    try:
        return await predict(db, payload.model_dump())
    except ServiceUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        ) from exc
