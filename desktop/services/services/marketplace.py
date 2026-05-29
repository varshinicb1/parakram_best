"""
Community Extension Marketplace — Backend for sharing and discovering extensions.

Features:
  - Browse community-submitted extensions
  - Rating and review system
  - Download count tracking
  - Category and tag filtering
  - Featured extensions
  - Extension submission (with validation)
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional

MARKETPLACE_DIR = Path("./storage/marketplace")
MARKETPLACE_DIR.mkdir(parents=True, exist_ok=True)


# Built-in community extensions
COMMUNITY_EXTENSIONS = [
    {
        "id": "parakram-mqtt",
        "name": "MQTT Client Generator",
        "description": "Auto-generates MQTT client code for any broker with TLS support, topic management, and reconnect logic",
        "author": "Vidyutlabs",
        "version": "1.2.0",
        "category": "connectivity",
        "tags": ["mqtt", "iot", "cloud", "pub-sub"],
        "downloads": 1847,
        "rating": 4.8,
        "reviews": 23,
        "featured": True,
        "boards": ["esp32dev", "esp32-s3-devkitc-1", "rpipicow"],
    },
    {
        "id": "parakram-blynk",
        "name": "Blynk IoT Integration",
        "description": "Generate Blynk IoT app code with virtual pins, widgets, and OTA support",
        "author": "Vidyutlabs",
        "version": "2.0.1",
        "category": "connectivity",
        "tags": ["blynk", "iot", "app", "dashboard"],
        "downloads": 1234,
        "rating": 4.6,
        "reviews": 18,
        "featured": True,
        "boards": ["esp32dev", "esp32-s3-devkitc-1"],
    },
    {
        "id": "parakram-pid",
        "name": "PID Controller Library",
        "description": "Auto-tuned PID controller with anti-windup, derivative filter, and output limiting",
        "author": "community",
        "version": "1.0.3",
        "category": "control",
        "tags": ["pid", "control", "motor", "temperature"],
        "downloads": 892,
        "rating": 4.9,
        "reviews": 14,
        "featured": False,
        "boards": ["esp32dev", "nucleo_f446re", "teensy40"],
    },
    {
        "id": "parakram-display",
        "name": "Display Driver Pack",
        "description": "Drivers for 20+ display types: OLED, TFT, E-Paper, LED matrix with graphics primitives",
        "author": "Vidyutlabs",
        "version": "3.1.0",
        "category": "display",
        "tags": ["oled", "tft", "e-paper", "graphics"],
        "downloads": 2341,
        "rating": 4.7,
        "reviews": 31,
        "featured": True,
        "boards": ["esp32dev", "esp32-s3-devkitc-1", "pico", "uno"],
    },
    {
        "id": "parakram-modbus",
        "name": "Modbus RTU/TCP",
        "description": "Industrial Modbus client/server with auto-register mapping and HMI integration",
        "author": "community",
        "version": "1.1.0",
        "category": "industrial",
        "tags": ["modbus", "industrial", "plc", "scada"],
        "downloads": 567,
        "rating": 4.5,
        "reviews": 8,
        "featured": False,
        "boards": ["esp32dev", "nucleo_f446re", "nucleo_h743zi"],
    },
    {
        "id": "parakram-kalman",
        "name": "Kalman Filter Suite",
        "description": "1D, 2D, and extended Kalman filters for sensor fusion with automatic noise estimation",
        "author": "community",
        "version": "2.0.0",
        "category": "signal",
        "tags": ["kalman", "filter", "imu", "sensor-fusion"],
        "downloads": 1123,
        "rating": 4.8,
        "reviews": 16,
        "featured": True,
        "boards": ["esp32dev", "nucleo_f446re", "teensy40", "pico"],
    },
    {
        "id": "parakram-aws-iot",
        "name": "AWS IoT Core Connector",
        "description": "Secure MQTT connection to AWS IoT Core with certificate management and shadow sync",
        "author": "community",
        "version": "1.3.0",
        "category": "cloud",
        "tags": ["aws", "iot", "cloud", "mqtt", "shadow"],
        "downloads": 789,
        "rating": 4.4,
        "reviews": 11,
        "featured": False,
        "boards": ["esp32dev", "esp32-s3-devkitc-1"],
    },
    {
        "id": "parakram-motor",
        "name": "Motor Control Suite",
        "description": "DC motor, stepper, and servo control with acceleration profiles and position feedback",
        "author": "Vidyutlabs",
        "version": "2.1.0",
        "category": "actuator",
        "tags": ["motor", "stepper", "servo", "pwm"],
        "downloads": 1567,
        "rating": 4.7,
        "reviews": 22,
        "featured": True,
        "boards": ["esp32dev", "nucleo_f446re", "pico", "uno", "teensy40"],
    },
    {
        "id": "parakram-fota",
        "name": "FOTA (Firmware Over The Air)",
        "description": "Encrypted firmware OTA with rollback, delta updates, and A/B partition support",
        "author": "Vidyutlabs",
        "version": "1.5.0",
        "category": "system",
        "tags": ["ota", "update", "firmware", "security"],
        "downloads": 2100,
        "rating": 4.9,
        "reviews": 28,
        "featured": True,
        "boards": ["esp32dev", "esp32-s3-devkitc-1"],
    },
    {
        "id": "parakram-power-mgmt",
        "name": "Smart Power Management",
        "description": "Deep sleep scheduling, wake-on-event, battery monitoring, and solar charge controller",
        "author": "community",
        "version": "1.0.1",
        "category": "power",
        "tags": ["power", "sleep", "battery", "solar"],
        "downloads": 934,
        "rating": 4.6,
        "reviews": 12,
        "featured": False,
        "boards": ["esp32dev", "esp32-c3-devkitm-1", "nrf52840_dk"],
    },
]


def get_marketplace_extensions(category: str = "", tag: str = "", featured_only: bool = False) -> list[dict]:
    """Get marketplace extensions with optional filters."""
    results = COMMUNITY_EXTENSIONS
    if category:
        results = [e for e in results if e["category"] == category.lower()]
    if tag:
        results = [e for e in results if tag.lower() in [t.lower() for t in e["tags"]]]
    if featured_only:
        results = [e for e in results if e.get("featured")]
    return sorted(results, key=lambda e: e["downloads"], reverse=True)


def get_categories() -> list[dict]:
    """Get all extension categories with counts."""
    cats: dict[str, int] = {}
    for ext in COMMUNITY_EXTENSIONS:
        c = ext["category"]
        cats[c] = cats.get(c, 0) + 1
    return [{"name": k, "count": v} for k, v in sorted(cats.items())]


def submit_extension(data: dict) -> dict:
    """Submit a new extension to the marketplace."""
    ext_id = data.get("id", "")
    if not ext_id:
        return {"error": "Extension ID required"}
    out = MARKETPLACE_DIR / f"{ext_id}.json"
    data["submitted_at"] = datetime.now().isoformat()
    data["status"] = "pending_review"
    data["downloads"] = 0
    data["rating"] = 0
    out.write_text(json.dumps(data, indent=2))
    return {"status": "submitted", "id": ext_id}
