"""
OTA and Power Profiler API Routes.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


# ── Power Profiler ─────────────────────────────────────────

class PowerProfileRequest(BaseModel):
    board: str
    peripherals: list[str] = []
    duty_cycles: dict = {}


class BoardCompareRequest(BaseModel):
    boards: list[str]
    peripherals: list[str] = []


@router.post("/power/profile")
async def power_profile(req: PowerProfileRequest):
    """Generate detailed power consumption profile."""
    from services.power_profiler import get_power_profiler
    profiler = get_power_profiler()
    return profiler.profile(req.board, req.peripherals, req.duty_cycles)


@router.post("/power/compare")
async def power_compare(req: BoardCompareRequest):
    """Compare power across multiple boards."""
    from services.power_profiler import get_power_profiler
    profiler = get_power_profiler()
    return profiler.compare_boards(req.boards, req.peripherals)


# ── OTA Manager ────────────────────────────────────────────

class OTAReleaseRequest(BaseModel):
    project: str
    version: str
    board: str
    firmware_path: str
    changelog: str = ""


class OTACheckRequest(BaseModel):
    project: str
    board: str
    current_version: str


class OTACodeRequest(BaseModel):
    project: str
    board: str
    server_url: str = "http://192.168.1.100:8000"


@router.post("/ota/release")
async def create_ota_release(req: OTAReleaseRequest):
    """Create a new OTA firmware release."""
    from services.ota_manager import get_ota_manager
    mgr = get_ota_manager()
    return mgr.create_release(req.project, req.version, req.board, req.firmware_path, req.changelog)


@router.get("/ota/{project}/releases")
async def list_ota_releases(project: str):
    """List all OTA releases for a project."""
    from services.ota_manager import get_ota_manager
    mgr = get_ota_manager()
    return {"releases": mgr.list_releases(project)}


@router.post("/ota/check")
async def check_ota_update(req: OTACheckRequest):
    """Check if firmware update is available."""
    from services.ota_manager import get_ota_manager
    mgr = get_ota_manager()
    return mgr.check_update(req.project, req.board, req.current_version)


@router.post("/ota/generate-code")
async def generate_ota_code(req: OTACodeRequest):
    """Generate OTA client code for Arduino/ESP32."""
    from services.ota_manager import get_ota_manager
    mgr = get_ota_manager()
    code = mgr.generate_ota_code(req.project, req.board, req.server_url)
    return {"code": code, "language": "cpp"}
