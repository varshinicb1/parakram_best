"""
Wokwi Simulator Integration — run ESP32 simulations in the browser.

Generates Wokwi diagram.json from the canvas graph and provides
endpoints to launch simulations via wokwi-client.
"""

import os
import json
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

# ─── Wokwi Component Mapping ────────────────────────────────
# Maps Parakram block IDs to Wokwi component part IDs
WOKWI_PARTS = {
    # Sensors
    "dht22": {"type": "wokwi-dht22", "attrs": {}},
    "bme280": {"type": "wokwi-custom-chip", "attrs": {"chipName": "bme280"}},
    "bmp280": {"type": "wokwi-custom-chip", "attrs": {"chipName": "bmp280"}},
    "mpu6050": {"type": "wokwi-mpu6050", "attrs": {}},
    "bh1750": {"type": "wokwi-custom-chip", "attrs": {"chipName": "bh1750"}},
    "ads1115": {"type": "wokwi-custom-chip", "attrs": {"chipName": "ads1115"}},
    "vl53l0x": {"type": "wokwi-custom-chip", "attrs": {"chipName": "vl53l0x"}},
    "ina219": {"type": "wokwi-custom-chip", "attrs": {"chipName": "ina219"}},
    # Actuators
    "led_output": {"type": "wokwi-led", "attrs": {"color": "green"}},
    "servo_motor": {"type": "wokwi-servo", "attrs": {}},
    # Display
    "i2c_oled": {"type": "wokwi-ssd1306", "attrs": {}},
    "spi_display": {"type": "wokwi-ili9341", "attrs": {}},
    # Communication
    "wifi_station": None,  # Built into ESP32
    "mqtt_client": None,
    "websocket_client": None,
    "ble_server": None,
}


def generate_diagram(nodes: list[dict], edges: list[dict]) -> dict:
    """
    Generate a Wokwi diagram.json from Parakram canvas nodes/edges.

    Returns a valid Wokwi diagram with:
    - ESP32 DevKit as the main board
    - Mapped components from the block graph
    - Wire connections based on pin configurations
    """
    parts = []
    connections = []

    # Always add ESP32 board
    parts.append({
        "type": "board-esp32-devkit-c-v4",
        "id": "esp32",
        "top": 0,
        "left": 200,
        "attrs": {},
    })

    # Component placement grid
    x_offset = 0
    y_offset = -200
    col = 0

    for node in nodes:
        block_id = node.get("id", "").lower().replace(" ", "_").replace("-", "_")
        # Try to match by id, then by stripping common suffixes
        wokwi_part = WOKWI_PARTS.get(block_id)

        # Try matching by name
        if wokwi_part is None:
            name_key = node.get("name", "").lower().replace(" ", "_").replace("-", "_").replace("&", "")
            wokwi_part = WOKWI_PARTS.get(name_key)

        if wokwi_part is None or wokwi_part.get("type") is None:
            continue  # Skip blocks without Wokwi representation

        part_id = f"part_{block_id}"
        parts.append({
            "type": wokwi_part["type"],
            "id": part_id,
            "top": y_offset,
            "left": x_offset,
            "attrs": wokwi_part.get("attrs", {}),
        })

        # Auto-wire based on configuration
        config = node.get("configuration", {})
        if isinstance(config, list):
            config = {c.get("key", ""): c.get("default", "") for c in config}

        # Wire pin connections
        pin = config.get("pin") or config.get("data_pin")
        if pin:
            connections.append({
                "from": f"esp32:GPIO{pin}",
                "to": f"{part_id}:VCC",
                "color": "green",
            })

        # Wire I2C connections (SDA=21, SCL=22 by default)
        sda = config.get("sda_pin", "21")
        scl = config.get("scl_pin", "22")
        category = node.get("category", "")
        if category in ["sensor", "display"] and not pin:
            connections.append({"from": f"esp32:GPIO{sda}", "to": f"{part_id}:SDA", "color": "blue"})
            connections.append({"from": f"esp32:GPIO{scl}", "to": f"{part_id}:SCL", "color": "yellow"})

        # Grid layout
        col += 1
        x_offset += 250
        if col >= 3:
            col = 0
            x_offset = 0
            y_offset -= 250

    return {
        "version": 1,
        "author": "Parakram AI",
        "editor": "wokwi",
        "parts": parts,
        "connections": connections,
        "serialMonitor": {"display": "terminal"},
    }


# ─── API Routes ──────────────────────────────────────────────

class WokwiRequest(BaseModel):
    project_id: str
    nodes: list[dict] = []
    edges: list[dict] = []


@router.post("/diagram")
async def create_diagram(request: WokwiRequest):
    """Generate a Wokwi diagram.json from the canvas graph."""
    diagram = generate_diagram(request.nodes, request.edges)

    # Save to project
    projects_dir = os.environ.get("PROJECTS_DIR", "../projects")
    project_dir = os.path.join(projects_dir, request.project_id, "firmware")
    os.makedirs(project_dir, exist_ok=True)

    diagram_path = os.path.join(project_dir, "diagram.json")
    with open(diagram_path, "w") as f:
        json.dump(diagram, f, indent=2)

    # Also save wokwi.toml
    wokwi_toml = f"""[wokwi]
version = 1
firmware = ".pio/build/esp32dev/firmware.bin"
elf = ".pio/build/esp32dev/firmware.elf"
"""
    toml_path = os.path.join(project_dir, "wokwi.toml")
    with open(toml_path, "w") as f:
        f.write(wokwi_toml)

    return {
        "status": "success",
        "diagram": diagram,
        "parts_count": len(diagram["parts"]),
        "connections_count": len(diagram["connections"]),
        "files": [diagram_path, toml_path],
    }


@router.get("/parts")
async def list_supported_parts():
    """List all Wokwi-supported components."""
    supported = []
    for block_id, part in WOKWI_PARTS.items():
        if part and part.get("type"):
            supported.append({
                "block_id": block_id,
                "wokwi_type": part["type"],
            })
    return {"supported_parts": supported, "total": len(supported)}
