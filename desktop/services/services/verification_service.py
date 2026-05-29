"""
Verification Service
Manages user verification prompts and stores results.
"""

import os
import json
from datetime import datetime
from storage.version_manager import VersionManager


class VerificationService:
    """Manages user verification of firmware behavior."""

    def __init__(self):
        self.projects_dir = os.environ.get("PROJECTS_DIR", "../projects")
        self.version_manager = VersionManager()

    def create_verification_prompt(
        self, project_id: str, expected_behaviors: list[str]
    ) -> dict:
        """
        Create a verification prompt for the user.
        Lists expected behaviors that the user should confirm.
        """
        return {
            "project_id": project_id,
            "timestamp": datetime.now().isoformat(),
            "prompt": "Please verify the following behaviors on your device:",
            "checks": [
                {"id": i, "description": behavior, "status": "pending"}
                for i, behavior in enumerate(expected_behaviors)
            ],
        }

    def submit_verification(
        self,
        project_id: str,
        results: list[dict],
        notes: str = "",
    ) -> dict:
        """
        Submit user verification results.
        Creates a version snapshot with the results.
        """
        verification = {
            "timestamp": datetime.now().isoformat(),
            "results": results,
            "notes": notes,
            "all_passed": all(r.get("passed", False) for r in results),
        }

        # Save verification log
        log_dir = os.path.join(self.projects_dir, project_id, "logs")
        os.makedirs(log_dir, exist_ok=True)

        log_file = os.path.join(
            log_dir,
            f"verification_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        )
        with open(log_file, "w") as f:
            json.dump(verification, f, indent=2)

        # Create version snapshot
        self.version_manager.create_snapshot(
            project_id,
            trigger="user_verification",
            metadata={"verification": verification},
        )

        return verification
