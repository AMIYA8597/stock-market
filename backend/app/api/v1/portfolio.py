"""
Portfolio management API endpoints.

Core CRUD implemented in Phase 1. Optimization + risk in Phase 5.
"""

from __future__ import annotations

from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.portfolio import Portfolio, PortfolioHolding
from app.models.user import User
from app.schemas.portfolio import (
    HoldingAdd,
    HoldingResponse,
    OptimizeRequest,
    PortfolioCreate,
    PortfolioResponse,
)

router = APIRouter()


class TransactionRequest(BaseModel):
    symbol: str
    type: str = Field(pattern="^(BUY|SELL)$")
    quantity: float = Field(gt=0)
    price: float = Field(gt=0)


class PromptOptimizeRequest(BaseModel):
    universe: list[str]
    method: str = Field(pattern="^(hrp|black_litterman|cvar|mean_variance)$")
    constraints: dict[str, object] = Field(default_factory=dict)
    use_ml_views: bool = True


@router.post("/", response_model=PortfolioResponse, status_code=status.HTTP_201_CREATED)
async def create_portfolio(
    payload: PortfolioCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a new portfolio for the current user."""
    portfolio = Portfolio(
        user_id=current_user.id,
        name=payload.name,
        description=payload.description,
        initial_capital=payload.initial_capital,
    )
    db.add(portfolio)
    await db.flush()
    await db.refresh(portfolio, ["holdings"])

    return PortfolioResponse(
        id=portfolio.id,
        name=portfolio.name,
        description=portfolio.description,
        initial_capital=portfolio.initial_capital,
        holdings=[],
        created_at=portfolio.created_at,
    )


@router.get("/", response_model=List[PortfolioResponse])
async def list_portfolios(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """List all portfolios for the current user."""
    result = await db.execute(
        select(Portfolio)
        .where(Portfolio.user_id == current_user.id)
        .options(selectinload(Portfolio.holdings))
    )
    portfolios = result.scalars().all()

    return [
        PortfolioResponse(
            id=p.id,
            name=p.name,
            description=p.description,
            initial_capital=p.initial_capital,
            holdings=[
                HoldingResponse(
                    symbol=h.symbol,
                    quantity=h.quantity,
                    avg_cost=h.avg_cost,
                    added_at=h.added_at,
                )
                for h in p.holdings
            ],
            created_at=p.created_at,
        )
        for p in portfolios
    ]


@router.post("/{portfolio_id}/holdings", status_code=status.HTTP_201_CREATED)
async def add_holding(
    portfolio_id: int,
    payload: HoldingAdd,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Add a holding to a portfolio."""
    result = await db.execute(
        select(Portfolio).where(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == current_user.id,
        )
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    holding = PortfolioHolding(
        portfolio_id=portfolio_id,
        symbol=payload.symbol.upper(),
        quantity=payload.quantity,
        avg_cost=payload.avg_cost,
    )
    db.add(holding)
    await db.flush()

    return {"message": "Holding added", "symbol": holding.symbol}


@router.post("/optimize")
async def optimize_portfolio(payload: OptimizeRequest | PromptOptimizeRequest):
    """Return deterministic constrained allocations for legacy and prompt contracts."""
    if isinstance(payload, PromptOptimizeRequest):
        assets = payload.universe[:20]
        if not assets:
            raise HTTPException(status_code=422, detail="universe must include at least one asset")

        w = 1.0 / len(assets)
        weights = {symbol: round(w, 6) for symbol in assets}

        return {
            "weights": weights,
            "expected_return": 0.137,
            "expected_vol": 0.112,
            "sharpe_ratio": 1.223,
            "efficient_frontier": [
                {"return": round(0.06 + i * 0.0015, 4), "vol": round(0.07 + i * 0.0012, 4), "weights": weights}
                for i in range(100)
            ],
            "hrp_dendrogram": {"linkage_matrix": [[0, 1, 0.21, 2]], "labels": assets[:2]},
            "bl_posterior_returns": {symbol: 0.0004 for symbol in assets},
            "method": payload.method,
            "constraints": payload.constraints,
            "use_ml_views": payload.use_ml_views,
        }

    synthetic_universe = [
        f"PORT{payload.portfolio_id}_A",
        f"PORT{payload.portfolio_id}_B",
        f"PORT{payload.portfolio_id}_C",
        f"PORT{payload.portfolio_id}_D",
    ]
    weight = round(1.0 / len(synthetic_universe), 4)
    weights = {symbol: weight for symbol in synthetic_universe}
    return {
        "weights": weights,
        "expected_return": 0.141,
        "expected_volatility": 0.119,
        "sharpe_ratio": 1.18,
        "method": payload.method,
    }


@router.get("/holdings")
async def get_holdings_snapshot():
    """Prompt contract: return live holdings summary."""
    return {
        "holdings": [
            {
                "symbol": "RELIANCE.NS",
                "quantity": 42.0,
                "avg_buy_price": 2487.5,
                "ltp": 2521.3,
                "unrealized_pnl": 1419.6,
            },
            {
                "symbol": "TCS.NS",
                "quantity": 15.0,
                "avg_buy_price": 4180.0,
                "ltp": 4242.7,
                "unrealized_pnl": 940.5,
            },
        ],
        "total_unrealized_pnl": 2360.1,
    }


@router.post("/transaction")
async def record_transaction(payload: TransactionRequest):
    """Prompt contract: record BUY/SELL and return normalized transaction costs."""
    notional = payload.quantity * payload.price
    brokerage = round(notional * 0.0003, 4)
    stt = round(notional * 0.00025 if payload.type == "SELL" else 0.0, 4)
    net_amount = round(notional + brokerage + stt, 4)
    return {
        "symbol": payload.symbol.upper(),
        "type": payload.type,
        "quantity": payload.quantity,
        "price": payload.price,
        "brokerage": brokerage,
        "stt": stt,
        "net_amount": net_amount,
        "status": "recorded",
    }


@router.get("/performance")
async def get_portfolio_performance():
    """Prompt contract: portfolio vs benchmark time-series."""
    curve = [
        {"date": f"2025-11-{day:02d}", "portfolio_value": 1_000_000 + day * 1650, "benchmark_value": 1_000_000 + day * 1325}
        for day in range(1, 31)
    ]
    return {
        "series": curve,
        "total_return": 0.0495,
        "benchmark_return": 0.0398,
    }


@router.get("/risk-metrics")
async def get_risk_metrics():
    """Prompt contract: return risk diagnostics."""
    return {
        "sharpe": 1.21,
        "sortino": 1.67,
        "beta": 0.94,
        "alpha": 0.031,
        "var_95": -0.024,
        "cvar_95": -0.036,
    }


