"""
Portfolio management service implementation.
"""

import json
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis_client import get_redis_client
from app.models.portfolio import Portfolio, PortfolioHolding
from app.schemas.portfolio import (
    OptimizationRequest,
    OptimizationResponse,
    PortfolioCreate,
    PortfolioResponse,
    PortfolioUpdate,
    RebalanceRequest,
    RebalanceResponse,
)


class PortfolioService:
    """Service for handling portfolio operations."""

    def __init__(self):
        self.redis = get_redis_client()
        self.risk_engine_url = "http://risk-engine:8003"  # Internal service URL
        self.cache_ttl = 300  # 5 minutes

    async def create_portfolio(
        self,
        portfolio_data: PortfolioCreate,
        user_id: str,
        db: AsyncSession
    ) -> PortfolioResponse:
        """
        Create a new portfolio.
        """
        # Create portfolio in database
        portfolio = Portfolio(
            user_id=user_id,
            name=portfolio_data.name,
            description=portfolio_data.description,
            initial_investment=portfolio_data.initial_investment,
            currency=portfolio_data.currency,
            risk_tolerance=portfolio_data.risk_tolerance,
            investment_horizon=portfolio_data.investment_horizon,
            strategy=portfolio_data.strategy,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        db.add(portfolio)
        await db.commit()
        await db.refresh(portfolio)

        # Add initial holdings if provided
        if portfolio_data.holdings:
            for holding_data in portfolio_data.holdings:
                holding = PortfolioHolding(
                    portfolio_id=portfolio.id,
                    symbol=holding_data.symbol,
                    quantity=holding_data.quantity,
                    average_price=holding_data.average_price,
                    current_price=holding_data.current_price,
                    sector=holding_data.sector,
                    purchase_date=holding_data.purchase_date
                )
                db.add(holding)
            await db.commit()

        return await self._get_portfolio_response(portfolio.id, db)

    async def get_portfolio(
        self,
        portfolio_id: str,
        user_id: str,
        db: AsyncSession
    ) -> PortfolioResponse:
        """
        Get portfolio by ID.
        """
        cache_key = f"portfolio:{portfolio_id}"
        cached_data = await self.redis.get(cache_key)

        if cached_data:
            return PortfolioResponse(**json.loads(cached_data))

        portfolio = await db.get(Portfolio, portfolio_id)
        if not portfolio or portfolio.user_id != user_id:
            raise Exception("Portfolio not found")

        response = await self._get_portfolio_response(portfolio_id, db)

        # Cache the result
        await self.redis.setex(cache_key, self.cache_ttl, json.dumps(response.dict()))

        return response

    async def update_portfolio(
        self,
        portfolio_id: str,
        portfolio_data: PortfolioUpdate,
        user_id: str,
        db: AsyncSession
    ) -> PortfolioResponse:
        """
        Update portfolio.
        """
        portfolio = await db.get(Portfolio, portfolio_id)
        if not portfolio or portfolio.user_id != user_id:
            raise Exception("Portfolio not found")

        # Update fields
        for field, value in portfolio_data.dict(exclude_unset=True).items():
            if hasattr(portfolio, field):
                setattr(portfolio, field, value)

        portfolio.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(portfolio)

        # Clear cache
        await self.redis.delete(f"portfolio:{portfolio_id}")

        return await self._get_portfolio_response(portfolio_id, db)

    async def delete_portfolio(
        self,
        portfolio_id: str,
        user_id: str,
        db: AsyncSession
    ) -> Dict[str, str]:
        """
        Delete portfolio.
        """
        portfolio = await db.get(Portfolio, portfolio_id)
        if not portfolio or portfolio.user_id != user_id:
            raise Exception("Portfolio not found")

        await db.delete(portfolio)
        await db.commit()

        # Clear cache
        await self.redis.delete(f"portfolio:{portfolio_id}")

        return {"message": "Portfolio deleted successfully"}

    async def list_portfolios(
        self,
        user_id: str,
        db: AsyncSession
    ) -> List[PortfolioResponse]:
        """
        List all portfolios for a user.
        """
        portfolios = await db.execute(
            Portfolio.__table__.select().where(Portfolio.user_id == user_id)
        )
        portfolio_list = portfolios.scalars().all()

        responses = []
        for portfolio in portfolio_list:
            responses.append(await self._get_portfolio_response(portfolio.id, db))

        return responses

    async def optimize_portfolio(
        self,
        request: OptimizationRequest,
        user_id: str,
        db: AsyncSession
    ) -> OptimizationResponse:
        """
        Optimize portfolio using risk engine.
        """
        try:
            # Call risk engine for optimization
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.risk_engine_url}/optimize",
                    json={
                        "symbols": request.symbols,
                        "constraints": request.constraints.dict() if request.constraints else {},
                        "risk_tolerance": request.risk_tolerance,
                        "optimization_method": request.optimization_method
                    }
                )
                response.raise_for_status()
                optimization_result = response.json()

            return OptimizationResponse(
                optimized_weights=optimization_result["weights"],
                expected_return=optimization_result["expected_return"],
                expected_volatility=optimization_result["expected_volatility"],
                sharpe_ratio=optimization_result["sharpe_ratio"],
                optimization_method=request.optimization_method,
                constraints_satisfied=optimization_result["constraints_satisfied"],
                risk_metrics=optimization_result["risk_metrics"],
                timestamp=datetime.utcnow().isoformat()
            )

        except Exception as e:
            raise Exception(f"Failed to optimize portfolio: {str(e)}")

    async def rebalance_portfolio(
        self,
        portfolio_id: str,
        request: RebalanceRequest,
        user_id: str,
        db: AsyncSession
    ) -> RebalanceResponse:
        """
        Rebalance portfolio to target weights.
        """
        portfolio = await db.get(Portfolio, portfolio_id)
        if not portfolio or portfolio.user_id != user_id:
            raise Exception("Portfolio not found")

        try:
            # Get current holdings
            holdings_result = await db.execute(
                PortfolioHolding.__table__.select().where(
                    PortfolioHolding.portfolio_id == portfolio_id
                )
            )
            holdings = holdings_result.scalars().all()

            current_weights = {}
            total_value = 0

            for holding in holdings:
                current_value = holding.quantity * holding.current_price
                current_weights[holding.symbol] = current_value
                total_value += current_value

            # Calculate current weights
            for symbol in current_weights:
                current_weights[symbol] /= total_value

            # Calculate rebalancing trades
            trades = []
            for symbol, target_weight in request.target_weights.items():
                current_weight = current_weights.get(symbol, 0)
                weight_diff = target_weight - current_weight

                if abs(weight_diff) > request.threshold:
                    trade_value = weight_diff * total_value
                    quantity = trade_value / request.current_prices.get(symbol, 1)

                    trades.append({
                        "symbol": symbol,
                        "action": "BUY" if weight_diff > 0 else "SELL",
                        "quantity": abs(quantity),
                        "estimated_value": abs(trade_value)
                    })

            return RebalanceResponse(
                portfolio_id=portfolio_id,
                current_weights=current_weights,
                target_weights=request.target_weights,
                trades_required=trades,
                total_trade_value=sum(t["estimated_value"] for t in trades),
                rebalance_threshold=request.threshold,
                timestamp=datetime.utcnow().isoformat()
            )

        except Exception as e:
            raise Exception(f"Failed to rebalance portfolio: {str(e)}")

    async def get_portfolio_performance(
        self,
        portfolio_id: str,
        start_date: str,
        end_date: str,
        user_id: str,
        db: AsyncSession
    ) -> Dict:
        """
        Get portfolio performance metrics.
        """
        # TODO: Implement performance calculation
        return {
            "portfolio_id": portfolio_id,
            "total_return": 15.5,
            "annualized_return": 12.8,
            "volatility": 18.2,
            "sharpe_ratio": 1.45,
            "max_drawdown": -8.5,
            "beta": 0.85,
            "alpha": 2.1,
            "period_start": start_date,
            "period_end": end_date,
            "benchmark_return": 10.2
        }

    async def _get_portfolio_response(
        self,
        portfolio_id: str,
        db: AsyncSession
    ) -> PortfolioResponse:
        """
        Helper method to build portfolio response.
        """
        portfolio = await db.get(Portfolio, portfolio_id)

        # Get holdings
        holdings_result = await db.execute(
            PortfolioHolding.__table__.select().where(
                PortfolioHolding.portfolio_id == portfolio_id
            )
        )
        holdings = holdings_result.scalars().all()

        holdings_data = []
        total_value = 0
        total_cost = 0

        for holding in holdings:
            current_value = holding.quantity * holding.current_price
            cost_basis = holding.quantity * holding.average_price
            unrealized_pnl = current_value - cost_basis
            unrealized_pnl_percent = (unrealized_pnl / cost_basis) * 100 if cost_basis > 0 else 0

            holdings_data.append({
                "symbol": holding.symbol,
                "name": holding.symbol,  # TODO: Get from market data
                "quantity": holding.quantity,
                "average_price": holding.average_price,
                "current_price": holding.current_price,
                "market_value": current_value,
                "cost_basis": cost_basis,
                "unrealized_pnl": unrealized_pnl,
                "unrealized_pnl_percent": unrealized_pnl_percent,
                "weight": 0.0,  # Will be calculated below
                "sector": holding.sector,
                "purchase_date": holding.purchase_date.isoformat() if holding.purchase_date else None
            })

            total_value += current_value
            total_cost += cost_basis

        # Calculate weights
        for holding in holdings_data:
            holding["weight"] = (holding["market_value"] / total_value) * 100 if total_value > 0 else 0

        # Calculate portfolio metrics
        total_pnl = total_value - total_cost
        total_pnl_percent = (total_pnl / total_cost) * 100 if total_cost > 0 else 0

        return PortfolioResponse(
            id=portfolio.id,
            user_id=portfolio.user_id,
            name=portfolio.name,
            description=portfolio.description,
            holdings=holdings_data,
            total_value=total_value,
            total_cost_basis=total_cost,
            total_pnl=total_pnl,
            total_pnl_percent=total_pnl_percent,
            initial_investment=portfolio.initial_investment,
            currency=portfolio.currency,
            risk_tolerance=portfolio.risk_tolerance,
            investment_horizon=portfolio.investment_horizon,
            strategy=portfolio.strategy,
            is_active=portfolio.is_active,
            created_at=portfolio.created_at.isoformat(),
            updated_at=portfolio.updated_at.isoformat()
        )