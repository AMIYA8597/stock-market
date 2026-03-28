"""Explainability endpoints router (GET/POST /explain/*)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.schemas.explain import (
    AttentionResponse,
    AttentionTimestep,
    CounterfactualInstance,
    CounterfactualRequest,
    CounterfactualResponse,
    FeatureChange,
    SHAPContribution,
    SHAPResponse,
)

router = APIRouter(prefix="/explain", tags=["explainability"])


@router.get("/shap/{symbol}", response_model=SHAPResponse)
async def get_shap_explanation(symbol: str, db: AsyncSession = Depends(get_db)) -> SHAPResponse:
    _ = db
    now = datetime.now(timezone.utc)
    rows = [
        SHAPContribution(name="momentum_21d", shap_value=Decimal("0.012300"), feature_value=Decimal("0.06100000"), percentile_rank=Decimal("88.20")),
        SHAPContribution(name="volatility_10d", shap_value=Decimal("-0.006800"), feature_value=Decimal("0.01340000"), percentile_rank=Decimal("43.10")),
    ]
    return SHAPResponse(
        symbol=symbol.upper(),
        model="xgboost",
        feature_contributions=rows,
        base_value=Decimal("0.001100"),
        output_value=Decimal("0.006600"),
        waterfall_ready=True,
        timestamp=now,
    )


@router.get("/attention/{symbol}", response_model=AttentionResponse)
async def get_attention_explanation(symbol: str, db: AsyncSession = Depends(get_db)) -> AttentionResponse:
    _ = db
    now = datetime.now(timezone.utc)
    weights = [
        [Decimal("0.04"), Decimal("0.08"), Decimal("0.12"), Decimal("0.10"), Decimal("0.07")],
        [Decimal("0.03"), Decimal("0.07"), Decimal("0.13"), Decimal("0.11"), Decimal("0.06")],
    ]
    means = [Decimal("0.035"), Decimal("0.075"), Decimal("0.125"), Decimal("0.105"), Decimal("0.065")]
    top = [
        AttentionTimestep(date=now - timedelta(days=2), weight=Decimal("0.125000")),
        AttentionTimestep(date=now - timedelta(days=3), weight=Decimal("0.105000")),
    ]
    return AttentionResponse(
        symbol=symbol.upper(),
        model="tft",
        weights=weights,
        mean_weights=means,
        top_timesteps=top,
        num_heads=2,
        num_timesteps=5,
        timestamp=now,
    )


@router.post("/counterfactual/{symbol}", response_model=CounterfactualResponse)
async def post_counterfactual_explanation(
    symbol: str,
    request: CounterfactualRequest,
    db: AsyncSession = Depends(get_db),
) -> CounterfactualResponse:
    _ = db
    target = request.target_direction.upper()
    if target not in {"BUY", "SELL"}:
        raise HTTPException(status_code=400, detail="target_direction must be BUY or SELL")

    rows = []
    for _ in range(request.num_cfs):
        rows.append(
            CounterfactualInstance(
                cf_id=str(uuid4()),
                changed_features=[
                    FeatureChange(name="momentum_21d", original_value=Decimal("0.01200000"), counterfactual_value=Decimal("0.02400000"), change_pct=Decimal("100.00")),
                    FeatureChange(name="rsi_14", original_value=Decimal("47.00000000"), counterfactual_value=Decimal("54.00000000"), change_pct=Decimal("14.89")),
                ],
                resulting_signal=Decimal("0.4100") if target == "BUY" else Decimal("-0.3900"),
                resulting_confidence=Decimal("0.7200"),
                proximity_score=Decimal("0.8100"),
            )
        )

    return CounterfactualResponse(
        symbol=symbol.upper(),
        target_direction=target,
        counterfactuals=rows,
        original_signal=Decimal("-0.1200"),
        original_confidence=Decimal("0.6100"),
        timestamp=datetime.now(timezone.utc),
    )
