"""
Git Routes — Version control API for firmware projects.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from services.git_manager import GitManager, ProjectCleaner

router = APIRouter()


class GitInitRequest(BaseModel):
    project_dir: str


class GitCommitRequest(BaseModel):
    project_dir: str
    message: Optional[str] = None


class GitReleaseRequest(BaseModel):
    project_dir: str
    version: str
    notes: str = ""


class GitRemoteRequest(BaseModel):
    project_dir: str
    url: str
    name: str = "origin"


class GitPushRequest(BaseModel):
    project_dir: str
    remote: str = "origin"
    branch: str = "main"


@router.post("/init")
async def init_repo(req: GitInitRequest):
    """Initialize a git repository for a firmware project."""
    git = GitManager(req.project_dir)
    result = git.init()
    return result


@router.post("/commit")
async def auto_commit(req: GitCommitRequest):
    """Auto-commit all changes in a firmware project."""
    git = GitManager(req.project_dir)
    result = git.auto_commit(req.message)
    return result


@router.get("/history")
async def get_history(project_dir: str, limit: int = 20):
    """Get git commit history for a project."""
    git = GitManager(project_dir)
    commits = git.get_history(limit)
    return {"commits": commits, "total": len(commits)}


@router.post("/release")
async def create_release(req: GitReleaseRequest):
    """Create a tagged release for the firmware."""
    git = GitManager(req.project_dir)
    result = git.create_release(req.version, req.notes)
    return result


@router.post("/remote")
async def set_remote(req: GitRemoteRequest):
    """Set or update the git remote URL."""
    git = GitManager(req.project_dir)
    result = git.set_remote(req.url, req.name)
    return result


@router.post("/push")
async def push_to_remote(req: GitPushRequest):
    """Push commits and tags to remote repository."""
    git = GitManager(req.project_dir)
    result = git.push(req.remote, req.branch)
    return result


@router.post("/clean")
async def clean_project(project_dir: str):
    """Clean build artifacts to save disk space."""
    cleaner = ProjectCleaner(project_dir)
    result = cleaner.clean_build_artifacts()
    size = cleaner.get_project_size()
    return {**result, "size": size}


@router.get("/size")
async def get_project_size(project_dir: str):
    """Get project size breakdown."""
    cleaner = ProjectCleaner(project_dir)
    return cleaner.get_project_size()
