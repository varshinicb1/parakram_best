"""
LLM Routes — Provider management, model selection, API key management.
Users can switch models, add API keys, and configure custom providers.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from agents.llm_provider import (
    get_router, get_settings, set_api_key,
    add_custom_provider, remove_custom_provider,
)

router = APIRouter()


class SwitchRequest(BaseModel):
    model_id: str


class ApiKeyRequest(BaseModel):
    provider: str     # "openrouter", "openai", "anthropic", "google", etc.
    api_key: str


class CustomProviderRequest(BaseModel):
    id: str           # unique identifier
    name: str         # display name
    base_url: str     # OpenAI-compatible API endpoint
    model: str        # model identifier
    api_key: str = ""
    provider_name: str = "custom"
    category: str = "general"
    context: int = 8192


@router.get("/models")
async def list_models():
    """List all available models (free + user-configured)."""
    llm = get_router()
    return {
        "active": llm.active_model_id,
        "models": llm.list_models(),
    }


@router.post("/select")
async def select_model(req: SwitchRequest):
    """Switch the active LLM model."""
    llm = get_router()
    llm.switch(req.model_id)
    return {
        "status": "switched",
        "active": llm.active_model_id,
        "name": llm.active.name,
    }


@router.get("/settings")
async def get_llm_settings():
    """Get current LLM settings (without exposing full API keys)."""
    settings = get_settings()
    # Mask API keys for security
    masked_keys = {}
    for provider, key in settings.get("api_keys", {}).items():
        if key:
            masked_keys[provider] = key[:8] + "..." + key[-4:] if len(key) > 12 else "****"
        else:
            masked_keys[provider] = ""
    return {
        "active_model": settings.get("active_model", ""),
        "api_keys": masked_keys,
        "custom_providers": settings.get("custom_providers", []),
    }


@router.post("/api-key")
async def save_api_key(req: ApiKeyRequest):
    """Save an API key for a provider."""
    if not req.provider:
        raise HTTPException(status_code=400, detail="Provider name required")
    result = set_api_key(req.provider, req.api_key)
    return result


@router.delete("/api-key/{provider}")
async def delete_api_key(provider: str):
    """Remove an API key for a provider."""
    result = set_api_key(provider, "")
    return result


@router.post("/custom-provider")
async def add_provider(req: CustomProviderRequest):
    """Add a custom OpenAI-compatible LLM provider."""
    provider = {
        "id": req.id,
        "name": req.name,
        "base_url": req.base_url,
        "model": req.model,
        "api_key": req.api_key,
        "provider_name": req.provider_name,
        "category": req.category,
        "context": req.context,
    }
    result = add_custom_provider(provider)
    return result


@router.delete("/custom-provider/{provider_id}")
async def delete_provider(provider_id: str):
    """Remove a custom provider."""
    result = remove_custom_provider(provider_id)
    return result


@router.post("/test")
async def test_provider():
    """Quick test of the active LLM provider."""
    llm = get_router()
    try:
        response = await llm.generate(
            "Respond with exactly: PARAKRAM_OK",
            max_tokens=20,
            temperature=0.0,
        )
        return {
            "model": llm.active_model_id,
            "provider": llm.active.name,
            "response": response.strip(),
            "ok": "PARAKRAM_OK" in response,
        }
    except Exception as e:
        return {"model": llm.active_model_id, "error": str(e), "ok": False}


@router.get("/status")
async def provider_status():
    """Check health of the active provider."""
    llm = get_router()
    return {
        "model": llm.active_model_id,
        "name": llm.active.name,
        "available": llm.active.is_available(),
    }
