"""
Workspace Routes — File management within project directories.
VS Code-style file CRUD for the workspace editor.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
import json
import os

router = APIRouter()

PROJECTS_DIR = Path("./projects")
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)


class FileWriteRequest(BaseModel):
    path: str  # relative to project
    content: str


class FileRenameRequest(BaseModel):
    old_path: str
    new_path: str


class ProjectCreateRequest(BaseModel):
    name: str
    board: str = "esp32dev"
    template: str = "blank"  # blank, blink, sensor, iot


@router.get("/projects")
async def list_projects():
    """List all projects in workspace."""
    projects = []
    for entry in PROJECTS_DIR.iterdir():
        if entry.is_dir():
            ini_file = entry / "platformio.ini"
            projects.append({
                "name": entry.name,
                "path": str(entry),
                "has_platformio": ini_file.exists(),
                "file_count": sum(1 for _ in entry.rglob("*") if _.is_file()),
            })
    return {"projects": projects}


@router.post("/projects/create")
async def create_project(req: ProjectCreateRequest):
    """Create a new PlatformIO project."""
    project_dir = PROJECTS_DIR / req.name
    if project_dir.exists():
        raise HTTPException(400, f"Project '{req.name}' already exists")

    src_dir = project_dir / "src"
    include_dir = project_dir / "include"
    lib_dir = project_dir / "lib"
    src_dir.mkdir(parents=True)
    include_dir.mkdir(parents=True)
    lib_dir.mkdir(parents=True)

    # platformio.ini
    platform_map = {
        "esp32dev": "espressif32", "esp32-s3-devkitc-1": "espressif32",
        "esp32-c3-devkitm-1": "espressif32", "pico": "raspberrypi",
        "nucleo_f446re": "ststm32", "megaatmega2560": "atmelavr",
    }
    (project_dir / "platformio.ini").write_text(f"""[env:{req.board}]
platform = {platform_map.get(req.board, "espressif32")}
board = {req.board}
framework = arduino
monitor_speed = 115200
""")

    # Template code
    templates = {
        "blank": '#include <Arduino.h>\n\nvoid setup() {\n    Serial.begin(115200);\n    Serial.println("Parakram Project Ready");\n}\n\nvoid loop() {\n    // Your code here\n}\n',
        "blink": '#include <Arduino.h>\n\n#define LED_PIN 2\n\nvoid setup() {\n    Serial.begin(115200);\n    pinMode(LED_PIN, OUTPUT);\n    Serial.println("Blink Ready");\n}\n\nvoid loop() {\n    digitalWrite(LED_PIN, HIGH);\n    delay(500);\n    digitalWrite(LED_PIN, LOW);\n    delay(500);\n}\n',
        "sensor": '#include <Arduino.h>\n#include <Wire.h>\n\nvoid setup() {\n    Serial.begin(115200);\n    Wire.begin();\n    Serial.println("Sensor Project Ready");\n}\n\nvoid loop() {\n    // Read sensor data\n    Serial.println("Reading sensors...");\n    delay(1000);\n}\n',
        "iot": '#include <Arduino.h>\n#include <WiFi.h>\n\nconst char* WIFI_SSID = "YOUR_SSID";\nconst char* WIFI_PASS = "YOUR_PASS";\n\nvoid setup() {\n    Serial.begin(115200);\n    WiFi.begin(WIFI_SSID, WIFI_PASS);\n    while (WiFi.status() != WL_CONNECTED) {\n        delay(500);\n        Serial.print(".");\n    }\n    Serial.println("\\nWiFi connected: " + WiFi.localIP().toString());\n}\n\nvoid loop() {\n    // IoT logic\n    delay(1000);\n}\n',
    }
    (src_dir / "main.cpp").write_text(templates.get(req.template, templates["blank"]))

    return {"project": req.name, "path": str(project_dir), "board": req.board, "template": req.template}


@router.get("/files/{project_name}")
async def list_files(project_name: str):
    """List all files in a project."""
    project_dir = PROJECTS_DIR / project_name
    if not project_dir.exists():
        raise HTTPException(404, "Project not found")

    def walk_dir(base: Path, rel: str = "") -> list:
        items = []
        for entry in sorted(base.iterdir()):
            rel_path = f"{rel}/{entry.name}" if rel else entry.name
            if entry.is_dir():
                items.append({
                    "name": entry.name, "path": rel_path, "type": "directory",
                    "children": walk_dir(entry, rel_path),
                })
            else:
                items.append({
                    "name": entry.name, "path": rel_path, "type": "file",
                    "size": entry.stat().st_size,
                    "extension": entry.suffix,
                })
        return items

    return {"project": project_name, "tree": walk_dir(project_dir)}


@router.get("/files/{project_name}/read")
async def read_file(project_name: str, path: str):
    """Read a file's contents."""
    file_path = PROJECTS_DIR / project_name / path
    if not file_path.exists():
        raise HTTPException(404, "File not found")
    if not file_path.is_file():
        raise HTTPException(400, "Path is not a file")

    try:
        content = file_path.read_text(encoding="utf-8")
        return {"path": path, "content": content, "size": len(content)}
    except UnicodeDecodeError:
        return {"path": path, "content": "[Binary file]", "size": file_path.stat().st_size, "binary": True}


@router.post("/files/{project_name}/write")
async def write_file(project_name: str, req: FileWriteRequest):
    """Write content to a file (create if not exists)."""
    file_path = PROJECTS_DIR / project_name / req.path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(req.content, encoding="utf-8")
    return {"path": req.path, "size": len(req.content), "status": "saved"}


@router.delete("/files/{project_name}/delete")
async def delete_file(project_name: str, path: str):
    """Delete a file."""
    file_path = PROJECTS_DIR / project_name / path
    if not file_path.exists():
        raise HTTPException(404, "File not found")
    if file_path.is_dir():
        import shutil
        shutil.rmtree(file_path)
    else:
        file_path.unlink()
    return {"deleted": path}
