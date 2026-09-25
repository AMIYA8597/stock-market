import logging
from collections.abc import Callable

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_context, RequestContext
from app.database.connection import get_db
from app.models.billing import OrganizationSubscription, Plan, PlanEntitlement

logger = logging.getLogger(__name__)


def require_feature(feature_key: str) -> Callable:
    """Dependency that ensures the current organization's plan includes `feature_key`."""
    async def _dependency(
        ctx: RequestContext = Depends(get_current_context),
        db: AsyncSession = Depends(get_db),
    ) -> RequestContext:
        if not ctx.organization_id:
            raise HTTPException(status_code=403, detail="Organization context required")

        result = await db.execute(
            select(PlanEntitlement)
            .join(Plan, PlanEntitlement.plan_id == Plan.id)
            .join(OrganizationSubscription, OrganizationSubscription.plan_id == Plan.id)
            .where(
                OrganizationSubscription.organization_id == ctx.organization_id,
                OrganizationSubscription.status == "active",
                PlanEntitlement.feature_key == feature_key,
                PlanEntitlement.is_enabled == True
            )
        )
        entitlement = result.scalars().first()
        if not entitlement:
            raise HTTPException(
                status_code=403, 
                detail=f"Feature '{feature_key}' requires a premium plan or is not enabled for your organization."
            )
        return ctx
    return _dependency


from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert
from datetime import datetime, timezone
from app.models.identity import UsageCounter
import uuid

def require_quota(feature_key: str, increment: int = 1) -> Callable:
    """Dependency that atomically checks and increments quota for `feature_key`."""
    async def _dependency(
        ctx: RequestContext = Depends(get_current_context),
        db: AsyncSession = Depends(get_db),
    ) -> RequestContext:
        if not ctx.organization_id:
            raise HTTPException(status_code=403, detail="Organization context required")

        org_uuid = uuid.UUID(ctx.organization_id)
        
        result = await db.execute(
            select(PlanEntitlement)
            .join(Plan, PlanEntitlement.plan_id == Plan.id)
            .join(OrganizationSubscription, OrganizationSubscription.plan_id == Plan.id)
            .where(
                OrganizationSubscription.organization_id == org_uuid,
                OrganizationSubscription.status == "active",
                PlanEntitlement.feature_key == feature_key
            )
        )
        entitlement = result.scalars().first()
        if not entitlement:
            raise HTTPException(status_code=403, detail=f"Feature '{feature_key}' is not available.")
        
        limit = entitlement.quota_limit
        if limit is None:
            return ctx  # Unlimited

        now = datetime.now(timezone.utc)
        # Using a simplistic monthly reset period based on current month for illustration
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Upsert the usage counter to ensure it exists for this period
        stmt = insert(UsageCounter).values(
            organization_id=org_uuid,
            metric=feature_key,
            period_start=period_start,
            period_end=period_start, # Ignoring period_end complexity for now
            current_count=0,
            limit_count=limit
        ).on_conflict_do_nothing(
            index_elements=['organization_id', 'metric', 'period_start'] # Assuming index exists, actually UsageCounter doesn't have unique constraint for this out of box, wait.
        )
        # Instead of ON CONFLICT, let's just do an atomic UPDATE with WHERE
        
        # We can just do an update. If rowcount is 0, we insert and then update.
        update_stmt = (
            update(UsageCounter)
            .where(
                UsageCounter.organization_id == org_uuid,
                UsageCounter.metric == feature_key,
                UsageCounter.period_start == period_start,
                UsageCounter.current_count + increment <= limit
            )
            .values(current_count=UsageCounter.current_count + increment)
            .returning(UsageCounter.current_count)
        )
        updated = await db.execute(update_stmt)
        if updated.first():
            return ctx
            
        # If not updated, either row doesn't exist or limit exceeded
        # Check if row exists
        row_exists = await db.scalar(
            select(UsageCounter.id).where(
                UsageCounter.organization_id == org_uuid,
                UsageCounter.metric == feature_key,
                UsageCounter.period_start == period_start
            )
        )
        
        if row_exists:
            raise HTTPException(status_code=403, detail=f"Quota exceeded for '{feature_key}'.")
            
        # If it doesn't exist, we insert it with current_count = increment if increment <= limit
        if increment > limit:
            raise HTTPException(status_code=403, detail=f"Quota exceeded for '{feature_key}'.")
            
        new_counter = UsageCounter(
            organization_id=org_uuid,
            metric=feature_key,
            period_start=period_start,
            period_end=period_start,
            current_count=increment,
            limit_count=limit
        )
        db.add(new_counter)
        try:
            await db.flush()
        except Exception:
            # Another transaction might have inserted it, fallback to check
            raise HTTPException(status_code=403, detail=f"Quota check failed, please try again.")

        return ctx
    return _dependency
