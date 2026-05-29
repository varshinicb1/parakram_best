"""
Board and Export API Routes.
"""

from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


# ── Board Database ─────────────────────────────────────────

class BoardSearchRequest(BaseModel):
    query: str = ""
    has_wifi: bool = False
    has_ble: bool = False
    min_flash_kb: int = 0
    min_ram_kb: int = 0


@router.get("/boards")
async def list_boards():
    """List all supported boards."""
    from agents.board_database import list_all_boards
    return {"boards": list_all_boards(), "count": len(list_all_boards())}


@router.get("/boards/{board_id}")
async def get_board_info(board_id: str):
    """Get detailed info for a specific board."""
    from agents.board_database import get_board
    info = get_board(board_id)
    if not info:
        from fastapi import HTTPException
        raise HTTPException(404, "Board not found")
    return info


@router.post("/boards/search")
async def search_boards_route(req: BoardSearchRequest):
    """Search boards with filters."""
    from agents.board_database import search_boards
    results = search_boards(req.query, req.has_wifi, req.has_ble, req.min_flash_kb, req.min_ram_kb)
    return {"boards": results, "count": len(results)}


@router.get("/boards/{board_id}/platformio")
async def get_platformio_config(board_id: str):
    """Get PlatformIO env config for a board."""
    from agents.board_database import get_platformio_env
    return {"config": get_platformio_env(board_id)}


# ── Project Export/Import ──────────────────────────────────

class ExportRequest(BaseModel):
    project_name: str
    include_readme: bool = True


class ImportRequest(BaseModel):
    zip_path: str
    new_name: Optional[str] = None


@router.post("/export")
async def export_project(req: ExportRequest):
    """Export project as zip."""
    from services.project_exporter import get_project_exporter
    exporter = get_project_exporter()
    return exporter.export_project(req.project_name, req.include_readme)


@router.post("/import")
async def import_project(req: ImportRequest):
    """Import project from zip."""
    from services.project_exporter import get_project_exporter
    exporter = get_project_exporter()
    return exporter.import_project(req.zip_path, req.new_name)


@router.get("/exports")
async def list_exports():
    """List all exported project zips."""
    from services.project_exporter import get_project_exporter
    exporter = get_project_exporter()
    return {"exports": exporter.list_exports()}
