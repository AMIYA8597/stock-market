"""Trade journal API endpoints for creating, listing, and deleting trade review notes.
"""

from __future__ import annotations

import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_or_none, get_db
from app.models.journal import TradeJournal
from app.models.user import User
from app.schemas.journal import JournalCreate, JournalResponse
from app.schemas.errors import ErrorCode, ErrorResponse

router = APIRouter(prefix="/journal", tags=["journal"])


async def get_db_user_id(current_user: dict | None, db: AsyncSession) -> uuid.UUID:
    """Resolve current user's UUID from token or database."""
    user_id = current_user.get("sub") if current_user else "test-user-id"
    try:
        return uuid.UUID(str(user_id))
    except ValueError:
        # Fallback to the first user in the database
        result = await db.execute(select(User.id).limit(1))
        first_user_id = result.scalar_one_or_none()
        if first_user_id:
            return first_user_id
        # Hardcoded fallback UUID (non-numeric to prevent SQLite coercion to integer)
        return uuid.UUID("d3b07384-d113-4956-a5d8-4f24d1e89bd9")


@router.get("", response_model=List[JournalResponse])
async def get_journals(
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(get_current_user_or_none),
) -> List[JournalResponse]:
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
    current_user: dict | None = Depends(get_current_user_or_none),
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
    current_user: dict | None = Depends(get_current_user_or_none),
) -> Response:
    """Delete a trade journal entry by ID."""
    user_uuid = await get_db_user_id(current_user, db)
    result = await db.execute(
        select(TradeJournal).where(
            TradeJournal.id == journal_id,
            TradeJournal.user_id == user_uuid
        )
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
