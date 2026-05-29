"""
Project Manager
File-based project CRUD — each project is a directory with JSON metadata.
"""

import os
import json
import shutil
from datetime import datetime
from models.graph_model import CanvasGraph, ProjectMeta


class ProjectManager:
    """Manages project directories and their contents."""

    def __init__(self):
        self.projects_dir = os.environ.get("PROJECTS_DIR", "../projects")
        os.makedirs(self.projects_dir, exist_ok=True)

    def create_project(self, project: ProjectMeta) -> dict:
        """Create a new project directory with scaffolding."""
        project_dir = os.path.join(self.projects_dir, project.id)

        if os.path.exists(project_dir):
            raise FileExistsError(f"Project {project.id} already exists")

        # Create directory structure
        os.makedirs(project_dir)
        os.makedirs(os.path.join(project_dir, "firmware", "src"), exist_ok=True)
        os.makedirs(os.path.join(project_dir, "firmware", "include"), exist_ok=True)
        os.makedirs(os.path.join(project_dir, "versions"), exist_ok=True)
        os.makedirs(os.path.join(project_dir, "logs"), exist_ok=True)

        # Set timestamps
        now = datetime.now().isoformat()
        project_data = project.model_dump()
        project_data["created_at"] = now
        project_data["updated_at"] = now

        # Save project metadata
        meta_path = os.path.join(project_dir, "project.json")
        with open(meta_path, "w") as f:
            json.dump(project_data, f, indent=2)

        # Create empty canvas
        canvas = {"nodes": [], "edges": []}
        canvas_path = os.path.join(project_dir, "canvas.json")
        with open(canvas_path, "w") as f:
            json.dump(canvas, f, indent=2)

        # Create hardware config
        hw_config = {
            "board": project.target_board,
            "framework": project.framework,
            "pins_used": {},
            "libraries": [],
        }
        hw_path = os.path.join(project_dir, "hardware_config.json")
        with open(hw_path, "w") as f:
            json.dump(hw_config, f, indent=2)

        return project_data

    def list_projects(self) -> list[dict]:
        """List all projects with metadata."""
        projects = []
        if not os.path.exists(self.projects_dir):
            return projects

        for item in os.listdir(self.projects_dir):
            meta_path = os.path.join(self.projects_dir, item, "project.json")
            if os.path.isfile(meta_path):
                with open(meta_path) as f:
                    projects.append(json.load(f))
        return projects

    def get_project(self, project_id: str) -> dict | None:
        """Get project metadata."""
        meta_path = os.path.join(self.projects_dir, project_id, "project.json")
        if not os.path.isfile(meta_path):
            return None
        with open(meta_path) as f:
            return json.load(f)

    def delete_project(self, project_id: str) -> bool:
        """Delete a project directory."""
        project_dir = os.path.join(self.projects_dir, project_id)
        if not os.path.exists(project_dir):
            return False
        shutil.rmtree(project_dir)
        return True

    def load_canvas(self, project_id: str) -> dict | None:
        """Load canvas graph from project."""
        canvas_path = os.path.join(self.projects_dir, project_id, "canvas.json")
        if not os.path.isfile(canvas_path):
            return None
        with open(canvas_path) as f:
            return json.load(f)

    def save_canvas(self, project_id: str, graph: CanvasGraph) -> bool:
        """Save canvas graph to project."""
        project_dir = os.path.join(self.projects_dir, project_id)
        if not os.path.exists(project_dir):
            return False

        canvas_path = os.path.join(project_dir, "canvas.json")
        with open(canvas_path, "w") as f:
            json.dump(graph.model_dump(), f, indent=2)

        # Update project timestamp
        meta_path = os.path.join(project_dir, "project.json")
        if os.path.isfile(meta_path):
            with open(meta_path) as f:
                meta = json.load(f)
            meta["updated_at"] = datetime.now().isoformat()
            with open(meta_path, "w") as f:
                json.dump(meta, f, indent=2)

        return True
