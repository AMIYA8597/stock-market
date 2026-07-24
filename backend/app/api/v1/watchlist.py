"""FastAPI Router for User Watchlist."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_or_none, get_db
from app.models.watchlist import UserWatchlist

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


class WatchlistAddRequest(BaseModel):
    symbol: str


class WatchlistResponse(BaseModel):
    symbols: list[str]


@router.get("", response_model=WatchlistResponse, summary="Get user watchlist")
async def get_watchlist(
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(get_current_user_or_none),
) -> Any:
    """Retrieve the current user's watchlist."""
    user_id = str(current_user.id) if current_user else "test-user-id"

    result = await db.execute(
        select(UserWatchlist.symbol)
        .where(UserWatchlist.user_id == user_id)
        .order_by(UserWatchlist.added_at.desc())
    )
    symbols = result.scalars().all()

    return WatchlistResponse(symbols=list(symbols))


@router.post("", response_model=WatchlistResponse, summary="Add symbol to watchlist")
async def add_to_watchlist(
    request: WatchlistAddRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(get_current_user_or_none),
) -> Any:
    """Add a symbol to the current user's watchlist."""
    user_id = str(current_user.id) if current_user else "test-user-id"
    symbol = request.symbol.upper()

    # Validate symbol format somewhat
    if not symbol:
        raise HTTPException(status_code=400, detail="Invalid symbol")

    # Check if exists
    result = await db.execute(
        select(UserWatchlist)
        .where(UserWatchlist.user_id == user_id, UserWatchlist.symbol == symbol)
    )
    existing = result.scalar_one_or_none()

    if not existing:
        new_item = UserWatchlist(user_id=user_id, symbol=symbol)
        db.add(new_item)
        await db.commit()

    # Fetch updated list
    result = await db.execute(
        select(UserWatchlist.symbol)
        .where(UserWatchlist.user_id == user_id)
        .order_by(UserWatchlist.added_at.desc())
    )
    symbols = result.scalars().all()
    return WatchlistResponse(symbols=list(symbols))


@router.delete("/{symbol}", response_model=WatchlistResponse, summary="Remove symbol from watchlist")
async def remove_from_watchlist(
    symbol: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(get_current_user_or_none),
) -> Any:
    """Remove a symbol from the current user's watchlist."""
    user_id = str(current_user.id) if current_user else "test-user-id"
    target_symbol = symbol.upper()

    await db.execute(
        delete(UserWatchlist)
        .where(UserWatchlist.user_id == user_id, UserWatchlist.symbol == target_symbol)
    )
    await db.commit()

    # Fetch updated list
    result = await db.execute(
        select(UserWatchlist.symbol)
        .where(UserWatchlist.user_id == user_id)
        .order_by(UserWatchlist.added_at.desc())
    )
    symbols = result.scalars().all()
    return WatchlistResponse(symbols=list(symbols))
