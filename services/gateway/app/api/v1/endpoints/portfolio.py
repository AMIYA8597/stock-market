"""
Portfolio management endpoints.
"""

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user_with_permissions
from app.core.database import get_db
from app.schemas.portfolio import (
    OptimizationRequest,
    OptimizationResponse,
    PortfolioCreate,
    PortfolioResponse,
    PortfolioSummaryResponse,
    RebalanceRequest,
    RebalanceResponse,
)
from app.services.portfolio_service import PortfolioService

router = APIRouter()
portfolio_service = PortfolioService()


@router.post("/", response_model=PortfolioResponse)
async def create_portfolio(
    portfolio_data: PortfolioCreate,
    current_user: dict = Depends(get_current_user_with_permissions),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new portfolio.
    """
    return await portfolio_service.create_portfolio(portfolio_data, current_user["user_id"], db)


@router.get("/", response_model=List[PortfolioResponse])
async def list_portfolios(
    current_user: dict = Depends(get_current_user_with_permissions),
    db: AsyncSession = Depends(get_db)
):
    """
    List user portfolios.
    """
    return await portfolio_service.list_portfolios(current_user["user_id"], db)


@router.get("/{portfolio_id}", response_model=PortfolioSummaryResponse)
async def get_portfolio_summary(
    portfolio_id: str,
    current_user: dict = Depends(get_current_user_with_permissions),
    db: AsyncSession = Depends(get_db)
):
    """
    Get portfolio summary with holdings and performance.
    """
    portfolio = await portfolio_service.get_portfolio(portfolio_id, current_user["user_id"], db)

    # Convert to summary format
    return PortfolioSummaryResponse(
        portfolio=PortfolioResponse(
            id=portfolio.id,
            user_id=portfolio.user_id,
            name=portfolio.name,
            description=portfolio.description,
            is_default=portfolio.is_default,
            created_at=datetime.fromisoformat(portfolio.created_at),
            updated_at=datetime.fromisoformat(portfolio.updated_at)
        ),
        holdings=portfolio.holdings,
        total_value=portfolio.total_value,
        total_cost=portfolio.total_cost_basis,
        total_pnl=portfolio.total_pnl,
        total_pnl_percent=portfolio.total_pnl_percent,
        day_pnl=0.0,  # TODO: Calculate daily P&L
        day_pnl_percent=0.0
    )


@router.put("/{portfolio_id}", response_model=PortfolioResponse)
async def update_portfolio(
    portfolio_id: str,
    portfolio_data: PortfolioCreate,  # Using same schema for update
    current_user: dict = Depends(get_current_user_with_permissions),
    db: AsyncSession = Depends(get_db)
):
    """
    Update portfolio.
    """
    # Convert to update format
    update_data = {
        "name": portfolio_data.name,
        "description": portfolio_data.description,
        "risk_tolerance": portfolio_data.risk_tolerance,
        "investment_horizon": portfolio_data.investment_horizon,
        "strategy": portfolio_data.strategy
    }

    return await portfolio_service.update_portfolio(portfolio_id, update_data, current_user["user_id"], db)


@router.delete("/{portfolio_id}")
async def delete_portfolio(
    portfolio_id: str,
    current_user: dict = Depends(get_current_user_with_permissions),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete portfolio.
    """
    return await portfolio_service.delete_portfolio(portfolio_id, current_user["user_id"], db)


@router.post("/{portfolio_id}/optimize", response_model=OptimizationResponse)
async def optimize_portfolio(
    portfolio_id: str,
    optimization_data: OptimizationRequest,
    current_user: dict = Depends(get_current_user_with_permissions),
    db: AsyncSession = Depends(get_db)
):
    """
    Optimize portfolio weights.
    """
    return await portfolio_service.optimize_portfolio(optimization_data, current_user["user_id"], db)


@router.post("/{portfolio_id}/rebalance", response_model=RebalanceResponse)
async def rebalance_portfolio(
    portfolio_id: str,
    rebalance_data: RebalanceRequest,
    current_user: dict = Depends(get_current_user_with_permissions),
    db: AsyncSession = Depends(get_db)
):
    """
    Rebalance portfolio to target weights.
    """
    return await portfolio_service.rebalance_portfolio(portfolio_id, rebalance_data, current_user["user_id"], db)