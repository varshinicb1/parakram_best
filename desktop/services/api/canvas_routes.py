"""
Canvas routes — save/load canvas graph state.
"""

from fastapi import APIRouter, HTTPException
from models.graph_model import CanvasGraph
from storage.project_manager import ProjectManager

router = APIRouter()
pm = ProjectManager()


@router.get("/{project_id}")
async def get_canvas(project_id: str):
    """Load canvas graph for a project."""
    canvas = pm.load_canvas(project_id)
    if canvas is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return canvas


@router.put("/{project_id}")
async def save_canvas(project_id: str, graph: CanvasGraph):
    """Save canvas graph for a project."""
    success = pm.save_canvas(project_id, graph)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"status": "saved", "node_count": len(graph.nodes), "edge_count": len(graph.edges)}


@router.post("/{project_id}/export")
async def export_canvas(project_id: str):
    """Export canvas as downloadable JSON."""
    canvas = pm.load_canvas(project_id)
    if canvas is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return canvas
