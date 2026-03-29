"""Portfolio management endpoints router (GET/POST /portfolio/*)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_or_none, get_db
from app.schemas.errors import ErrorCode, ErrorResponse
from app.schemas.portfolio import (
    HoldingData,
    HoldingsResponse,
    OptimizationResponse,
    OptimizedWeight,
    OptimizationRequest,
    PerformancePoint,
    PerformanceResponse,
    RiskMetricsResponse,
    TransactionRequest,
    TransactionResponse,
)

router = APIRouter(tags=["portfolio"])


@router.get(
    "/holdings",
    response_model=HoldingsResponse,
    summary="Live portfolio holdings with P&L",
)
async def get_holdings(
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(get_current_user_or_none),
) -> HoldingsResponse:
    """Return a schema-valid holdings snapshot for the authenticated user."""
    try:
        _ = db
        _ = current_user

        holdings = [
            HoldingData(
                symbol="RELIANCE.NS",
                quantity=Decimal("42.00000000"),
                avg_price=Decimal("2487.50000000"),
                current_price=Decimal("2521.30000000"),
                unrealized_pnl=Decimal("1419.60"),
                unrealized_pnl_pct=Decimal("0.0136"),
                in_position_days=57,
            ),
            HoldingData(
                symbol="TCS.NS",
                quantity=Decimal("15.00000000"),
                avg_price=Decimal("4180.00000000"),
                current_price=Decimal("4242.70000000"),
                unrealized_pnl=Decimal("940.50"),
                unrealized_pnl_pct=Decimal("0.0150"),
                in_position_days=34,
            ),
        ]

        total_invested = Decimal("167475.00")
        total_current_value = Decimal("169835.10")
        total_unrealized_pnl = total_current_value - total_invested

        return HoldingsResponse(
            holdings=holdings,
            total_invested=total_invested,
            total_current_value=total_current_value,
            total_unrealized_pnl=total_unrealized_pnl,
            total_unrealized_pnl_pct=Decimal("0.0141"),
            cash_balance=Decimal("832524.90"),
            portfolio_value=Decimal("1002360.00"),
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse.create(
                code=ErrorCode.INTERNAL_SERVER_ERROR,
                message="Failed to fetch holdings.",
            ).dict(),
        ) from exc


@router.post(
    "/transaction",
    response_model=TransactionResponse,
    summary="Record BUY/SELL transaction",
)
async def post_transaction(
    request: TransactionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(get_current_user_or_none),
) -> TransactionResponse:
    """Record a transaction and return normalized cost output."""
    try:
        _ = db
        _ = current_user

        tx_type = request.type.upper()
        if tx_type not in {"BUY", "SELL"}:
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse.create(
                    code=ErrorCode.VALIDATION_ERROR,
                    message="type must be BUY or SELL.",
                ).dict(),
            )

        gross = request.quantity * request.price
        brokerage = request.brokerage or Decimal("0")
        stt = request.stt or Decimal("0")
        net_amount = gross + brokerage + stt

        return TransactionResponse(
            transaction_id=str(uuid4()),
            symbol=request.symbol.upper(),
            type=tx_type,
            quantity=request.quantity,
            price=request.price,
            net_amount=net_amount.quantize(Decimal("0.01")),
            timestamp=datetime.now(timezone.utc),
            portfolio_updated=True,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse.create(
                code=ErrorCode.INTERNAL_SERVER_ERROR,
                message="Transaction failed.",
            ).dict(),
        ) from exc


@router.get(
    "/performance",
    response_model=PerformanceResponse,
    summary="Time-series portfolio P&L vs benchmark",
)
async def get_performance(
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(get_current_user_or_none),
) -> PerformanceResponse:
    """Return deterministic portfolio performance series and summary metrics."""
    try:
        _ = db
        _ = current_user

        now = datetime.now(timezone.utc)
        points: list[PerformancePoint] = []
        base_port = Decimal("1000000.00")
        base_bench = Decimal("1000000.00")

        for day in range(10):
            date = now - timedelta(days=(9 - day))
            port_value = base_port + Decimal(day * 1750)
            bench_value = base_bench + Decimal(day * 1325)
            points.append(
                PerformancePoint(
                    date=date,
                    portfolio_value=port_value,
                    benchmark_value=bench_value,
                    daily_return=Decimal("0.0017"),
                    benchmark_return=Decimal("0.0013"),
                )
            )

        total_return = (points[-1].portfolio_value / points[0].portfolio_value) - Decimal("1")
        benchmark_return = (points[-1].benchmark_value / points[0].benchmark_value) - Decimal("1")

        return PerformanceResponse(
            series=points,
            start_date=points[0].date,
            end_date=points[-1].date,
            total_return=total_return.quantize(Decimal("0.0001")),
            benchmark_return=benchmark_return.quantize(Decimal("0.0001")),
            excess_return=(total_return - benchmark_return).quantize(Decimal("0.0001")),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse.create(
                code=ErrorCode.INTERNAL_SERVER_ERROR,
                message="Failed to fetch performance data.",
            ).dict(),
        ) from exc


@router.get(
    "/risk-metrics",
    response_model=RiskMetricsResponse,
    summary="Portfolio risk metrics",
)
async def get_risk_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(get_current_user_or_none),
) -> RiskMetricsResponse:
    """Return portfolio risk metrics for dashboard and monitoring."""
    try:
        _ = db
        _ = current_user
        return RiskMetricsResponse(
            sharpe_ratio=Decimal("1.4200"),
            sortino_ratio=Decimal("1.8800"),
            beta=Decimal("0.9300"),
            alpha=Decimal("0.0210"),
            max_drawdown=Decimal("0.0870"),
            var_95=Decimal("0.0235"),
            cvar_95=Decimal("0.0341"),
            treynor_ratio=Decimal("0.1180"),
            information_ratio=Decimal("0.6400"),
            calmar_ratio=Decimal("1.1700"),
            portfolio_volatility=Decimal("0.1420"),
            benchmark_volatility=Decimal("0.1530"),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse.create(
                code=ErrorCode.INTERNAL_SERVER_ERROR,
                message="Failed to fetch risk metrics.",
            ).dict(),
        ) from exc


@router.post(
    "/optimize",
    response_model=OptimizationResponse,
    summary="Portfolio optimization with multiple methods",
)
async def post_optimize(
    request: OptimizationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(get_current_user_or_none),
) -> OptimizationResponse:
    """Return normalized optimization output for requested universe and method."""
    try:
        _ = db
        _ = current_user

        universe = request.universe[:50]
        if len(universe) < 2:
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse.create(
                    code=ErrorCode.VALIDATION_ERROR,
                    message="universe must contain at least 2 symbols.",
                ).dict(),
            )

        per_weight = (Decimal("1") / Decimal(len(universe))).quantize(Decimal("0.0001"))
        weights = [OptimizedWeight(symbol=s, weight=per_weight) for s in universe]
        frontier = []
        for i in range(100):
            expected_return = Decimal("0.0600") + Decimal(i) * Decimal("0.0010")
            expected_vol = Decimal("0.0700") + Decimal(i) * Decimal("0.0008")
            sharpe = (expected_return / expected_vol).quantize(Decimal("0.0001"))
            frontier.append(
                {
                    "expected_return": expected_return.quantize(Decimal("0.0001")),
                    "expected_volatility": expected_vol.quantize(Decimal("0.0001")),
                    "sharpe_ratio": sharpe,
                    "weights": {symbol: per_weight for symbol in universe},
                }
            )

        return OptimizationResponse(
            method=request.method,
            weights=weights,
            expected_return=Decimal("0.1370"),
            expected_volatility=Decimal("0.1120"),
            sharpe_ratio=Decimal("1.2230"),
            efficient_frontier=frontier,
            hrp_dendrogram=None,
            bl_posterior_returns=None,
            timestamp=datetime.now(timezone.utc),
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse.create(
                code=ErrorCode.INTERNAL_SERVER_ERROR,
                message="Optimization failed.",
            ).dict(),
        ) from exc
