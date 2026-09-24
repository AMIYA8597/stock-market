from fastapi import APIRouter, Depends, HTTPException
import logging

from app.core.security import get_current_context, RequestContext

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])

def _require_superadmin(ctx: RequestContext) -> None:
    # In a real app, this would check if the user is a platform SUPERADMIN
    # or the token has a specific claim.
    if ctx.organization_role != "SUPERADMIN":
        raise HTTPException(status_code=403, detail="Superadmin access is required.")

@router.get("/users")
async def list_users(ctx: RequestContext = Depends(get_current_context)):
    _require_superadmin(ctx)
    return {"users": []}

@router.patch("/users/{user_id}/role")
async def update_user_role(user_id: str, ctx: RequestContext = Depends(get_current_context)):
    _require_superadmin(ctx)
    return {"status": "ok"}

@router.get("/content")
async def content_control(ctx: RequestContext = Depends(get_current_context)):
    _require_superadmin(ctx)
    return {"posts": []}

@router.post("/ingest")
async def trigger_ingestion(ctx: RequestContext = Depends(get_current_context)):
    _require_superadmin(ctx)
    from app.jobs.ingestion import IngestionPipeline
    import asyncio
    pipeline = IngestionPipeline()
    asyncio.create_task(pipeline.run_full_ingestion())
    return {"message": "Ingestion triggered"}
