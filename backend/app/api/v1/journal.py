"""Trade journal API endpoints for creating, listing, and deleting trade review notes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.journal import TradeJournal
from app.schemas.errors import ErrorCode, ErrorResponse
from app.schemas.journal import JournalCreate, JournalResponse

router = APIRouter(prefix="/journal", tags=["journal"])


async def get_db_user_id(current_user, db: AsyncSession) -> uuid.UUID:
    if getattr(current_user, "id", None):
        return current_user.id
    if isinstance(current_user, dict) and current_user.get("sub"):
        return uuid.UUID(current_user["sub"]) if isinstance(current_user["sub"], str) else current_user["sub"]
    raise HTTPException(status_code=401, detail="Unauthorized")


@router.get("", response_model=list[JournalResponse])
async def get_journals(
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(get_current_user),
) -> list[JournalResponse]:
    """Retrieve all trade journal entries for the current user."""
    user_uuid = await get_db_user_id(current_user, db)
    result = await db.execute(
        select(TradeJournal)
        .where(TradeJournal.user_id == user_uuid)
        .order_by(TradeJournal.created_at.desc())
    )
    entries = result.scalars().all()
    return entries


@router.post("", response_model=JournalResponse, status_code=status.HTTP_201_CREATED)
async def create_journal(
    payload: JournalCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(get_current_user),
) -> JournalResponse:
    """Create a new trade journal entry."""
    user_uuid = await get_db_user_id(current_user, db)
    entry = TradeJournal(
        user_id=user_uuid,
        symbol=payload.symbol.upper(),
        notes=payload.notes,
        tags=payload.tags,
        rating=payload.rating,
        entry_price=payload.entry_price,
        exit_price=payload.exit_price,
        quantity=payload.quantity,
        direction=payload.direction,
    )
    db.add(entry)
    await db.flush()
    # The session will commit automatically upon exiting the dependency context
    return entry


@router.delete("/{journal_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_journal(
    journal_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(get_current_user),
) -> Response:
    """Delete a trade journal entry by ID."""
    user_uuid = await get_db_user_id(current_user, db)
    result = await db.execute(
        select(TradeJournal).where(TradeJournal.id == journal_id, TradeJournal.user_id == user_uuid)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse.create(
                code=ErrorCode.RESOURCE_NOT_FOUND,
                message="Trade journal entry not found.",
            ).dict(),
        )
    await db.delete(entry)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
