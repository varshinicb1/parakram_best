"""
Admin Routes — User management, subscription controls, and analytics.
Protected: Admin role only.
"""

import os
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from api.auth_routes import get_current_user

router = APIRouter()

USERS_DIR = Path(os.environ.get("PARAKRAM_USERS_DIR", "./storage/users"))


def _require_admin(user: dict):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")


@router.get("/users")
async def list_users(user: dict = Depends(get_current_user)):
    """List all registered users (admin only)."""
    _require_admin(user)

    users = []
    if USERS_DIR.exists():
        for f in USERS_DIR.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                users.append({
                    "id": data.get("id"),
                    "email": data.get("email"),
                    "display_name": data.get("display_name", ""),
                    "role": data.get("role", "maker"),
                    "subscription": data.get("subscription", "free"),
                    "created_at": data.get("created_at", 0),
                    "builds_today": data.get("builds_today", 0),
                })
            except Exception:
                continue

    return {"users": users, "total": len(users)}


class UpdateRoleRequest(BaseModel):
    role: str  # "maker", "pro", "admin"


@router.patch("/users/{user_id}/role")
async def update_user_role(user_id: str, req: UpdateRoleRequest,
                           user: dict = Depends(get_current_user)):
    """Change a user's role (admin only)."""
    _require_admin(user)

    valid_roles = ["maker", "pro", "admin"]
    if req.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Role must be one of: {valid_roles}")

    # Find user by ID
    if USERS_DIR.exists():
        for f in USERS_DIR.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                if data.get("id") == user_id:
                    data["role"] = req.role
                    f.write_text(json.dumps(data, indent=2))
                    return {"status": "updated", "user_id": user_id, "role": req.role}
            except Exception:
                continue

    raise HTTPException(status_code=404, detail="User not found")


class UpdateSubscriptionRequest(BaseModel):
    subscription: str  # "free", "pro", "enterprise"


@router.patch("/users/{user_id}/subscription")
async def update_subscription(user_id: str, req: UpdateSubscriptionRequest,
                               user: dict = Depends(get_current_user)):
    """Override a user's subscription tier (admin only)."""
    _require_admin(user)

    valid_subs = ["free", "pro", "enterprise"]
    if req.subscription not in valid_subs:
        raise HTTPException(status_code=400, detail=f"Subscription must be one of: {valid_subs}")

    if USERS_DIR.exists():
        for f in USERS_DIR.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                if data.get("id") == user_id:
                    data["subscription"] = req.subscription
                    f.write_text(json.dumps(data, indent=2))
                    return {"status": "updated", "user_id": user_id, "subscription": req.subscription}
            except Exception:
                continue

    raise HTTPException(status_code=404, detail="User not found")


@router.get("/analytics")
async def get_analytics(user: dict = Depends(get_current_user)):
    """Get platform usage analytics (admin only)."""
    _require_admin(user)

    total_users = 0
    roles = {"maker": 0, "pro": 0, "admin": 0}
    subs = {"free": 0, "pro": 0, "enterprise": 0}
    total_builds = 0

    if USERS_DIR.exists():
        for f in USERS_DIR.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                total_users += 1
                role = data.get("role", "maker")
                sub = data.get("subscription", "free")
                roles[role] = roles.get(role, 0) + 1
                subs[sub] = subs.get(sub, 0) + 1
                total_builds += data.get("builds_today", 0)
            except Exception:
                continue

    return {
        "total_users": total_users,
        "roles": roles,
        "subscriptions": subs,
        "total_builds_today": total_builds,
    }
