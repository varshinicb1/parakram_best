"""
Project routes — CRUD operations for Parakram projects.
"""

from fastapi import APIRouter, HTTPException
from models.graph_model import ProjectMeta
from storage.project_manager import ProjectManager

router = APIRouter()
pm = ProjectManager()


@router.get("/")
async def list_projects():
    """List all projects."""
    projects = pm.list_projects()
    return {"projects": projects}


@router.post("/")
async def create_project(project: ProjectMeta):
    """Create a new project."""
    try:
        result = pm.create_project(project)
        return {"status": "created", "project": result}
    except FileExistsError:
        raise HTTPException(status_code=409, detail="Project already exists")


@router.get("/{project_id}")
async def get_project(project_id: str):
    """Get project details."""
    project = pm.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.delete("/{project_id}")
async def delete_project(project_id: str):
    """Delete a project."""
    success = pm.delete_project(project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"status": "deleted", "project_id": project_id}
