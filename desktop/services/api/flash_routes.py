"""
Flash routes — device detection, firmware upload, serial monitor.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.flash_service import FlashService

router = APIRouter()
flash_svc = FlashService()


class FlashRequest(BaseModel):
    project_id: str
    port: str | None = None  # Auto-detect if not specified


@router.get("/devices")
async def list_devices():
    """Detect connected ESP32 devices."""
    devices = flash_svc.detect_devices()
    return {"devices": devices}


@router.post("/upload")
async def flash_device(request: FlashRequest):
    """Flash firmware to connected device."""
    try:
        result = await flash_svc.flash(
            project_id=request.project_id,
            port=request.port,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/monitor")
async def start_monitor(request: FlashRequest):
    """Start serial monitor for device."""
    try:
        result = flash_svc.start_monitor(
            port=request.port,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/monitor")
async def stop_monitor():
    """Stop serial monitor."""
    flash_svc.stop_monitor()
    return {"status": "stopped"}
