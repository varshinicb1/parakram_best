"""
Extension API Routes — Extension lifecycle management.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from services.extension_manager import get_extension_manager

router = APIRouter()


class InstallRequest(BaseModel):
    manifest: dict


class ToggleRequest(BaseModel):
    enabled: bool


@router.get("/list")
async def list_extensions():
    mgr = get_extension_manager()
    mgr.discover()
    return {"extensions": mgr.list_all()}


@router.get("/marketplace")
async def marketplace():
    mgr = get_extension_manager()
    return {"available": mgr.get_marketplace()}


@router.post("/install")
async def install_extension(req: InstallRequest):
    mgr = get_extension_manager()
    result = mgr.install_from_dict(req.manifest)
    return {"message": result}


@router.put("/{ext_id}/toggle")
async def toggle_extension(ext_id: str, req: ToggleRequest):
    mgr = get_extension_manager()
    if req.enabled:
        success = mgr.enable(ext_id)
    else:
        success = mgr.disable(ext_id)
    if not success:
        raise HTTPException(404, "Extension not found")
    return {"id": ext_id, "enabled": req.enabled}


@router.delete("/{ext_id}")
async def uninstall_extension(ext_id: str):
    mgr = get_extension_manager()
    result = mgr.uninstall(ext_id)
    return {"message": result}


@router.post("/{ext_id}/load")
async def load_extension(ext_id: str):
    mgr = get_extension_manager()
    success = mgr.load_extension(ext_id)
    if not success:
        raise HTTPException(400, "Failed to load extension")
    return {"id": ext_id, "loaded": True}
