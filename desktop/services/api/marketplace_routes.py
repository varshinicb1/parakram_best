"""
Stripe Webhook, Wiring, and Marketplace API Routes.
"""

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


# ── Stripe Webhooks ────────────────────────────────────────

@router.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events."""
    from services.stripe_webhook import get_webhook_handler
    handler = get_webhook_handler()

    payload = await request.body()
    sig = request.headers.get("Stripe-Signature", "")

    if not handler.verify_signature(payload, sig):
        raise HTTPException(400, "Invalid signature")

    import json
    event = json.loads(payload)
    event_type = event.get("type", "")
    data = event.get("data", {})

    result = await handler.handle_event(event_type, data)
    return {"received": True, "result": result}


# ── Wiring Diagram ─────────────────────────────────────────

class WiringRequest(BaseModel):
    components: list[str]
    board: str = "esp32dev"


@router.post("/wiring/generate")
async def generate_wiring(req: WiringRequest):
    """Generate wiring diagram for components."""
    from services.wiring_generator import get_wiring_generator
    gen = get_wiring_generator()
    return gen.generate(req.components, req.board)


# ── Community Marketplace ──────────────────────────────────

class MarketplaceSearchRequest(BaseModel):
    category: str = ""
    tag: str = ""
    featured_only: bool = False


class ExtensionSubmitRequest(BaseModel):
    id: str
    name: str
    description: str
    author: str
    version: str
    category: str
    tags: list[str] = []
    boards: list[str] = []


@router.get("/marketplace")
async def browse_marketplace():
    """Browse all marketplace extensions."""
    from services.marketplace import get_marketplace_extensions
    return {"extensions": get_marketplace_extensions(), "count": len(get_marketplace_extensions())}


@router.post("/marketplace/search")
async def search_marketplace(req: MarketplaceSearchRequest):
    """Search marketplace with filters."""
    from services.marketplace import get_marketplace_extensions
    results = get_marketplace_extensions(req.category, req.tag, req.featured_only)
    return {"extensions": results, "count": len(results)}


@router.get("/marketplace/categories")
async def get_categories():
    """Get extension categories."""
    from services.marketplace import get_categories
    return {"categories": get_categories()}


@router.post("/marketplace/submit")
async def submit_extension(req: ExtensionSubmitRequest):
    """Submit a new extension."""
    from services.marketplace import submit_extension
    return submit_extension(req.model_dump())
