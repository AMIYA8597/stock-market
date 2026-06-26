"""Stock screener endpoints router (POST/GET /screener/*)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.schemas.errors import ErrorCode, ErrorResponse
from app.schemas.screener import (
    ScreenerPreset,
    ScreenerPresetsResponse,
    ScreenerResult,
    ScreenerRunRequest,
    ScreenerRunResponse,
)
from app.services.market_data_service import MarketDataService

router = APIRouter(prefix="/screener", tags=["screener"])


@router.post("/run", response_model=ScreenerRunResponse)
async def post_screener_run(request: ScreenerRunRequest, db: AsyncSession = Depends(get_db)) -> ScreenerRunResponse:
    try:
        import numpy as np
        from sqlalchemy import select
        from app.models.asset import Symbol
        from app.models.ohlcv import OHLCV
        from app.models.signal import EnsembleSignal


        # Helper to round float values safely, handling NaNs and Inf
        def safe_round(val: float, places: int) -> float:
            import math
            if val is None or math.isnan(val) or math.isinf(val):
                return 0.0
            return round(float(val), places)

        # 1. Fetch active symbols matching request exchange list
        stmt = select(Symbol).where(Symbol.is_active == True)
        if request.exchange:
            stmt = stmt.where(Symbol.exchange.in_([ex.upper() for ex in request.exchange]))
        res = await db.execute(stmt)
        symbols = res.scalars().all()

        results = []
        for s in symbols:
            # Query latest 30 daily OHLCV bars for this symbol
            ohlcv_stmt = (
                select(OHLCV)
                .where(OHLCV.symbol_id == s.id, OHLCV.interval == "1d")
                .order_by(OHLCV.time.desc())
                .limit(30)
            )
            ohlcv_res = await db.execute(ohlcv_stmt)
            records = list(ohlcv_res.scalars().all())
            records.reverse()

            if len(records) < 2:
                # Insufficient data — skip this symbol, never generate fake prices
                continue
            else:
                closes = [float(r.close) for r in records]
                volumes = [float(r.volume) for r in records]


            latest_price = closes[-1]
            prev_price = closes[-2] if len(closes) > 1 else latest_price
            change_pct = ((latest_price - prev_price) / prev_price * 100.0) if prev_price > 0 else 0.0

            # Compute RSI-14
            deltas = np.diff(closes)
            if len(deltas) >= 14:
                gains = np.where(deltas > 0, deltas, 0.0)
                losses = np.where(deltas < 0, -deltas, 0.0)
                avg_gain = np.mean(gains[-14:])
                avg_loss = np.mean(losses[-14:])
                if avg_loss == 0:
                    rsi_val = 100.0
                else:
                    rs = avg_gain / avg_loss
                    rsi_val = 100.0 - (100.0 / (1.0 + rs))
            else:
                rsi_val = 50.0

            # Compute momentum_21d
            momentum_21d = (closes[-1] / closes[-22] - 1.0) if len(closes) >= 22 else 0.0

            # Compute volume_ratio
            volume_ratio = volumes[-1] / np.mean(volumes[-21:]) if (len(volumes) >= 21 and np.mean(volumes[-21:]) > 0) else 1.0

            # Query latest EnsembleSignal
            sig_stmt = (
                select(EnsembleSignal)
                .where(EnsembleSignal.symbol_id == s.id)
                .order_by(EnsembleSignal.time.desc())
                .limit(1)
            )
            sig_res = await db.execute(sig_stmt)
            latest_sig = sig_res.scalar_one_or_none()

            if latest_sig:
                sig_dir = latest_sig.direction
                sig_conf = float(latest_sig.confidence)
                regime_map = {0: "bull", 1: "bear", 2: "sideways", 3: "crisis"}
                regime_state = regime_map.get(latest_sig.regime_state, "sideways")
            else:
                sig_dir = "NEUTRAL"
                sig_conf = 0.5
                regime_state = "sideways"

            # Fetch PE ratio and market cap from MarketDataService (no random fallback)
            pe_ratio = None
            mcap = None
            try:
                sym_ns = s.ticker if "." in s.ticker else f"{s.ticker}.NS"
                info = await MarketDataService.get_ticker_info(sym_ns)
                pe_raw = info.get("trailingPE") or info.get("forwardPE")
                mc_raw = info.get("marketCap")
                if pe_raw is not None:
                    pe_ratio = float(pe_raw)
                if mc_raw is not None:
                    mcap = float(mc_raw) / 1e7  # convert to crores for display
            except Exception:
                pass  # Leave pe_ratio and mcap as None — never fabricate values

            results.append({
                "ticker": s.ticker,
                "name": s.name,
                "exchange": s.exchange,
                "asset_type": s.asset_type,
                "price": latest_price,
                "change_pct": change_pct,
                "pe_ratio": pe_ratio,
                "rsi": rsi_val,
                "signal_direction": sig_dir,
                "signal_confidence": sig_conf,
                "regime_state": regime_state,
                "momentum_21d": momentum_21d,
                "volume_ratio": volume_ratio,
                "market_cap": mcap,
            })

        # Apply Filters
        filtered = []
        filters = request.filters
        for item in results:
            if filters.asset_class and item["asset_type"] != filters.asset_class.upper():
                continue
                
            mcap_base = item["market_cap"] * 1000000.0
            if filters.market_cap_min is not None and mcap_base < float(filters.market_cap_min):
                continue
            if filters.market_cap_max is not None and mcap_base > float(filters.market_cap_max):
                continue
                
            if filters.pe_ratio_max is not None:
                if item["pe_ratio"] is None or item["pe_ratio"] > float(filters.pe_ratio_max):
                    continue
                    
            if filters.rsi_min is not None and item["rsi"] < float(filters.rsi_min):
                continue
            if filters.rsi_max is not None and item["rsi"] > float(filters.rsi_max):
                continue
                
            if filters.momentum_21d_min is not None and item["momentum_21d"] < float(filters.momentum_21d_min):
                continue
                
            if filters.volume_ratio_min is not None and item["volume_ratio"] < float(filters.volume_ratio_min):
                continue
                
            if filters.signal_direction:
                if item["signal_direction"] not in [sd.upper() for sd in filters.signal_direction]:
                    continue
                    
            if filters.regime_compatible:
                is_bull_regime = item["regime_state"] == "bull"
                is_bear_regime = item["regime_state"] in {"bear", "crisis"}
                is_buy_signal = item["signal_direction"] in {"BUY", "STRONG_BUY"}
                is_sell_signal = item["signal_direction"] in {"SELL", "STRONG_SELL"}
                
                compatible = False
                if is_buy_signal and is_bull_regime:
                    compatible = True
                elif is_sell_signal and is_bear_regime:
                    compatible = True
                elif item["signal_direction"] == "NEUTRAL":
                    compatible = True
                    
                if not compatible:
                    continue

            filtered.append(item)

        # Sorting
        sort_by = request.sort_by.lower()
        def get_sort_key(item_dict):
            if sort_by == "rsi":
                return item_dict["rsi"]
            elif sort_by == "momentum_21d":
                return item_dict["momentum_21d"]
            elif sort_by == "volume_ratio":
                return item_dict["volume_ratio"]
            elif sort_by == "pe_ratio":
                return item_dict["pe_ratio"] if item_dict["pe_ratio"] is not None else 999.0
            else:
                return item_dict["signal_confidence"]

        reverse = True
        if sort_by == "pe_ratio":
            reverse = False
            
        filtered.sort(key=get_sort_key, reverse=reverse)

        final_results = []
        for item in filtered[:request.limit]:
            final_results.append(
                ScreenerResult(
                    ticker=item["ticker"],
                    name=item["name"],
                    exchange=item["exchange"],
                    asset_type=item["asset_type"],
                    price=Decimal(str(safe_round(item["price"], 8))),
                    change_pct=Decimal(str(safe_round(item["change_pct"], 4))),
                    pe_ratio=Decimal(str(safe_round(item["pe_ratio"], 4))) if item["pe_ratio"] is not None else None,
                    rsi=Decimal(str(safe_round(item["rsi"], 4))) if item["rsi"] is not None else None,
                    signal_direction=item["signal_direction"],
                    signal_confidence=Decimal(str(safe_round(item["signal_confidence"], 4))),
                    regime_state=item["regime_state"],
                    momentum_21d=Decimal(str(safe_round(item["momentum_21d"], 4))),
                    volume_ratio=Decimal(str(safe_round(item["volume_ratio"], 4))),
                )
            )

        return ScreenerRunResponse(
            results=final_results,
            total_matched=len(filtered),
            filters_applied=request.model_dump(),
            generated_at=datetime.now(UTC),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse.create(
                code=ErrorCode.INTERNAL_SERVER_ERROR,
                message=f"Screener run failed: {str(exc)}",
            ).dict(),
        ) from exc


@router.get("/presets", response_model=ScreenerPresetsResponse)
async def get_screener_presets() -> ScreenerPresetsResponse:
    now = datetime.now(UTC)
    presets = [
        ScreenerPreset(name="value_stocks", description="Low PE and stable trend", filters_json={"pe_ratio_max": 20, "rsi_min": 35}, created_at=now),
        ScreenerPreset(name="momentum", description="Strong 21d momentum with volume support", filters_json={"momentum_21d_min": 0.05, "volume_ratio_min": 1.3}, created_at=now),
        ScreenerPreset(name="regime_aligned_buys", description="BUY signals aligned with bull regime", filters_json={"signal_direction": ["BUY", "STRONG_BUY"], "regime_compatible": True}, created_at=now),
    ]
    return ScreenerPresetsResponse(presets=presets)
