"""
Signup & Download API Routes — User registration and download tracking.
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class SignupRequest(BaseModel):
    name: str
    email: str
    phone: str = ""
    organization: str = ""
    use_case: str = ""


@router.post("/signup")
async def signup(req: SignupRequest, request: Request):
    """Register a new user and get download access."""
    from services.user_database import get_user_db
    db = get_user_db()

    ip = request.client.host if request.client else ""
    referrer = request.headers.get("referer", "")

    result = db.signup(
        name=req.name,
        email=req.email,
        phone=req.phone,
        organization=req.organization,
        use_case=req.use_case,
        ip_address=ip,
        referrer=referrer,
    )
    return result


@router.post("/download/{user_id}")
async def log_download(user_id: int, version: str = "2.0.0", platform: str = "desktop"):
    """Log a download event."""
    from services.user_database import get_user_db
    db = get_user_db()
    db.log_download(user_id, version, platform)
    return {"status": "logged"}


@router.get("/user/{email}")
async def get_user(email: str):
    """Get user by email."""
    from services.user_database import get_user_db
    db = get_user_db()
    user = db.get_user(email)
    if not user:
        from fastapi import HTTPException
        raise HTTPException(404, "User not found")
    return user


@router.get("/admin/users")
async def admin_users(limit: int = 100, offset: int = 0):
    """Admin: list all users."""
    from services.user_database import get_user_db
    db = get_user_db()
    return db.get_all_users(limit, offset)


@router.get("/admin/stats")
async def admin_stats():
    """Admin: signup statistics."""
    from services.user_database import get_user_db
    db = get_user_db()
    return db.get_stats()
