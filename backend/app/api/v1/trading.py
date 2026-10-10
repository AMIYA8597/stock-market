"""Trading mode and audit log endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.dependencies import get_current_user

router = APIRouter(prefix="/trading", tags=["trading"])


class ModeResponse(BaseModel):
    mode: str
    is_live: bool


@router.get("/mode")
async def get_mode(
    current_user: dict = Depends(get_current_user),
) -> ModeResponse:
    return ModeResponse(mode="PAPER", is_live=False)


@router.get("/audit-log")
async def get_audit_log(
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
):
    return {"entries": [], "total": 0}
