"""
Project Gallery — Showcase and share firmware projects.

Features:
  - Project templates with thumbnails
  - Community project sharing
  - One-click import into workspace
  - Star/like system
  - Tags and categories
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional

GALLERY_STORAGE = Path("./storage/gallery")
GALLERY_STORAGE.mkdir(parents=True, exist_ok=True)


# Built-in project templates
BUILT_IN_TEMPLATES = [
    {
        "id": "weather-station",
        "title": "IoT Weather Station",
        "description": "ESP32 + BME280 + OLED with MQTT data publishing and web dashboard",
        "board": "esp32dev",
        "tags": ["iot", "sensor", "mqtt", "weather"],
        "difficulty": "beginner",
        "peripherals": ["BME280", "SSD1306 OLED", "WiFi"],
        "estimated_cost": 15.0,
        "stars": 245,
        "author": "Vidyutlabs",
    },
    {
        "id": "smart-garden",
        "title": "Smart Garden Monitor",
        "description": "Soil moisture, temperature, light sensors with automated watering relay",
        "board": "esp32dev",
        "tags": ["iot", "agriculture", "automation"],
        "difficulty": "beginner",
        "peripherals": ["Soil Moisture", "DHT22", "LDR", "Relay"],
        "estimated_cost": 18.0,
        "stars": 189,
        "author": "Vidyutlabs",
    },
    {
        "id": "drone-controller",
        "title": "Drone Flight Controller",
        "description": "STM32F4 + MPU6050 IMU + PID control + ESC PWM output with telemetry",
        "board": "nucleo_f446re",
        "tags": ["drone", "pid", "imu", "advanced"],
        "difficulty": "expert",
        "peripherals": ["MPU6050", "ESC", "PWM", "UART Telemetry"],
        "estimated_cost": 45.0,
        "stars": 312,
        "author": "Vidyutlabs",
    },
    {
        "id": "home-security",
        "title": "Home Security System",
        "description": "PIR motion detection, RFID access, camera trigger, Telegram alerts",
        "board": "esp32-s3-devkitc-1",
        "tags": ["security", "camera", "rfid", "iot"],
        "difficulty": "medium",
        "peripherals": ["PIR", "RFID", "Camera", "Buzzer", "WiFi"],
        "estimated_cost": 35.0,
        "stars": 156,
        "author": "Vidyutlabs",
    },
    {
        "id": "robot-arm",
        "title": "6-DOF Robot Arm Controller",
        "description": "RP2040 + 6 servos with inverse kinematics and serial command interface",
        "board": "pico",
        "tags": ["robotics", "servo", "kinematics"],
        "difficulty": "advanced",
        "peripherals": ["6x Servo", "UART", "OLED Display"],
        "estimated_cost": 50.0,
        "stars": 98,
        "author": "Vidyutlabs",
    },
    {
        "id": "can-bus-logger",
        "title": "OBD-II CAN Bus Logger",
        "description": "ESP32 + MCP2515 CAN interface for automotive diagnostics with SD logging",
        "board": "esp32dev",
        "tags": ["automotive", "can-bus", "diagnostics"],
        "difficulty": "advanced",
        "peripherals": ["MCP2515 CAN", "SD Card", "OLED"],
        "estimated_cost": 25.0,
        "stars": 203,
        "author": "Vidyutlabs",
    },
    {
        "id": "ble-fitness-tracker",
        "title": "BLE Fitness Tracker",
        "description": "nRF52840 + MPU6050 + heart rate sensor with BLE data streaming to phone",
        "board": "nrf52840_dk",
        "tags": ["ble", "wearable", "fitness", "low-power"],
        "difficulty": "advanced",
        "peripherals": ["MPU6050", "MAX30102 HR", "SSD1306 OLED", "BLE"],
        "estimated_cost": 40.0,
        "stars": 134,
        "author": "Vidyutlabs",
    },
    {
        "id": "lora-sensor-node",
        "title": "LoRa Sensor Node",
        "description": "Ultra low-power LoRa sensor node with deep sleep, solar charging, and TTN",
        "board": "esp32dev",
        "tags": ["lora", "iot", "low-power", "solar"],
        "difficulty": "medium",
        "peripherals": ["SX1276 LoRa", "BME280", "Solar", "Deep Sleep"],
        "estimated_cost": 22.0,
        "stars": 178,
        "author": "Vidyutlabs",
    },
    {
        "id": "led-matrix-display",
        "title": "LED Matrix Message Board",
        "description": "ESP32 + WS2812B matrix with web interface for custom messages and animations",
        "board": "esp32dev",
        "tags": ["display", "neopixel", "web", "animation"],
        "difficulty": "beginner",
        "peripherals": ["WS2812B Matrix", "WiFi", "Web Server"],
        "estimated_cost": 20.0,
        "stars": 267,
        "author": "Vidyutlabs",
    },
    {
        "id": "rtos-sensor-hub",
        "title": "FreeRTOS Multi-Sensor Hub",
        "description": "ESP32 FreeRTOS with 5 sensor tasks, queue-based communication, and web dashboard",
        "board": "esp32dev",
        "tags": ["freertos", "iot", "multi-task"],
        "difficulty": "advanced",
        "peripherals": ["BME280", "MPU6050", "VL53L0X", "ADS1115", "OLED"],
        "estimated_cost": 30.0,
        "stars": 145,
        "author": "Vidyutlabs",
    },
]


def get_gallery_templates() -> list[dict]:
    return BUILT_IN_TEMPLATES


def search_gallery(query: str = "", tag: str = "", difficulty: str = "") -> list[dict]:
    results = BUILT_IN_TEMPLATES
    if query:
        q = query.lower()
        results = [t for t in results if q in t["title"].lower() or q in t["description"].lower()]
    if tag:
        results = [t for t in results if tag.lower() in [t.lower() for t in t["tags"]]]
    if difficulty:
        results = [t for t in results if t["difficulty"] == difficulty.lower()]
    return results


def save_community_project(project_data: dict) -> str:
    out = GALLERY_STORAGE / f"{project_data.get('id', 'unnamed')}.json"
    project_data["submitted_at"] = datetime.now().isoformat()
    out.write_text(json.dumps(project_data, indent=2))
    return str(out)
