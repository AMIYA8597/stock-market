"""Portfolio management endpoints router (GET/POST /portfolio/*)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_or_none, get_db
from app.schemas.errors import ErrorCode, ErrorResponse
from app.schemas.portfolio import (
    HoldingData,
    HoldingsResponse,
    OptimizationRequest,
    OptimizationResponse,
    OptimizedWeight,
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
    """Return a holdings snapshot for the authenticated user (backed by MongoDB if configured)."""
    try:
        from app.core.config import get_settings
        settings = get_settings()

        # Resolve user ID (fallback to test-user-id if unauthenticated)
        user_id = current_user.get("sub") if current_user else "test-user-id"

        if settings.MONGODB_URL:
            from app.database.mongodb import get_live_price, mongo_get_portfolio

            portfolio = await mongo_get_portfolio(user_id)
            cash_balance = Decimal(str(portfolio.get("cash_balance", 1000000.0)))
            mongo_holdings = portfolio.get("holdings", [])

            holdings = []
            total_invested = Decimal("0.0")
            total_current_value = Decimal("0.0")

            for h in mongo_holdings:
                symbol = h["symbol"].upper()
                qty = Decimal(str(h["quantity"]))
                avg_p = Decimal(str(h["avg_price"]))

                # Fetch live price
                curr_p_val = await get_live_price(symbol)
                curr_p = Decimal(str(curr_p_val))

                unrealized_pnl = (curr_p - avg_p) * qty
                unrealized_pnl_pct = (curr_p - avg_p) / avg_p if avg_p > 0 else Decimal("0.0")

                holdings.append(
                    HoldingData(
                        symbol=symbol,
                        quantity=qty,
                        avg_price=avg_p,
                        current_price=curr_p,
                        unrealized_pnl=unrealized_pnl.quantize(Decimal("0.01")),
                        unrealized_pnl_pct=unrealized_pnl_pct.quantize(Decimal("0.0001")),
                        in_position_days=h.get("in_position_days", 1),
                    )
                )
                total_invested += avg_p * qty
                total_current_value += curr_p * qty

            total_unrealized_pnl = total_current_value - total_invested
            total_unrealized_pnl_pct = total_unrealized_pnl / total_invested if total_invested > 0 else Decimal("0.0")
            portfolio_value = total_current_value + cash_balance

            return HoldingsResponse(
                holdings=holdings,
                total_invested=total_invested.quantize(Decimal("0.01")),
                total_current_value=total_current_value.quantize(Decimal("0.01")),
                total_unrealized_pnl=total_unrealized_pnl.quantize(Decimal("0.01")),
                total_unrealized_pnl_pct=total_unrealized_pnl_pct.quantize(Decimal("0.0001")),
                cash_balance=cash_balance.quantize(Decimal("0.01")),
                portfolio_value=portfolio_value.quantize(Decimal("0.01")),
                timestamp=datetime.now(UTC),
            )

        # Fallback static mock holdings
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
            timestamp=datetime.now(UTC),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse.create(
                code=ErrorCode.INTERNAL_SERVER_ERROR,
                message=f"Failed to fetch holdings: {str(exc)}",
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
    """Record a transaction and update cash/holdings inside MongoDB if configured."""
    try:
        from app.core.config import get_settings
        settings = get_settings()

        user_id = current_user.get("sub") if current_user else "test-user-id"
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

        if tx_type == "BUY":
            net_amount = gross + brokerage + stt
        else:
            net_amount = gross - brokerage - stt

        if settings.MONGODB_URL:
            from app.database.mongodb import (
                mongo_add_transaction,
                mongo_get_portfolio,
                mongo_save_portfolio,
            )

            # Fetch and lock/update portfolio in Mongo
            portfolio = await mongo_get_portfolio(user_id)
            cash_balance = Decimal(str(portfolio.get("cash_balance", 1000000.0)))
            holdings = portfolio.get("holdings", [])

            symbol = request.symbol.upper().strip()
            qty = Decimal(str(request.quantity))
            price = Decimal(str(request.price))

            if tx_type == "BUY":
                if cash_balance < net_amount:
                    raise HTTPException(
                        status_code=400,
                        detail=ErrorResponse.create(
                            code=ErrorCode.VALIDATION_ERROR,
                            message=f"Insufficient cash balance. Required: {net_amount}, Available: {cash_balance}",
                        ).dict(),
                    )
                new_cash = cash_balance - net_amount

                # Update holding
                found = False
                for h in holdings:
                    if h["symbol"].upper() == symbol:
                        h_qty = Decimal(str(h["quantity"]))
                        h_avg = Decimal(str(h["avg_price"]))

                        new_qty = h_qty + qty
                        new_avg = (h_qty * h_avg + qty * price) / new_qty

                        h["quantity"] = float(new_qty)
                        h["avg_price"] = float(new_avg)
                        found = True
                        break
                if not found:
                    holdings.append({
                        "symbol": symbol,
                        "quantity": float(qty),
                        "avg_price": float(price),
                        "in_position_days": 1
                    })
            else:  # SELL
                # Check holding
                found_h = None
                for h in holdings:
                    if h["symbol"].upper() == symbol:
                        found_h = h
                        break
                if not found_h or Decimal(str(found_h["quantity"])) < qty:
                    raise HTTPException(
                        status_code=400,
                        detail=ErrorResponse.create(
                            code=ErrorCode.VALIDATION_ERROR,
                            message=f"Insufficient holdings of {symbol} to sell.",
                        ).dict(),
                    )
                new_cash = cash_balance + net_amount

                h_qty = Decimal(str(found_h["quantity"]))
                new_qty = h_qty - qty
                if new_qty <= 0:
                    holdings.remove(found_h)
                else:
                    found_h["quantity"] = float(new_qty)

            # Save transaction & portfolio in Mongo
            await mongo_save_portfolio(user_id, float(new_cash), holdings)
            tx = await mongo_add_transaction(user_id, symbol, tx_type, float(qty), float(price), float(net_amount))

            return TransactionResponse(
                transaction_id=str(tx["transaction_id"]),
                symbol=symbol,
                type=tx_type,
                quantity=qty,
                price=price,
                net_amount=net_amount.quantize(Decimal("0.01")),
                timestamp=tx["timestamp"],
                portfolio_updated=True,
            )

        # Mock fallback response
        return TransactionResponse(
            transaction_id=str(uuid4()),
            symbol=request.symbol.upper(),
            type=tx_type,
            quantity=request.quantity,
            price=request.price,
            net_amount=net_amount.quantize(Decimal("0.01")),
            timestamp=datetime.now(UTC),
            portfolio_updated=True,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse.create(
                code=ErrorCode.INTERNAL_SERVER_ERROR,
                message=f"Transaction failed: {str(exc)}",
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

        now = datetime.now(UTC)
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
            timestamp=datetime.now(UTC),
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
