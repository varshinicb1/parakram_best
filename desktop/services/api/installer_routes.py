"""
Installer API Routes — Toolchain status, installation, and auto library resolution.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from services.installer_service import ToolchainInstaller, LibraryAutoInstaller

router = APIRouter()


class InstallRequest(BaseModel):
    toolchain_id: str


class LibraryResolveRequest(BaseModel):
    source_code: str
    project_dir: str = "./firmware_output"


class LibraryInstallRequest(BaseModel):
    project_dir: str
    libraries: list[str]


@router.get("/toolchains")
async def list_toolchains():
    """Check status of all supported toolchains."""
    results = await ToolchainInstaller.check_all()
    return {"toolchains": results}


@router.post("/toolchains/install")
async def install_toolchain(req: InstallRequest):
    """Install a specific toolchain."""
    result = await ToolchainInstaller.install(req.toolchain_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/toolchains/{toolchain_id}")
async def check_toolchain(toolchain_id: str):
    """Check if a specific toolchain is installed."""
    result = await ToolchainInstaller.check_installed(toolchain_id)
    return result


@router.post("/libraries/resolve")
async def resolve_libraries(req: LibraryResolveRequest):
    """Resolve library dependencies from source code."""
    resolution = LibraryAutoInstaller.resolve_libraries(req.source_code)
    return resolution


@router.post("/libraries/install")
async def install_libraries(req: LibraryInstallRequest):
    """Install specific libraries via PlatformIO."""
    result = await LibraryAutoInstaller.install_libraries(req.project_dir, req.libraries)
    return result


@router.post("/libraries/auto-install")
async def auto_install(req: LibraryResolveRequest):
    """Auto-detect and install libraries from source code."""
    result = await LibraryAutoInstaller.auto_install_from_code(req.project_dir, req.source_code)
    return result
