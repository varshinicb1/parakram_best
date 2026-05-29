"""
Git Manager — Automatic version control for firmware projects.
Auto-init, auto-commit, auto-push, and release management.
"""

import os
import subprocess
import shutil
from datetime import datetime
from typing import Optional


class GitManager:
    """Manages git operations for firmware projects."""

    def __init__(self, project_dir: str):
        self.project_dir = project_dir
        self.git_dir = os.path.join(project_dir, ".git")

    def _run(self, *args, cwd: str = None) -> tuple[int, str, str]:
        """Run a git command and return (returncode, stdout, stderr)."""
        try:
            result = subprocess.run(
                ["git"] + list(args),
                cwd=cwd or self.project_dir,
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.returncode, result.stdout.strip(), result.stderr.strip()
        except FileNotFoundError:
            return -1, "", "git not found in PATH"
        except subprocess.TimeoutExpired:
            return -1, "", "git command timed out"

    def is_initialized(self) -> bool:
        return os.path.isdir(self.git_dir)

    def init(self) -> dict:
        """Initialize a git repo with sensible defaults."""
        if self.is_initialized():
            return {"status": "already_initialized", "path": self.project_dir}

        code, out, err = self._run("init")
        if code != 0:
            return {"status": "error", "error": err}

        # Create .gitignore for embedded projects
        gitignore_path = os.path.join(self.project_dir, ".gitignore")
        if not os.path.exists(gitignore_path):
            with open(gitignore_path, "w") as f:
                f.write(
                    ".pio/\n"
                    "build/\n"
                    "__pycache__/\n"
                    "*.o\n"
                    "*.elf\n"
                    "*.bin\n"
                    "*.hex\n"
                    ".vscode/\n"
                    "node_modules/\n"
                    ".DS_Store\n"
                )

        # Initial commit
        self._run("add", "-A")
        self._run("commit", "-m", "Initial commit — Parakram firmware project")

        return {"status": "initialized", "path": self.project_dir}

    def auto_commit(self, message: Optional[str] = None) -> dict:
        """Auto-commit all changes with a descriptive message."""
        if not self.is_initialized():
            self.init()

        # Check for changes
        code, out, _ = self._run("status", "--porcelain")
        if not out:
            return {"status": "no_changes"}

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        commit_msg = message or f"[Parakram] Auto-commit firmware update — {timestamp}"

        self._run("add", "-A")
        code, out, err = self._run("commit", "-m", commit_msg)

        if code == 0:
            # Get commit hash
            _, hash_out, _ = self._run("rev-parse", "--short", "HEAD")
            return {"status": "committed", "hash": hash_out, "message": commit_msg}
        else:
            return {"status": "error", "error": err}

    def get_history(self, limit: int = 20) -> list[dict]:
        """Get commit history."""
        if not self.is_initialized():
            return []

        code, out, _ = self._run(
            "log", f"--max-count={limit}",
            "--format=%H|%h|%s|%ai|%an"
        )

        if code != 0 or not out:
            return []

        commits = []
        for line in out.split("\n"):
            parts = line.split("|", 4)
            if len(parts) == 5:
                commits.append({
                    "hash": parts[0],
                    "short_hash": parts[1],
                    "message": parts[2],
                    "date": parts[3],
                    "author": parts[4],
                })
        return commits

    def create_release(self, version: str, notes: str = "") -> dict:
        """Create a tagged release."""
        if not self.is_initialized():
            return {"status": "error", "error": "Not a git repo"}

        # Auto-commit any pending changes
        self.auto_commit(f"[Release] v{version}")

        # Create tag
        tag_msg = notes or f"Parakram firmware release v{version}"
        code, out, err = self._run("tag", "-a", f"v{version}", "-m", tag_msg)

        if code == 0:
            return {"status": "released", "version": version, "tag": f"v{version}"}
        else:
            return {"status": "error", "error": err}

    def set_remote(self, url: str, name: str = "origin") -> dict:
        """Set or update the git remote."""
        # Check if remote exists
        code, out, _ = self._run("remote", "get-url", name)
        if code == 0:
            self._run("remote", "set-url", name, url)
        else:
            self._run("remote", "add", name, url)

        return {"status": "remote_set", "name": name, "url": url}

    def push(self, remote: str = "origin", branch: str = "main") -> dict:
        """Push commits and tags to remote."""
        code, out, err = self._run("push", remote, branch)
        tag_code, _, _ = self._run("push", remote, "--tags")

        if code == 0:
            return {"status": "pushed", "remote": remote, "branch": branch}
        else:
            return {"status": "error", "error": err}

    def diff(self, commit: str = "HEAD~1") -> str:
        """Get diff since a given commit."""
        code, out, _ = self._run("diff", commit)
        return out if code == 0 else ""


class ProjectCleaner:
    """Auto-clean build artifacts to save disk space."""

    CLEAN_PATTERNS = [
        ".pio/build",
        "build/",
        "__pycache__",
    ]

    def __init__(self, project_dir: str):
        self.project_dir = project_dir

    def clean_build_artifacts(self) -> dict:
        """Remove build artifacts after successful flash."""
        removed = []
        for pattern in self.CLEAN_PATTERNS:
            path = os.path.join(self.project_dir, pattern)
            if os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
                removed.append(pattern)

        return {"status": "cleaned", "removed": removed}

    def get_project_size(self) -> dict:
        """Calculate project size breakdown."""
        total = 0
        source_size = 0
        build_size = 0

        for root, dirs, files in os.walk(self.project_dir):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    size = os.path.getsize(fp)
                    total += size
                    if ".pio" in root or "build" in root:
                        build_size += size
                    else:
                        source_size += size
                except OSError:
                    pass

        return {
            "total_mb": round(total / 1048576, 2),
            "source_mb": round(source_size / 1048576, 2),
            "build_mb": round(build_size / 1048576, 2),
        }
