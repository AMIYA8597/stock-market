from collections.abc import Callable

from app.models.subscription import Subscription
from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_or_none, get_db
from app.models.payment import Plan
from app.models.user import User


def require_active_subscription(tier: str = "Pro") -> Callable:
    """Dependency that ensures the current user has an active subscription to `tier` or higher."""

    async def _dependency(
        current_user: "User" | None = Depends(get_current_user_or_none),
        db: AsyncSession = Depends(get_db),
    ) -> Subscription:
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required.")

        user_id_str = str(current_user.id)
        import uuid

        try:
            user_id = uuid.UUID(user_id_str)
        except ValueError:
            user_id = user_id_str

        # In a real app we might assign numerical tiers to plans, but here we can just check if they have active sub
        result = await db.execute(
            select(Subscription, Plan)
            .join(Plan, Subscription.plan_id == Plan.id)
            .where(Subscription.user_id == user_id, Subscription.status == "active")
        )
        row = result.first()
        if not row:
            raise HTTPException(status_code=403, detail="Active premium subscription required.")

        sub, plan = row
        # Very simple tier logic for this example
        tiers = {"Free": 0, "Pro": 1, "Institutional": 2}
        user_tier = tiers.get(plan.name, 0)
        req_tier = tiers.get(tier, 1)

        if user_tier < req_tier:
            raise HTTPException(status_code=403, detail=f"Requires {tier} plan or higher.")

        return sub

    return _dependency
