"""
Gallery and Crash Decoder Routes.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class CrashDecodeRequest(BaseModel):
    dump: str


class GallerySearchRequest(BaseModel):
    query: str = ""
    tag: str = ""
    difficulty: str = ""


# ── Crash Decoder ──────────────────────────────────────────

@router.post("/crash/decode")
async def decode_crash(req: CrashDecodeRequest):
    """Decode a crash dump from ESP32/STM32/RP2040."""
    from services.crash_decoder import get_crash_decoder
    decoder = get_crash_decoder()
    return decoder.decode(req.dump)


# ── Project Gallery ────────────────────────────────────────

@router.get("/gallery/templates")
async def list_gallery():
    """List all project templates."""
    from services.project_gallery import get_gallery_templates
    return {"templates": get_gallery_templates()}


@router.post("/gallery/search")
async def search_gallery_route(req: GallerySearchRequest):
    """Search project templates."""
    from services.project_gallery import search_gallery
    results = search_gallery(req.query, req.tag, req.difficulty)
    return {"results": results, "count": len(results)}
