"""
Subscription API Routes — Plan management, limits, and Stripe-ready payment hooks.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class UpgradeRequest(BaseModel):
    user_id: str
    plan: str
    stripe_customer_id: str = ""
    stripe_subscription_id: str = ""


class LimitCheckRequest(BaseModel):
    user_id: str
    resource: str
    current_count: int = 0


@router.get("/plans")
async def list_plans():
    """List all available plans with features and pricing."""
    from services.subscription_manager import get_subscription_manager
    mgr = get_subscription_manager()
    return {"plans": mgr.get_all_plans()}


@router.get("/subscription/{user_id}")
async def get_subscription(user_id: str):
    """Get a user's current subscription."""
    from services.subscription_manager import get_subscription_manager
    mgr = get_subscription_manager()
    return mgr.get_subscription(user_id)


@router.get("/limits/{user_id}")
async def get_limits(user_id: str):
    """Get plan limits for a user."""
    from services.subscription_manager import get_subscription_manager
    mgr = get_subscription_manager()
    return mgr.get_limits(user_id)


@router.post("/check-limit")
async def check_limit(req: LimitCheckRequest):
    """Check if user can perform an action based on plan limits."""
    from services.subscription_manager import get_subscription_manager
    mgr = get_subscription_manager()
    return mgr.check_limit(req.user_id, req.resource, req.current_count)


@router.post("/upgrade")
async def upgrade_plan(req: UpgradeRequest):
    """Upgrade a user's plan (Stripe webhook receiver)."""
    from services.subscription_manager import get_subscription_manager
    mgr = get_subscription_manager()
    return mgr.upgrade(req.user_id, req.plan, req.stripe_customer_id, req.stripe_subscription_id)
