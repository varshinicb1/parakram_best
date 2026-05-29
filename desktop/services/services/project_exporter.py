"""
Project Export/Import — Zip packaging and sharing.

Features:
  - Export project as .zip with all source, config, and metadata
  - Import projects from .zip
  - Generate sharable project bundle with README
  - Clean export (exclude build artifacts, .pio, node_modules)
"""

import os
import json
import zipfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional


class ProjectExporter:
    """Export and import Parakram projects."""

    EXPORT_DIR = Path("./storage/exports")
    PROJECTS_DIR = Path("./projects")

    # Directories/files to exclude from export
    EXCLUDES = {
        ".pio", ".vscode", "node_modules", "__pycache__", ".git",
        ".DS_Store", "Thumbs.db", "*.pyc", "*.o", "*.elf", "*.bin",
    }

    def __init__(self):
        self.EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    def export_project(self, project_name: str, include_readme: bool = True) -> dict:
        """Export a project as a zip file."""
        project_dir = self.PROJECTS_DIR / project_name
        if not project_dir.exists():
            return {"error": f"Project '{project_name}' not found"}

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_name = f"{project_name}_{timestamp}.zip"
        zip_path = self.EXPORT_DIR / zip_name

        file_count = 0
        total_size = 0

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(project_dir):
                # Skip excluded directories
                dirs[:] = [d for d in dirs if d not in self.EXCLUDES]

                for file in files:
                    if any(file.endswith(ext.replace("*", "")) for ext in self.EXCLUDES if "*" in ext):
                        continue
                    if file in self.EXCLUDES:
                        continue

                    file_path = Path(root) / file
                    arcname = file_path.relative_to(project_dir)
                    zf.write(file_path, arcname)
                    file_count += 1
                    total_size += file_path.stat().st_size

            # Add README if requested
            if include_readme:
                readme = self._generate_readme(project_name, project_dir)
                zf.writestr("README.md", readme)

            # Add Parakram metadata
            metadata = {
                "project": project_name,
                "exported_at": datetime.now().isoformat(),
                "exported_by": "Parakram OS",
                "version": "2.0.0",
                "files": file_count,
            }
            zf.writestr(".parakram.json", json.dumps(metadata, indent=2))

        return {
            "zip_file": zip_name,
            "path": str(zip_path),
            "files": file_count,
            "size_bytes": zip_path.stat().st_size,
            "size_kb": round(zip_path.stat().st_size / 1024, 1),
        }

    def import_project(self, zip_path: str, new_name: Optional[str] = None) -> dict:
        """Import a project from a zip file."""
        src = Path(zip_path)
        if not src.exists():
            return {"error": f"Zip file not found: {zip_path}"}

        # Determine project name
        with zipfile.ZipFile(src, 'r') as zf:
            # Check for Parakram metadata
            meta = None
            if ".parakram.json" in zf.namelist():
                meta = json.loads(zf.read(".parakram.json"))
                name = new_name or meta.get("project", src.stem)
            else:
                name = new_name or src.stem

            dest = self.PROJECTS_DIR / name
            if dest.exists():
                return {"error": f"Project '{name}' already exists"}

            zf.extractall(dest)

        file_count = sum(1 for _ in dest.rglob("*") if _.is_file())
        return {
            "project": name,
            "path": str(dest),
            "files": file_count,
            "imported_from": str(src),
            "has_metadata": meta is not None,
        }

    def list_exports(self) -> list[dict]:
        """List all exported zip files."""
        exports = []
        for f in sorted(self.EXPORT_DIR.glob("*.zip"), reverse=True):
            exports.append({
                "name": f.name,
                "size_kb": round(f.stat().st_size / 1024, 1),
                "created": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
            })
        return exports

    def _generate_readme(self, name: str, project_dir: Path) -> str:
        """Generate a README.md for the exported project."""
        ini_path = project_dir / "platformio.ini"
        board = "unknown"
        if ini_path.exists():
            for line in ini_path.read_text().split("\n"):
                if "board" in line and "=" in line:
                    board = line.split("=")[1].strip()
                    break

        src_files = list((project_dir / "src").rglob("*")) if (project_dir / "src").exists() else []
        lib_files = list((project_dir / "lib").rglob("*")) if (project_dir / "lib").exists() else []

        return f"""# {name}

> Generated by [Parakram](https://github.com/varshinicb1/parakram) by Vidyutlabs — Open-Source Firmware Platform

## Board
- **Target**: `{board}`
- **Framework**: Arduino / PlatformIO

## Project Structure
```
{name}/
├── src/          # Source code ({len(src_files)} files)
├── lib/          # Libraries ({len(lib_files)} files)
├── include/      # Headers
└── platformio.ini
```

## Build & Flash
```bash
# Install PlatformIO
pip install platformio

# Build
pio run

# Upload to board
pio run --target upload

# Monitor serial output
pio device monitor --baud 115200
```

## Generated by Parakram OS
This project was created using Parakram — the open-source firmware development platform by Vidyutlabs.
Visit [vidyutlabs.com/parakram](https://vidyutlabs.com/parakram) for more info.
"""

    def cleanup_old_exports(self, keep_latest: int = 10) -> int:
        """Remove old exports, keep only latest N."""
        exports = sorted(self.EXPORT_DIR.glob("*.zip"), key=lambda f: f.stat().st_mtime, reverse=True)
        removed = 0
        for f in exports[keep_latest:]:
            f.unlink()
            removed += 1
        return removed


def get_project_exporter() -> ProjectExporter:
    return ProjectExporter()
