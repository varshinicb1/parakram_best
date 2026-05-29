"""
WebSocket Manager — Real-time progress streaming for firmware pipeline.

Sends step-by-step progress updates to the frontend during:
  - Autonomous firmware generation
  - Compilation and self-healing
  - Datasheet parsing
  - OTA upload

Uses FastAPI WebSockets for low-latency, bidirectional communication.
"""

import asyncio
import json
from datetime import datetime
from typing import Optional
from fastapi import WebSocket, WebSocketDisconnect


class ConnectionManager:
    """Manage WebSocket connections for real-time updates."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.pipeline_status: dict = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """Send message to all connected clients."""
        dead = []
        for conn in self.active_connections:
            try:
                await conn.send_json(message)
            except Exception:
                dead.append(conn)
        for d in dead:
            self.disconnect(d)

    async def send_pipeline_update(self, step: str, status: str,
                                     progress: float, details: str = "",
                                     data: Optional[dict] = None):
        """Send a pipeline step update."""
        msg = {
            "type": "pipeline_update",
            "timestamp": datetime.now().isoformat(),
            "step": step,
            "status": status,  # pending, running, success, error
            "progress": progress,  # 0-100
            "details": details,
            "data": data or {},
        }
        self.pipeline_status[step] = msg
        await self.broadcast(msg)

    async def send_build_log(self, line: str, level: str = "info"):
        """Send a build log line."""
        await self.broadcast({
            "type": "build_log",
            "timestamp": datetime.now().isoformat(),
            "line": line,
            "level": level,  # info, warning, error, success
        })

    async def send_serial_data(self, data: str, port: str = ""):
        """Stream serial data in real-time."""
        await self.broadcast({
            "type": "serial_data",
            "timestamp": datetime.now().isoformat(),
            "data": data,
            "port": port,
        })

    async def send_notification(self, title: str, message: str,
                                  severity: str = "info"):
        """Send a UI notification."""
        await self.broadcast({
            "type": "notification",
            "timestamp": datetime.now().isoformat(),
            "title": title,
            "message": message,
            "severity": severity,  # info, success, warning, error
        })

    def get_pipeline_status(self) -> dict:
        """Get current pipeline state for reconnecting clients."""
        return self.pipeline_status


# Singleton
_manager: Optional[ConnectionManager] = None

def get_ws_manager() -> ConnectionManager:
    global _manager
    if _manager is None:
        _manager = ConnectionManager()
    return _manager
