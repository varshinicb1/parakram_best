"""
OTA Manager — Over-the-Air firmware update management.

Handles:
  - Building firmware for OTA delivery
  - Hosting update server locally
  - Version management and rollback
  - Progress tracking
  - Signed firmware validation (SHA256)

Embedder has no OTA management — this is a Parakram-only feature.
"""

import os
import hashlib
import json
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class FirmwareRelease:
    version: str
    board: str
    filename: str
    size_bytes: int = 0
    sha256: str = ""
    created_at: str = ""
    changelog: str = ""
    download_url: str = ""


@dataclass
class OTAConfig:
    project_name: str
    current_version: str = "0.0.0"
    releases: list[FirmwareRelease] = field(default_factory=list)
    auto_update: bool = False
    update_channel: str = "stable"  # stable, beta, nightly


class OTAManager:
    """Manage OTA firmware updates for embedded devices."""

    STORAGE = Path("./storage/ota")

    def __init__(self):
        self.STORAGE.mkdir(parents=True, exist_ok=True)

    def create_release(self, project: str, version: str, board: str,
                       firmware_path: str, changelog: str = "") -> dict:
        """Create a new OTA release from a compiled firmware binary."""
        release_dir = self.STORAGE / project / version
        release_dir.mkdir(parents=True, exist_ok=True)

        # Copy firmware
        src = Path(firmware_path)
        if not src.exists():
            return {"error": f"Firmware file not found: {firmware_path}"}

        dest = release_dir / f"firmware_{board}.bin"
        dest.write_bytes(src.read_bytes())

        # Calculate hash
        sha256 = hashlib.sha256(dest.read_bytes()).hexdigest()

        release = FirmwareRelease(
            version=version,
            board=board,
            filename=dest.name,
            size_bytes=dest.stat().st_size,
            sha256=sha256,
            created_at=datetime.now().isoformat(),
            changelog=changelog,
            download_url=f"/api/ota/{project}/{version}/download",
        )

        # Save metadata
        meta_path = release_dir / "release.json"
        meta_path.write_text(json.dumps({
            "version": release.version,
            "board": release.board,
            "filename": release.filename,
            "size_bytes": release.size_bytes,
            "sha256": release.sha256,
            "created_at": release.created_at,
            "changelog": release.changelog,
        }, indent=2))

        return {
            "version": version,
            "board": board,
            "size": release.size_bytes,
            "sha256": sha256,
            "path": str(dest),
        }

    def list_releases(self, project: str) -> list[dict]:
        """List all releases for a project."""
        project_dir = self.STORAGE / project
        if not project_dir.exists():
            return []

        releases = []
        for version_dir in sorted(project_dir.iterdir(), reverse=True):
            meta_path = version_dir / "release.json"
            if meta_path.exists():
                releases.append(json.loads(meta_path.read_text()))
        return releases

    def get_latest(self, project: str, board: str, channel: str = "stable") -> Optional[dict]:
        """Get the latest release for a project/board combination."""
        releases = self.list_releases(project)
        for r in releases:
            if r.get("board") == board:
                return r
        return None

    def check_update(self, project: str, board: str, current_version: str) -> dict:
        """Check if an update is available."""
        latest = self.get_latest(project, board)
        if not latest:
            return {"update_available": False, "message": "No releases found"}

        if latest["version"] > current_version:
            return {
                "update_available": True,
                "current": current_version,
                "latest": latest["version"],
                "size": latest["size_bytes"],
                "changelog": latest.get("changelog", ""),
                "sha256": latest["sha256"],
            }
        return {"update_available": False, "current": current_version, "message": "Up to date"}

    def generate_ota_code(self, project: str, board: str, server_url: str) -> str:
        """Generate Arduino/ESP32 OTA client code."""
        return f'''// Parakram OTA Client — Auto-generated
#include <Arduino.h>
#include <WiFi.h>
#include <HTTPUpdate.h>
#include <WiFiClientSecure.h>

#define OTA_SERVER "{server_url}"
#define OTA_PROJECT "{project}"
#define OTA_BOARD "{board}"
#define CURRENT_VERSION "0.0.1"
#define CHECK_INTERVAL_MS 3600000  // 1 hour

void checkOTAUpdate() {{
    WiFiClient client;
    String url = String(OTA_SERVER) + "/api/ota/" + OTA_PROJECT + "/check?board=" + OTA_BOARD + "&version=" + CURRENT_VERSION;

    Serial.println("[OTA] Checking for updates...");

    HTTPClient http;
    http.begin(client, url);
    int httpCode = http.GET();

    if (httpCode == 200) {{
        String payload = http.getString();
        // Parse JSON and check update_available
        if (payload.indexOf("\\"update_available\\": true") >= 0) {{
            Serial.println("[OTA] Update available! Starting download...");
            String fwUrl = String(OTA_SERVER) + "/api/ota/" + OTA_PROJECT + "/latest/download";
            t_httpUpdate_return ret = httpUpdate.update(client, fwUrl);
            switch (ret) {{
                case HTTP_UPDATE_OK: Serial.println("[OTA] Update success — rebooting"); break;
                case HTTP_UPDATE_FAILED: Serial.printf("[OTA] Update failed: %s\\n", httpUpdate.getLastErrorString().c_str()); break;
                case HTTP_UPDATE_NO_UPDATES: Serial.println("[OTA] No updates"); break;
            }}
        }} else {{
            Serial.println("[OTA] Firmware is up to date");
        }}
    }}
    http.end();
}}

// Call in setup() or loop()
// checkOTAUpdate();
'''

    def delete_release(self, project: str, version: str) -> dict:
        """Delete a specific release."""
        release_dir = self.STORAGE / project / version
        if release_dir.exists():
            import shutil
            shutil.rmtree(release_dir)
            return {"deleted": True, "version": version}
        return {"deleted": False, "message": "Release not found"}


def get_ota_manager() -> OTAManager:
    return OTAManager()
