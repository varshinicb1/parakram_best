"""
Memory, Pinout, and WebSocket API Routes.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


# ── Memory Analyzer ────────────────────────────────────────

class MemoryAnalyzeRequest(BaseModel):
    board: str = "esp32"
    build_output: str = ""
    flash_used: int = 0
    ram_used: int = 0


class MemoryEstimateRequest(BaseModel):
    code: str
    board: str = "esp32"


@router.post("/memory/analyze")
async def analyze_memory(req: MemoryAnalyzeRequest):
    """Analyze memory usage from build output or known sizes."""
    from services.memory_analyzer import get_memory_analyzer
    analyzer = get_memory_analyzer()
    if req.build_output:
        return analyzer.analyze_from_build_output(req.build_output, req.board)
    return analyzer.analyze_from_sizes(req.board, req.flash_used, req.ram_used)


@router.post("/memory/estimate")
async def estimate_memory(req: MemoryEstimateRequest):
    """Estimate memory usage from source code."""
    from services.memory_analyzer import get_memory_analyzer
    analyzer = get_memory_analyzer()
    return analyzer.estimate_from_code(req.code, req.board)


# ── Pinout Visualizer ──────────────────────────────────────

@router.get("/pinout/{board_id}")
async def get_pinout(board_id: str):
    """Get pinout diagram data for a board."""
    from services.pinout_visualizer import get_pinout as _get
    data = _get(board_id)
    if not data:
        from fastapi import HTTPException
        raise HTTPException(404, f"Pinout not available for '{board_id}'")
    return data


@router.get("/pinout")
async def list_pinouts():
    """List boards with available pinout data."""
    from services.pinout_visualizer import list_available_pinouts
    return {"boards": list_available_pinouts()}


# ── WebSocket ──────────────────────────────────────────────

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Real-time WebSocket for pipeline progress, build logs, and serial data."""
    from services.ws_manager import get_ws_manager
    manager = get_ws_manager()
    await manager.connect(websocket)

    # Send current pipeline state on connect
    try:
        status = manager.get_pipeline_status()
        if status:
            await websocket.send_json({"type": "state_sync", "pipeline": status})

        while True:
            data = await websocket.receive_text()
            # Handle client commands
            import json
            msg = json.loads(data)
            if msg.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)
