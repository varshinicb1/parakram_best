"""
Version Manager
Automatic version snapshots — copies project state to timestamped dirs.
"""

import os
import json
import shutil
from datetime import datetime


class VersionManager:
    """Manages automatic version snapshots of projects."""

    def __init__(self):
        self.projects_dir = os.environ.get("PROJECTS_DIR", "../projects")

    def create_snapshot(
        self,
        project_id: str,
        trigger: str = "manual",
        metadata: dict | None = None,
    ) -> dict:
        """
        Create a version snapshot of the current project state.

        Triggers:
        - "block_change": Blocks were added/removed/connected
        - "compile_success": Firmware compiled successfully
        - "build_success": Full generate + compile succeeded
        - "user_verification": User submitted verification results
        - "manual": User-initiated snapshot

        Copies: canvas.json, hardware_config.json, firmware/
        """
        project_dir = os.path.join(self.projects_dir, project_id)
        versions_dir = os.path.join(project_dir, "versions")

        if not os.path.exists(project_dir):
            return {"status": "error", "message": "Project not found"}

        os.makedirs(versions_dir, exist_ok=True)

        # Get next version number
        existing = [d for d in os.listdir(versions_dir) if d.startswith("v")]
        version_num = len(existing) + 1
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        version_name = f"v{version_num:03d}_{timestamp}"

        snapshot_dir = os.path.join(versions_dir, version_name)
        os.makedirs(snapshot_dir)

        # Copy key files
        files_to_copy = ["canvas.json", "hardware_config.json"]
        for f in files_to_copy:
            src = os.path.join(project_dir, f)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(snapshot_dir, f))

        # Copy firmware directory
        firmware_src = os.path.join(project_dir, "firmware")
        if os.path.exists(firmware_src):
            firmware_dst = os.path.join(snapshot_dir, "firmware")
            shutil.copytree(
                firmware_src, firmware_dst,
                ignore=shutil.ignore_patterns(".pio", ".pioenvs"),
            )

        # Save version metadata
        version_meta = {
            "version": version_num,
            "name": version_name,
            "trigger": trigger,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
        }
        with open(os.path.join(snapshot_dir, "version.json"), "w") as f:
            json.dump(version_meta, f, indent=2)

        return {
            "status": "created",
            "version": version_num,
            "name": version_name,
            "trigger": trigger,
        }

    def list_versions(self, project_id: str) -> list[dict]:
        """List all version snapshots for a project."""
        versions_dir = os.path.join(self.projects_dir, project_id, "versions")
        if not os.path.exists(versions_dir):
            return []

        versions = []
        for d in sorted(os.listdir(versions_dir)):
            meta_path = os.path.join(versions_dir, d, "version.json")
            if os.path.isfile(meta_path):
                with open(meta_path) as f:
                    versions.append(json.load(f))
        return versions

    def restore_version(self, project_id: str, version_name: str) -> dict:
        """Restore a project to a specific version snapshot."""
        project_dir = os.path.join(self.projects_dir, project_id)
        snapshot_dir = os.path.join(project_dir, "versions", version_name)

        if not os.path.exists(snapshot_dir):
            return {"status": "error", "message": "Version not found"}

        # Create a backup of current state first
        self.create_snapshot(project_id, trigger="pre_restore_backup")

        # Restore files
        for f in ["canvas.json", "hardware_config.json"]:
            src = os.path.join(snapshot_dir, f)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(project_dir, f))

        # Restore firmware
        firmware_src = os.path.join(snapshot_dir, "firmware")
        firmware_dst = os.path.join(project_dir, "firmware")
        if os.path.exists(firmware_src):
            if os.path.exists(firmware_dst):
                shutil.rmtree(firmware_dst)
            shutil.copytree(firmware_src, firmware_dst)

        return {
            "status": "restored",
            "version": version_name,
        }
