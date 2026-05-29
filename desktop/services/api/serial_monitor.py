"""
Real-Time Serial Monitor — WebSocket-based live serial output viewer.

Connects to a serial port and streams data to connected WebSocket clients.
Also provides a mock mode for testing without hardware.
"""

import asyncio
import json
import math
import random
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

# Active connections
_ws_clients: list[WebSocket] = []
_monitor_task: Optional[asyncio.Task] = None
_monitor_active = False


class MonitorConfig(BaseModel):
    port: str = "mock"
    baud_rate: int = 115200
    mock: bool = True


@router.websocket("/ws")
async def serial_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time serial data streaming."""
    await websocket.accept()
    _ws_clients.append(websocket)
    print(f"[serial-monitor] Client connected ({len(_ws_clients)} total)")

    try:
        while True:
            # Keep connection alive, accept commands
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                cmd = msg.get("command", "")

                if cmd == "start":
                    config = MonitorConfig(**msg.get("config", {}))
                    await _start_monitor(config)
                    await websocket.send_json({"type": "status", "message": "Monitor started"})

                elif cmd == "stop":
                    await _stop_monitor()
                    await websocket.send_json({"type": "status", "message": "Monitor stopped"})

                elif cmd == "send":
                    # Send data to serial port
                    line = msg.get("data", "")
                    await _broadcast({"type": "tx", "data": line, "timestamp": _now()})

            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        _ws_clients.remove(websocket)
        print(f"[serial-monitor] Client disconnected ({len(_ws_clients)} remaining)")


@router.post("/start")
async def start_monitor(config: MonitorConfig):
    """Start the serial monitor (HTTP fallback for non-WebSocket clients)."""
    await _start_monitor(config)
    return {"status": "started", "port": config.port, "baud_rate": config.baud_rate}


@router.post("/stop")
async def stop_monitor():
    """Stop the serial monitor."""
    await _stop_monitor()
    return {"status": "stopped"}


@router.get("/status")
async def monitor_status():
    """Get current monitor status."""
    return {
        "active": _monitor_active,
        "clients": len(_ws_clients),
    }


# ─── Internal ────────────────────────────────────────────────

async def _start_monitor(config: MonitorConfig):
    """Start monitoring serial output."""
    global _monitor_task, _monitor_active
    await _stop_monitor()

    _monitor_active = True
    if config.mock:
        _monitor_task = asyncio.create_task(_mock_serial_loop())
    else:
        _monitor_task = asyncio.create_task(_real_serial_loop(config.port, config.baud_rate))


async def _stop_monitor():
    """Stop the serial monitor."""
    global _monitor_task, _monitor_active
    _monitor_active = False
    if _monitor_task:
        _monitor_task.cancel()
        try:
            await _monitor_task
        except asyncio.CancelledError:
            pass
        _monitor_task = None


async def _broadcast(message: dict):
    """Send a message to all connected WebSocket clients."""
    dead = []
    for ws in _ws_clients:
        try:
            await ws.send_json(message)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _ws_clients.remove(ws)


async def _mock_serial_loop():
    """Generate realistic mock serial output simulating an ESP32 device."""
    t = 0
    # Boot sequence
    boot_lines = [
        "ets Jun  8 2016 00:22:57",
        "rst:0x1 (POWERON_RESET),boot:0x13 (SPI_FAST_FLASH_BOOT)",
        "configsip: 0, SPIWP:0xee",
        "mode:DIO, clock div:1",
        "load:0x3fff0030,len:1184",
        "entry 0x400805f0",
        "",
        "[system] Parakram AI FreeRTOS starting...",
        "[bme280] Initialized with x16 oversampling",
        "[i2s-mic] INMP441 ready @ 16kHz",
        "[wifi] Connecting to MyNetwork...",
        "[wifi] Connected! IP: 192.168.1.42",
        "[ntp] Time synchronized",
        "[mqtt] Connected to broker",
        "[ota] OTA ready",
        "[system] All tasks created",
        "",
    ]

    for line in boot_lines:
        if not _monitor_active:
            return
        await _broadcast({
            "type": "rx",
            "data": line,
            "timestamp": _now(),
            "level": "info" if "[" in line else "system",
        })
        await asyncio.sleep(0.15)

    # Runtime loop
    while _monitor_active:
        t += 1
        temp = 27.5 + 7.5 * math.sin(t * 0.05) + random.gauss(0, 0.2)
        hum = 55 + 15 * math.sin(t * 0.03) + random.gauss(0, 0.5)
        press = 1013.25 + 5 * math.sin(t * 0.01)

        lines = [
            f"[bme280] T={temp:.1f}°C H={hum:.1f}% P={press:.1f}hPa",
        ]

        if t % 5 == 0:
            lines.append(f"[mqtt] Published to home/sensors (T={temp:.1f})")

        if t % 10 == 0:
            free_heap = 180000 + random.randint(-5000, 5000)
            stack_water = 2800 + random.randint(-200, 200)
            lines.append(f"[system] Heap: {free_heap}B | Stack watermark: {stack_water}B")

        if temp > 32.0:
            lines.append(f"[threshold] Temperature {temp:.1f}°C > 30.0°C — TRIGGERED")
            lines.append("[relay] Output ON")

        if t % 30 == 0:
            lines.append("[ota] Checking for updates...")
            lines.append("[ota] No update available")

        for line in lines:
            level = "warning" if "TRIGGERED" in line else "info"
            if "error" in line.lower() or "FAILED" in line:
                level = "error"
            await _broadcast({
                "type": "rx",
                "data": line,
                "timestamp": _now(),
                "level": level,
            })

        await asyncio.sleep(1.0)


async def _real_serial_loop(port: str, baud_rate: int):
    """Read from a real serial port and stream."""
    try:
        import serial
        ser = serial.Serial(port, baud_rate, timeout=0.1)
        while _monitor_active:
            if ser.in_waiting:
                line = ser.readline().decode("utf-8", errors="replace").strip()
                if line:
                    level = "info"
                    if "error" in line.lower() or "FAILED" in line:
                        level = "error"
                    elif "WARNING" in line or "warn" in line.lower():
                        level = "warning"
                    await _broadcast({
                        "type": "rx",
                        "data": line,
                        "timestamp": _now(),
                        "level": level,
                    })
            await asyncio.sleep(0.01)
        ser.close()
    except ImportError:
        await _broadcast({"type": "error", "data": "pyserial not installed", "timestamp": _now()})
    except Exception as e:
        await _broadcast({"type": "error", "data": str(e), "timestamp": _now()})


def _now() -> str:
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]
