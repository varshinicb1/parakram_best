"""
Auth Routes — JWT-based authentication for Parakram.
Sign up, log in, and password reset.
"""

import os
import json
import hashlib
import secrets
import time
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, EmailStr
from typing import Optional
import hmac
import base64

router = APIRouter()

# Simple file-based user store (replace with DB in production)
USERS_DIR = Path(os.environ.get("PARAKRAM_USERS_DIR", "./storage/users"))
USERS_DIR.mkdir(parents=True, exist_ok=True)

JWT_SECRET = os.environ.get("JWT_SECRET", "parakram-v2-secret-key-change-in-prod")
JWT_EXPIRY = 86400 * 7  # 7 days


# ─── Helpers ──────────────────────────────────────────────────

def _hash_password(password: str, salt: str = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
    return hashed.hex(), salt


def _create_jwt(user_id: str, email: str, role: str = "maker") -> str:
    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).decode().rstrip("=")
    payload_data = {
        "sub": user_id,
        "email": email,
        "role": role,
        "iat": int(time.time()),
        "exp": int(time.time()) + JWT_EXPIRY,
    }
    payload = base64.urlsafe_b64encode(json.dumps(payload_data).encode()).decode().rstrip("=")
    signature = hmac.new(JWT_SECRET.encode(), f"{header}.{payload}".encode(), hashlib.sha256).hexdigest()
    return f"{header}.{payload}.{signature}"


def _verify_jwt(token: str) -> Optional[dict]:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        # Verify signature
        expected_sig = hmac.new(JWT_SECRET.encode(), f"{parts[0]}.{parts[1]}".encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_sig, parts[2]):
            return None

        # Decode payload (add padding)
        payload_str = parts[1] + "=" * (4 - len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_str))

        # Check expiry
        if payload.get("exp", 0) < time.time():
            return None

        return payload
    except Exception:
        return None


def _get_user_file(email: str) -> Path:
    safe_email = email.replace("@", "_at_").replace(".", "_dot_")
    return USERS_DIR / f"{safe_email}.json"


def _load_user(email: str) -> Optional[dict]:
    user_file = _get_user_file(email)
    if user_file.exists():
        return json.loads(user_file.read_text())
    return None


def _save_user(user_data: dict):
    user_file = _get_user_file(user_data["email"])
    user_file.write_text(json.dumps(user_data, indent=2))


# ─── Auth Dependency ──────────────────────────────────────────

async def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization.split(" ", 1)[1]
    payload = _verify_jwt(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return payload


# ─── Routes ───────────────────────────────────────────────────

class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: str = ""


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/signup")
async def signup(req: SignupRequest):
    """Create a new user account."""
    if _load_user(req.email):
        raise HTTPException(status_code=409, detail="Email already registered")

    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    hashed, salt = _hash_password(req.password)
    user_id = secrets.token_hex(12)

    user_data = {
        "id": user_id,
        "email": req.email,
        "display_name": req.display_name or req.email.split("@")[0],
        "password_hash": hashed,
        "salt": salt,
        "role": "maker",
        "subscription": "free",
        "created_at": int(time.time()),
        "builds_today": 0,
        "last_build_date": "",
    }
    _save_user(user_data)

    token = _create_jwt(user_id, req.email, "maker")
    return {
        "status": "created",
        "token": token,
        "user": {"id": user_id, "email": req.email, "role": "maker"},
    }


@router.post("/login")
async def login(req: LoginRequest):
    """Authenticate and return a JWT token."""
    user = _load_user(req.email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    hashed, _ = _hash_password(req.password, user["salt"])
    if not hmac.compare_digest(hashed, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = _create_jwt(user["id"], req.email, user.get("role", "maker"))
    return {
        "status": "authenticated",
        "token": token,
        "user": {
            "id": user["id"],
            "email": req.email,
            "role": user.get("role", "maker"),
            "subscription": user.get("subscription", "free"),
            "display_name": user.get("display_name", ""),
        },
    }


@router.get("/me")
async def get_profile(user: dict = Depends(get_current_user)):
    """Get current user profile."""
    full_user = _load_user(user["email"])
    if not full_user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id": full_user["id"],
        "email": full_user["email"],
        "display_name": full_user.get("display_name", ""),
        "role": full_user.get("role", "maker"),
        "subscription": full_user.get("subscription", "free"),
        "created_at": full_user.get("created_at", 0),
    }
