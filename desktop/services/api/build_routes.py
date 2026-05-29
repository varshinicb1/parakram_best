"""
Build routes — firmware generation and PlatformIO compilation.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.firmware_generator import FirmwareGenerator
from services.build_service import BuildService
from storage.project_manager import ProjectManager
from storage.version_manager import VersionManager

router = APIRouter()
pm = ProjectManager()
vm = VersionManager()
firmware_gen = FirmwareGenerator()
build_svc = BuildService()


class BuildRequest(BaseModel):
    project_id: str
    max_retries: int = 3


class BuildResponse(BaseModel):
    status: str
    message: str
    errors: list[str] = []
    output: str = ""


@router.post("/generate")
async def generate_firmware(request: BuildRequest):
    """Generate firmware from canvas graph."""
    canvas = pm.load_canvas(request.project_id)
    if canvas is None:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        result = await firmware_gen.generate(request.project_id, canvas)
        return {"status": "generated", "files": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compile")
async def compile_firmware(request: BuildRequest):
    """Compile firmware using PlatformIO."""
    project = pm.get_project(request.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    result = await build_svc.compile(
        project_id=request.project_id,
        max_retries=request.max_retries,
    )

    # Snapshot on successful compile
    if result["status"] == "success":
        vm.create_snapshot(request.project_id, trigger="compile_success")

    return result


@router.post("/generate-and-compile")
async def generate_and_compile(request: BuildRequest):
    """Generate firmware from canvas and compile in one step."""
    canvas = pm.load_canvas(request.project_id)
    if canvas is None:
        raise HTTPException(status_code=404, detail="Project not found")

    # Generate
    try:
        files = await firmware_gen.generate(request.project_id, canvas)
    except Exception as e:
        return BuildResponse(status="generation_failed", message=str(e))

    # Compile with retries
    result = await build_svc.compile(
        project_id=request.project_id,
        max_retries=request.max_retries,
    )

    if result["status"] == "success":
        vm.create_snapshot(request.project_id, trigger="build_success")

    return result


@router.get("/status/{project_id}")
async def build_status(project_id: str):
    """Get the current build status for a project."""
    status = build_svc.get_status(project_id)
    return {"project_id": project_id, "status": status}
