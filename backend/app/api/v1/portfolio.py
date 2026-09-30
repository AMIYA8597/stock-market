"""Portfolio management endpoints router (GET/POST /portfolio/*)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.core.entitlements import require_feature
from app.core.numeric import safe_round
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
    "",
    summary="List portfolios for user",
)
async def list_portfolios(
    current_user: dict | None = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    import uuid

    from sqlalchemy import select

    from app.models.paper_trading import PaperWallet

    uid = uuid.UUID(str(current_user.id))
    deposits_res = await db.execute(
        select(PaperWallet.balance).where(PaperWallet.user_id == uid)
    )
    # scalar_one() raises when a brand-new user has no PaperWallet row yet
    # (nothing to fall back to via `or 0.0` if it never returns) - that was
    # a 500 on every first /portfolio call for a freshly created account.
    balance = deposits_res.scalar_one_or_none()
    initial_cap = float(balance) if balance is not None else 0.0

    holdings = await get_holdings(current_user=current_user, db=db)

    return [
        {
            "id": 1,
            "user_id": str(current_user.id),
            "name": "Main Portfolio",
            "description": "Primary trading portfolio",
            "initial_capital": initial_cap,
            "total_value": float(holdings.portfolio_value),
            "cash_balance": float(holdings.cash_balance),
            "holdings": [h.model_dump() for h in holdings.holdings],
            "created_at": holdings.timestamp.isoformat(),
            "updated_at": holdings.timestamp.isoformat(),
        }
    ]


@router.get(
    "/holdings",
    response_model=HoldingsResponse,
    summary="Live portfolio holdings with P&L",
)
async def get_holdings(
    current_user: dict | None = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HoldingsResponse:
    """Return a holdings snapshot for the authenticated user."""
    try:
        import uuid

        from sqlalchemy import select

        from app.models.paper_trading import PaperPosition, PaperWallet
        from app.services.market_data_service import MarketDataService

        if not current_user:
            raise HTTPException(status_code=401, detail="Unauthorized")
        user_id_str = str(current_user.id)

        def _empty_holdings(cb: Decimal = Decimal("0.00")) -> HoldingsResponse:
            return HoldingsResponse(
                holdings=[],
                total_invested=Decimal("0.00"),
                total_current_value=Decimal("0.00"),
                total_unrealized_pnl=Decimal("0.00"),
                total_unrealized_pnl_pct=Decimal("0.0000"),
                cash_balance=cb,
                portfolio_value=cb,
                timestamp=datetime.now(UTC),
            )

        try:
            uid = uuid.UUID(user_id_str)
        except ValueError:
            return _empty_holdings()

        # Cash balance and holdings are read from the single, real paper-trading
        # ledger (PaperWallet/PaperPosition) that PaperTradingService already
        # maintains on every order fill, rather than a separate, never-written
        # deposit/transaction ledger.
        wallet_res = await db.execute(select(PaperWallet).where(PaperWallet.user_id == uid))
        wallet = wallet_res.scalar_one_or_none()
        cash_balance = Decimal(str(wallet.balance)) if wallet else Decimal("0.00")
        cash_balance = cash_balance.quantize(Decimal("0.01"))

        pos_res = await db.execute(select(PaperPosition).where(PaperPosition.user_id == uid))
        rows = pos_res.scalars().all()

        if not rows:
            return _empty_holdings(cash_balance)

        holdings = []
        total_invested = Decimal("0.0")
        total_current_value = Decimal("0.0")

        for position in rows:
            ticker = position.symbol
            qty = Decimal(str(position.quantity))
            avg_p = Decimal(str(position.avg_buy_price))

            try:
                quote = await MarketDataService.get_quote(ticker)
                curr_p_val = quote.get("price")
                curr_p = Decimal(str(curr_p_val)) if curr_p_val else avg_p
            except Exception:
                curr_p = avg_p

            unrealized_pnl = (curr_p - avg_p) * qty
            unrealized_pnl_pct = (curr_p - avg_p) / avg_p if avg_p > 0 else Decimal("0.0")

            days_held = max(
                1, (datetime.now(UTC) - position.updated_at.replace(tzinfo=UTC)).days
            )

            holdings.append(
                HoldingData(
                    symbol=ticker.upper(),
                    quantity=qty,
                    avg_price=avg_p.quantize(Decimal("0.01")),
                    current_price=curr_p.quantize(Decimal("0.01")),
                    unrealized_pnl=unrealized_pnl.quantize(Decimal("0.01")),
                    unrealized_pnl_pct=unrealized_pnl_pct.quantize(Decimal("0.0001")),
                    in_position_days=days_held,
                )
            )
            total_invested += avg_p * qty
            total_current_value += curr_p * qty

        total_unrealized_pnl = total_current_value - total_invested
        total_unrealized_pnl_pct = (
            total_unrealized_pnl / total_invested if total_invested > 0 else Decimal("0.0")
        )
        portfolio_value = total_current_value + cash_balance

        return HoldingsResponse(
            holdings=holdings,
            total_invested=total_invested.quantize(Decimal("0.01")),
            total_current_value=total_current_value.quantize(Decimal("0.01")),
            total_unrealized_pnl=total_unrealized_pnl.quantize(Decimal("0.01")),
            total_unrealized_pnl_pct=total_unrealized_pnl_pct.quantize(Decimal("0.0001")),
            cash_balance=cash_balance,
            portfolio_value=portfolio_value.quantize(Decimal("0.01")),
            timestamp=datetime.now(UTC),
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse.create(
                code=ErrorCode.INTERNAL_SERVER_ERROR,
                message=f"Failed to fetch holdings: {str(exc)}"[:500],
            ).dict(),
        ) from exc


@router.get(
    "/performance",
    response_model=PerformanceResponse,
    summary="Time-series portfolio P&L vs benchmark",
)
async def get_performance(
    current_user: dict | None = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PerformanceResponse:
    """Return time-series portfolio performance based on live data and current holdings."""
    try:
        from app.services.market_data_service import MarketDataService

        holdings_res = await get_holdings(current_user=current_user, db=db)
        now = datetime.now(UTC)
        points: list[PerformancePoint] = []

        # Determine base portfolio values for the last 10 days
        # We will fetch 1mo history for each holding
        histories = {}
        for h in holdings_res.holdings:
            try:
                hist = await MarketDataService.get_history(h.symbol, interval="1d", period="1mo")
                histories[h.symbol] = hist
            except Exception:
                pass

        try:
            bench_hist = await MarketDataService.get_history("^NSEI", interval="1d", period="1mo")
        except Exception:
            bench_hist = []

        # Find the last 10 valid market dates from the benchmark
        # Extract dates as strings to match
        bench_dates = []
        bench_prices = {}
        for b in bench_hist:
            d = b.get("timestamp") or b.get("time")
            if d:
                # Parse timestamp safely
                try:
                    if isinstance(d, (int, float)):
                        dt = datetime.fromtimestamp(d, tz=UTC)
                    else:
                        dt = datetime.fromisoformat(str(d).replace("Z", "+00:00"))
                    date_str = dt.strftime("%Y-%m-%d")
                    bench_dates.append((dt, date_str, float(b.get("close", 0))))
                    bench_prices[date_str] = float(b.get("close", 0))
                except Exception:
                    pass

        bench_dates.sort(key=lambda x: x[0])
        last_10 = bench_dates[-10:] if bench_dates else []

        if not last_10:
            # Fallback to generated dates if benchmark fails
            for day in range(10):
                d = now - timedelta(days=(9 - day))
                date_str = d.strftime("%Y-%m-%d")
                last_10.append((d, date_str, 100000.0))

        # Build price maps for each symbol
        sym_prices = {}
        for sym, hist in histories.items():
            sym_prices[sym] = {}
            for b in hist:
                d = b.get("timestamp") or b.get("time")
                if d:
                    try:
                        if isinstance(d, (int, float)):
                            dt = datetime.fromtimestamp(d, tz=UTC)
                        else:
                            dt = datetime.fromisoformat(str(d).replace("Z", "+00:00"))
                        date_str = dt.strftime("%Y-%m-%d")
                        sym_prices[sym][date_str] = float(b.get("close", 0))
                    except Exception:
                        pass

        cash = float(holdings_res.cash_balance)
        bench_base = Decimal(str(last_10[0][2])) if last_10 and last_10[0][2] else Decimal("100000")

        # Calculate daily values
        for i, (dt, date_str, bench_val) in enumerate(last_10):
            port_val = cash
            for h in holdings_res.holdings:
                # get price for date, fallback to avg price if not found
                price = sym_prices.get(h.symbol, {}).get(date_str)
                if not price:
                    # find closest previous price
                    prev_prices = [
                        p for d_str, p in sym_prices.get(h.symbol, {}).items() if d_str <= date_str
                    ]
                    if prev_prices:
                        price = prev_prices[-1]
                    else:
                        price = float(h.avg_price)

                port_val += float(h.quantity) * price

            port_val_dec = Decimal(str(port_val)).quantize(Decimal("0.01"))
            bench_val_dec = Decimal(str(bench_val)).quantize(Decimal("0.01"))

            # compute returns
            d_ret = Decimal("0.0")
            b_ret = Decimal("0.0")
            if i > 0:
                prev_p = points[-1].portfolio_value
                if prev_p > 0:
                    d_ret = (port_val_dec - prev_p) / prev_p
                prev_b = points[-1].benchmark_value
                if prev_b > 0:
                    b_ret = (bench_val_dec - prev_b) / prev_b

            points.append(
                PerformancePoint(
                    date=dt,
                    portfolio_value=port_val_dec,
                    benchmark_value=bench_val_dec,
                    daily_return=d_ret.quantize(Decimal("0.0001")),
                    benchmark_return=b_ret.quantize(Decimal("0.0001")),
                )
            )

        if points:
            start_p = points[0].portfolio_value
            start_b = points[0].benchmark_value
            total_return = (
                (points[-1].portfolio_value / start_p) - Decimal("1")
                if start_p > 0
                else Decimal("0")
            )
            benchmark_return = (
                (points[-1].benchmark_value / start_b) - Decimal("1")
                if start_b > 0
                else Decimal("0")
            )
        else:
            total_return = Decimal("0")
            benchmark_return = Decimal("0")

        return PerformanceResponse(
            series=points,
            start_date=points[0].date if points else now,
            end_date=points[-1].date if points else now,
            total_return=total_return.quantize(Decimal("0.0001")),
            benchmark_return=benchmark_return.quantize(Decimal("0.0001")),
            excess_return=(total_return - benchmark_return).quantize(Decimal("0.0001")),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse.create(
                code=ErrorCode.INTERNAL_SERVER_ERROR,
                message=f"Failed to fetch performance data: {str(exc)}",
            ).dict(),
        ) from exc


@router.post(
    "/transaction",
    response_model=TransactionResponse,
    summary="Record BUY/SELL transaction",
)
async def post_transaction(
    request: TransactionRequest,
    current_user: dict | None = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TransactionResponse:
    """Execute a BUY/SELL paper transaction via the real paper-trading ledger.

    Delegates to PaperTradingService.place_order so this endpoint shares the
    same wallet/position bookkeeping and risk guardrails (daily loss circuit
    breaker, 50%-of-equity order cap, margin check) as the rest of the paper
    trading surface, instead of maintaining a second, parallel ledger.
    """
    try:
        from app.services.paper_trading import PaperTradingService

        if not current_user:
            raise HTTPException(status_code=401, detail="Unauthorized")
        user_id_str = str(current_user.id)
        tx_type = request.type.upper()

        if tx_type not in {"BUY", "SELL"}:
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse.create(
                    code=ErrorCode.VALIDATION_ERROR,
                    message="type must be BUY or SELL.",
                ).dict(),
            )

        symbol_ticker = request.symbol.upper().strip()

        try:
            order = await PaperTradingService.place_order(
                db=db,
                user_id=user_id_str,
                symbol=symbol_ticker,
                side=tx_type,
                quantity=float(request.quantity),
                order_type="MARKET",
            )
        except ValueError as ve:
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse.create(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=str(ve),
                ).dict(),
            ) from ve

        return TransactionResponse(
            transaction_id=str(order.id),
            symbol=symbol_ticker,
            type=tx_type,
            quantity=Decimal(str(order.quantity)),
            price=Decimal(str(order.price)) if order.price is not None else request.price,
            net_amount=Decimal(str(abs(order.net_amount))).quantize(Decimal("0.01")),
            timestamp=order.timestamp,
            portfolio_updated=True,
        )
    except HTTPException:
        raise
    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse.create(
                code=ErrorCode.INTERNAL_SERVER_ERROR,
                message=f"Transaction failed: {str(exc)}"[:500],
            ).dict(),
        ) from exc


@router.get(
    "/risk-metrics",
    response_model=RiskMetricsResponse,
    summary="Portfolio risk metrics",
)
async def get_risk_metrics(
    current_user: dict | None = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RiskMetricsResponse:
    """Return portfolio risk metrics based on actual historical performance."""
    try:
        if not current_user:
            raise HTTPException(status_code=401, detail="Unauthorized")

        import numpy as np

        # Calculate real performance
        perf = await get_performance(current_user=current_user, db=db)

        # If no history, return zeroes
        if not perf.series or len(perf.series) < 2:
            return RiskMetricsResponse(
                sharpe_ratio=Decimal("0.0"),
                sortino_ratio=Decimal("0.0"),
                beta=Decimal("0.0"),
                alpha=Decimal("0.0"),
                max_drawdown=Decimal("0.0"),
                var_95=Decimal("0.0"),
                cvar_95=Decimal("0.0"),
                treynor_ratio=Decimal("0.0"),
                information_ratio=Decimal("0.0"),
                calmar_ratio=Decimal("0.0"),
                portfolio_volatility=Decimal("0.0"),
                benchmark_volatility=Decimal("0.0"),
            )

        port_vals = [float(p.portfolio_value) for p in perf.series]
        bench_vals = [float(p.benchmark_value) for p in perf.series]

        # Returns
        port_rets = np.diff(port_vals) / np.array(port_vals[:-1])
        bench_rets = np.diff(bench_vals) / np.array(bench_vals[:-1])

        # Volatility
        port_vol = float(np.std(port_rets) * np.sqrt(252))
        bench_vol = float(np.std(bench_rets) * np.sqrt(252))

        # Sharpe
        mean_ret = float(np.mean(port_rets) * 252)
        sharpe = mean_ret / port_vol if port_vol > 0 else 0.0

        # Max DD
        cumulative = np.maximum.accumulate(port_vals)
        drawdowns = (cumulative - port_vals) / cumulative
        max_dd = float(np.max(drawdowns))

        # Beta
        cov = np.cov(port_rets, bench_rets)[0][1]
        var_bench = np.var(bench_rets)
        beta = float(cov / var_bench) if var_bench > 0 else 1.0

        # Alpha
        alpha = mean_ret - beta * float(np.mean(bench_rets) * 252)

        # Sortino (downside vol)
        downside = port_rets[port_rets < 0]
        down_vol = float(np.std(downside) * np.sqrt(252)) if len(downside) > 0 else 0.0
        sortino = mean_ret / down_vol if down_vol > 0 else sharpe

        # VaR & CVaR 95%
        var_95 = float(np.percentile(port_rets, 5))
        cvar_95 = (
            float(np.mean(port_rets[port_rets <= var_95]))
            if len(port_rets[port_rets <= var_95]) > 0
            else var_95
        )

        import math

        def safe_decimal(val: float) -> Decimal:
            if math.isnan(val) or math.isinf(val):
                return Decimal("0.0")
            return Decimal(str(round(val, 4)))

        return RiskMetricsResponse(
            sharpe_ratio=safe_decimal(sharpe),
            sortino_ratio=safe_decimal(sortino),
            beta=safe_decimal(beta),
            alpha=safe_decimal(alpha),
            max_drawdown=safe_decimal(max_dd),
            var_95=safe_decimal(abs(var_95)),
            cvar_95=safe_decimal(abs(cvar_95)),
            treynor_ratio=Decimal("0.0"),
            information_ratio=Decimal("0.0"),
            calmar_ratio=safe_decimal(mean_ret / max_dd if max_dd > 0 else 0.0),
            portfolio_volatility=safe_decimal(port_vol),
            benchmark_volatility=safe_decimal(bench_vol),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse.create(
                code=ErrorCode.INTERNAL_SERVER_ERROR,
                message=f"Failed to fetch risk metrics: {str(exc)}",
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
    current_user: dict = Depends(require_feature("PREMIUM")),
) -> OptimizationResponse:
    """Return normalized optimization output for requested universe and method."""
    try:
        # import random  # removed synthetic data usage
        import numpy as np
        from scipy.cluster.hierarchy import linkage
        from sqlalchemy import select

        from app.models.instrument import Instrument
        from app.models.ohlcv import OHLCV
        from app.models.signal import EnsembleSignal
        from app.schemas.portfolio import EfficientFrontierPoint, HRPDendrogramNode
        from research.portfolio.black_litterman import optimize_black_litterman
        from research.portfolio.cvar_optimization import optimize_cvar
        from research.portfolio.hrp import hrp_weights
        from research.portfolio.mean_variance import ledoit_wolf_shrinkage, optimize_mean_variance

        universe = request.universe[:50]
        if len(universe) < 2:
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse.create(
                    code=ErrorCode.VALIDATION_ERROR,
                    message="universe must contain at least 2 symbols.",
                ).dict(),
            )

        # 1. Resolve tickers to symbol IDs
        stmt = select(Instrument).where(Instrument.canonical_symbol.in_(universe))
        res = await db.execute(stmt)
        symbols = res.scalars().all()
        ticker_to_symbol_id = {s.canonical_symbol: s.id for s in symbols}
        symbol_id_to_ticker = {s.id: s.canonical_symbol for s in symbols}

        # 2. Get latest 252 available dates in OHLCV table for this universe
        dates_list = []
        if ticker_to_symbol_id:
            date_stmt = (
                select(OHLCV.timestamp)
                .where(OHLCV.instrument_id.in_(ticker_to_symbol_id.values()), OHLCV.interval == "1d")
                .distinct()
                .order_by(OHLCV.timestamp.desc())
                .limit(252)
            )
            date_res = await db.execute(date_stmt)
            dates_list = sorted([d[0] for d in date_res.all()])

        # Check if we need synthetic fallback (removed synthetic generation)
        use_synthetic = (
            False  # Synthetic data generation disabled; missing data handled via excluded_tickers
        )

        prices_dict = {}
        signals_dict = {}
        kelly_dict = {}

        if not use_synthetic and ticker_to_symbol_id:
            # Fetch OHLCV records
            ohlcv_stmt = select(OHLCV).where(
                OHLCV.instrument_id.in_(ticker_to_symbol_id.values()),
                OHLCV.interval == "1d",
                OHLCV.timestamp.in_(dates_list),
            )
            ohlcv_res = await db.execute(ohlcv_stmt)
            ohlcv_records = ohlcv_res.scalars().all()

            # Fetch Signal records
            sig_stmt = select(EnsembleSignal).where(
                EnsembleSignal.symbol_id.in_(ticker_to_symbol_id.values()),
                EnsembleSignal.time.in_(dates_list),
            )
            sig_res = await db.execute(sig_stmt)
            signal_records = sig_res.scalars().all()

            for r in ohlcv_records:
                ticker = symbol_id_to_ticker.get(r.instrument_id)
                if ticker:
                    prices_dict[(r.timestamp, ticker)] = float(r.close)

            for r in signal_records:
                ticker = symbol_id_to_ticker.get(r.symbol_id)
                if ticker:
                    signals_dict[(r.time, ticker)] = float(r.signal)
                    kelly_dict[(r.time, ticker)] = (
                        float(r.kelly_fraction) if r.kelly_fraction is not None else 0.05
                    )

        # Synthetic base price fallback removed per policy – real data required.

        # Identify tickers lacking historical price data and record them
        missing_tickers = [
            ticker for ticker in universe if all((d, ticker) not in prices_dict for d in dates_list)
        ]
        excluded_tickers = [{"ticker": t, "reason": "no_historical_data"} for t in missing_tickers]
        # Exclude missing tickers from universe
        if missing_tickers:
            universe = [t for t in universe if t not in missing_tickers]
            if not universe:
                # No valid tickers with historical data; return error.
                raise HTTPException(
                    status_code=400, detail="Insufficient historical data to optimize portfolio."
                )

        # Build aligned matrices
        T = len(dates_list)
        N = len(universe)
        prices_mat = np.zeros((T, N))
        signals_mat = np.zeros((T, N))
        kelly_mat = np.zeros((T, N))

        for i, d in enumerate(dates_list):
            for j, ticker in enumerate(universe):
                p = prices_dict.get((d, ticker))
                s = signals_dict.get((d, ticker))
                k = kelly_dict.get((d, ticker))

                if p is None:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Missing price data for ticker {ticker} on date {d}",
                    )
                if s is None:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Missing signal data for ticker {ticker} on date {d}",
                    )
                if k is None:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Missing kelly data for ticker {ticker} on date {d}",
                    )

                prices_mat[i, j] = p
                signals_mat[i, j] = s
                kelly_mat[i, j] = k

        # Compute asset returns
        returns_mat = np.zeros((T - 1, N))
        for j in range(N):
            p = prices_mat[:, j]
            p_prev = np.where(p[:-1] <= 1e-8, 1e-8, p[:-1])
            returns_mat[:, j] = (p[1:] - p[:-1]) / p_prev
        returns_mat = np.nan_to_num(returns_mat, nan=0.0, posinf=0.0, neginf=0.0)

        # Covariance estimator
        cov = ledoit_wolf_shrinkage(returns_mat)
        cov_ann = cov * 252.0
        exp_returns = np.mean(returns_mat, axis=0) * 252.0

        max_w = (
            float(request.constraints.max_weight)
            if (request.constraints and request.constraints.max_weight is not None)
            else 0.20
        )

        # Execute selected optimization method
        method = request.method.lower()
        hrp_dendrogram = None
        bl_posterior_returns = None

        if method == "hrp":
            weights_arr = hrp_weights(returns_mat)
            # Reconstruct Dendrogram
            try:

                def corr_distance(c_mat: np.ndarray) -> np.ndarray:
                    return np.sqrt((1.0 - c_mat) / 2.0)

                r = np.asarray(returns_mat, dtype=float)
                np.cov(r, rowvar=False)
                corr_hrp = np.corrcoef(r, rowvar=False)
                corr_hrp = np.nan_to_num(corr_hrp, nan=0.0)
                dist_hrp = corr_distance(corr_hrp)
                tri = dist_hrp[np.triu_indices(dist_hrp.shape[0], k=1)]
                z = linkage(tri, method="ward")

                nodes = {idx: {"symbols": [universe[idx]], "distance": 0.0} for idx in range(N)}
                for idx, row in enumerate(z):
                    left_idx = int(row[0])
                    right_idx = int(row[1])
                    dist = float(row[2])

                    left_node = nodes[left_idx]
                    right_node = nodes[right_idx]

                    merged_symbols = left_node["symbols"] + right_node["symbols"]
                    new_node = {
                        "symbols": merged_symbols,
                        "left": left_node,
                        "right": right_node,
                        "distance": dist,
                    }
                    nodes[N + idx] = new_node

                root_node = nodes[N + len(z) - 1]

                def to_dendrogram_node(d_dict) -> HRPDendrogramNode:
                    return HRPDendrogramNode(
                        symbols=d_dict["symbols"],
                        left=to_dendrogram_node(d_dict["left"]) if "left" in d_dict else None,
                        right=to_dendrogram_node(d_dict["right"]) if "right" in d_dict else None,
                        distance=Decimal(str(safe_round(d_dict["distance"], 6))),
                    )

                hrp_dendrogram = to_dendrogram_node(root_node).dict()
            except Exception:
                hrp_dendrogram = None

        elif method == "cvar":
            weights_arr = optimize_cvar(returns_mat, alpha=0.95, max_weight=max_w)

        elif method == "black_litterman":
            market_weights = np.ones(N) / N
            signals = signals_mat[-1, :]
            confidence = np.clip(kelly_mat[-1, :], 0.0, 1.0)
            weights_arr, bl_posterior = optimize_black_litterman(
                cov=cov_ann,
                market_weights=market_weights,
                signals=signals,
                confidence=confidence,
                risk_aversion=2.5,
                max_weight=max_w,
            )
            bl_posterior_returns = {
                universe[idx]: Decimal(str(safe_round(bl_posterior.posterior_returns[idx], 4)))
                for idx in range(N)
            }

        else:  # mean_variance
            weights_arr = optimize_mean_variance(
                exp_returns=exp_returns, cov=cov_ann, risk_aversion=2.5, max_weight=max_w
            )

        # Normalize weights
        weights_arr = np.clip(weights_arr, 0.0, 1.0)
        if weights_arr.sum() > 0:
            weights_arr = weights_arr / weights_arr.sum()
        else:
            weights_arr = np.ones(N) / N

        weights = [
            OptimizedWeight(
                symbol=universe[idx], weight=Decimal(str(safe_round(weights_arr[idx], 4)))
            )
            for idx in range(N)
        ]

        # Calculate final portfolio performance metrics
        port_ret = float(weights_arr.T @ exp_returns)
        port_vol = float(np.sqrt(max(weights_arr.T @ cov_ann @ weights_arr, 1e-12)))
        port_sharpe = port_ret / port_vol if port_vol > 0 else 0.0

        # Construct efficient frontier (exactly 100 points, as required by tests)
        frontier = []
        for ra in np.linspace(0.1, 10.0, 100):
            w_step = optimize_mean_variance(
                exp_returns=exp_returns, cov=cov_ann, risk_aversion=ra, max_weight=max_w
            )
            w_step = np.clip(w_step, 0.0, 1.0)
            if w_step.sum() > 0:
                w_step = w_step / w_step.sum()
            else:
                w_step = np.ones(N) / N

            ret_step = float(w_step.T @ exp_returns)
            vol_step = float(np.sqrt(max(w_step.T @ cov_ann @ w_step, 1e-12)))
            sharpe_step = ret_step / vol_step if vol_step > 0 else 0.0

            weights_dict = {
                universe[idx]: Decimal(str(safe_round(w_step[idx], 4))) for idx in range(N)
            }

            frontier.append(
                EfficientFrontierPoint(
                    expected_return=Decimal(str(safe_round(ret_step, 4))),
                    expected_volatility=Decimal(str(safe_round(vol_step, 4))),
                    sharpe_ratio=Decimal(str(safe_round(sharpe_step, 4))),
                    weights=weights_dict,
                )
            )

        return OptimizationResponse(
            method=request.method,
            weights=weights,
            expected_return=Decimal(str(safe_round(port_ret, 4))),
            expected_volatility=Decimal(str(safe_round(port_vol, 4))),
            sharpe_ratio=Decimal(str(safe_round(port_sharpe, 4))),
            efficient_frontier=frontier,
            hrp_dendrogram=hrp_dendrogram,
            bl_posterior_returns=bl_posterior_returns,
            excluded_tickers=excluded_tickers,
            timestamp=datetime.now(UTC),
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse.create(
                code=ErrorCode.INTERNAL_SERVER_ERROR,
                message=f"Optimization failed: {str(exc)}",
            ).dict(),
        ) from exc


@router.get(
    "/{portfolio_id}",
    summary="Get portfolio by ID",
)
async def get_portfolio(
    portfolio_id: int,
    current_user: dict | None = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    import uuid

    from sqlalchemy import select

    from app.models.paper_trading import PaperWallet

    uid = uuid.UUID(str(current_user.id))
    deposits_res = await db.execute(
        select(PaperWallet.balance).where(PaperWallet.user_id == uid)
    )
    # scalar_one() raises when a brand-new user has no PaperWallet row yet
    # (nothing to fall back to via `or 0.0` if it never returns) - that was
    # a 500 on every first /portfolio call for a freshly created account.
    balance = deposits_res.scalar_one_or_none()
    initial_cap = float(balance) if balance is not None else 0.0

    holdings = await get_holdings(current_user=current_user, db=db)

    return {
        "id": portfolio_id,
        "user_id": str(current_user.id),
        "name": "Main Portfolio",
        "description": "Primary trading portfolio",
        "initial_capital": initial_cap,
        "total_value": float(holdings.portfolio_value),
        "cash_balance": float(holdings.cash_balance),
        "holdings": [h.model_dump() for h in holdings.holdings],
        "created_at": holdings.timestamp.isoformat(),
        "updated_at": holdings.timestamp.isoformat(),
    }
