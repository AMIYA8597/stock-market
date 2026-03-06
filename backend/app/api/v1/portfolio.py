"""
Portfolio management API endpoints.

Core CRUD implemented in Phase 1. Optimization + risk in Phase 5.
"""

from __future__ import annotations

from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
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
async def optimize_portfolio(payload: OptimizeRequest):
    """Optimize portfolio allocation. (Phase 5)"""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Portfolio optimization not yet implemented — coming in Phase 5",
    )
