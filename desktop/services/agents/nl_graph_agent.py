"""
NL → Block Graph Agent — Natural language to firmware pipeline.

Takes a user prompt like "build me a weather station with MQTT"
and generates a complete Parakram block graph with nodes, edges,
pin assignments, and configuration.
"""

import os
import json
import re
from typing import Optional

# ── Component Knowledge Base ─────────────────────────
# Maps common concepts to Parakram block IDs
CONCEPT_TO_BLOCKS = {
    # Environmental
    "temperature": ["bme280", "dht22", "sht31"],
    "humidity": ["bme280", "dht22", "sht31"],
    "pressure": ["bme280"],
    "weather": ["bme280", "wifi_station", "mqtt_client"],
    "weather station": ["bme280", "wifi_station", "mqtt_client", "i2c_oled"],
    "climate": ["bme280", "sht31"],

    # Motion / Position
    "motion": ["pir_sensor", "mpu6050"],
    "acceleration": ["mpu6050"],
    "gyroscope": ["mpu6050"],
    "imu": ["mpu6050"],
    "gps": ["gps_neo6m"],
    "location": ["gps_neo6m", "wifi_station"],
    "distance": ["ultrasonic_hcsr04", "vl53l0x"],

    # Light / Vision
    "light": ["bh1750", "led_output"],
    "spectral": ["as7341"],
    "thermal camera": ["mlx90640"],
    "thermal": ["mlx90640"],
    "led": ["led_output", "neopixel_strip"],
    "neopixel": ["neopixel_strip"],
    "rgb": ["neopixel_strip"],

    # Weight / Force
    "weight": ["hx711"],
    "load cell": ["hx711"],
    "scale": ["hx711"],

    # Soil / Agriculture
    "soil": ["soil_moisture"],
    "moisture": ["soil_moisture"],
    "plant": ["soil_moisture", "dht22", "relay_module"],
    "garden": ["soil_moisture", "dht22", "relay_module", "wifi_station"],
    "irrigation": ["soil_moisture", "relay_module"],

    # Communication
    "wifi": ["wifi_station"],
    "mqtt": ["mqtt_client", "wifi_station"],
    "bluetooth": ["ble_server"],
    "ble": ["ble_server"],
    "lora": ["lora_sx1276"],
    "espnow": ["esp_now_peer"],
    "esp-now": ["esp_now_peer"],
    "http": ["http_client", "wifi_station"],
    "websocket": ["websocket_client", "wifi_station"],
    "api": ["http_client", "wifi_station"],
    "can": ["can_bus"],
    "can bus": ["can_bus"],

    # Actuators
    "servo": ["servo_motor"],
    "motor": ["dc_motor_l298n"],
    "stepper": ["stepper_a4988"],
    "relay": ["relay_module"],
    "pump": ["relay_module"],
    "fan": ["relay_module"],
    "valve": ["relay_module"],

    # Display
    "display": ["i2c_oled"],
    "oled": ["i2c_oled"],
    "screen": ["i2c_oled"],
    "tft": ["spi_display"],
    "lcd": ["i2c_oled"],
    "e-paper": ["e_paper"],
    "epaper": ["e_paper"],
    "matrix": ["led_matrix_max7219"],

    # Audio
    "microphone": ["i2s_microphone"],
    "speaker": ["i2s_speaker"],
    "audio": ["i2s_microphone", "i2s_speaker"],
    "sound": ["i2s_microphone"],

    # Security
    "rfid": ["rfid_rc522"],
    "nfc": ["rfid_rc522"],
    "fingerprint": ["fingerprint_r307"],
    "access control": ["rfid_rc522", "relay_module"],
    "door lock": ["rfid_rc522", "relay_module", "servo_motor"],
    "security": ["rfid_rc522", "pir_sensor"],

    # Power
    "battery": ["battery_monitor"],
    "sleep": ["deep_sleep"],
    "ota": ["ota_updater", "wifi_station"],
    "low power": ["deep_sleep", "battery_monitor"],

    # Storage
    "log": ["sd_card"],
    "sd card": ["sd_card"],
    "store": ["nvs_preferences"],
    "save": ["nvs_preferences"],
    "eeprom": ["eeprom_store"],

    # Application patterns
    "robot": ["dc_motor_l298n", "mpu6050", "ultrasonic_hcsr04", "ble_server"],
    "drone": ["mpu6050", "dc_motor_l298n", "gps_neo6m", "ble_server"],
    "smart home": ["wifi_station", "mqtt_client", "relay_module", "dht22", "pir_sensor"],
    "iot": ["wifi_station", "mqtt_client", "dht22"],
    "data logger": ["bme280", "sd_card", "deep_sleep", "battery_monitor"],
    "wearable": ["mpu6050", "max30102", "ble_server", "i2c_oled"],
    "health monitor": ["max30102", "mpu6050", "ble_server", "i2c_oled"],
    "tracker": ["gps_neo6m", "lora_sx1276", "battery_monitor", "deep_sleep"],
    "industrial": ["can_bus", "ads1115", "ina219", "relay_module", "sd_card"],
}

# Default I2C pin assignments per address to avoid conflicts
I2C_ADDRESSES = {
    "bme280": "0x76", "sht31": "0x44", "mpu6050": "0x68",
    "bh1750": "0x23", "ads1115": "0x48", "ina219": "0x40",
    "vl53l0x": "0x29", "i2c_oled": "0x3C", "as7341": "0x39",
    "mlx90640": "0x33", "max30102": "0x57",
}


class NLGraphAgent:
    """Converts natural language prompts into Parakram block graphs."""

    def __init__(self):
        self._hw_blocks = self._load_hw_library()

    def _load_hw_library(self) -> dict:
        """Load all available hardware blocks."""
        hw_dir = os.path.join(os.path.dirname(__file__), "..", "hardware_library")
        blocks = {}
        if not os.path.isdir(hw_dir):
            return blocks
        for cat_dir in os.listdir(hw_dir):
            cat_path = os.path.join(hw_dir, cat_dir)
            if not os.path.isdir(cat_path) or cat_dir.startswith(("_", ".")):
                continue
            for fname in os.listdir(cat_path):
                if not fname.endswith(".json"):
                    continue
                try:
                    with open(os.path.join(cat_path, fname), "r", encoding="utf-8") as f:
                        block = json.load(f)
                    block_id = block.get("id", fname.replace(".json", ""))
                    block["_category"] = cat_dir
                    blocks[block_id] = block
                except Exception:
                    pass
        return blocks

    def extract_blocks(self, prompt: str) -> list[str]:
        """Extract required block IDs from a natural language prompt."""
        prompt_lower = prompt.lower()
        needed = set()

        # Match concepts (longer phrases first for better matching)
        sorted_concepts = sorted(CONCEPT_TO_BLOCKS.keys(), key=len, reverse=True)
        for concept in sorted_concepts:
            if concept in prompt_lower:
                for block_id in CONCEPT_TO_BLOCKS[concept]:
                    needed.add(block_id)

        # Always include ESP32 manifest if any blocks need it
        if needed:
            needed.add("esp32_manifest")

        # WiFi dependency: MQTT/HTTP/WebSocket/OTA need WiFi
        wifi_deps = {"mqtt_client", "http_client", "websocket_client", "ota_updater"}
        if needed & wifi_deps:
            needed.add("wifi_station")

        return sorted(needed)

    def build_graph(self, prompt: str) -> dict:
        """
        Build a complete block graph from a natural language prompt.

        Returns:
        {
            "nodes": [{"id": ..., "block_id": ..., "position": ..., "config": ...}],
            "edges": [{"source": ..., "target": ..., "label": ...}],
            "board": "esp32dev",
            "description": str,
        }
        """
        block_ids = self.extract_blocks(prompt)

        nodes = []
        edges = []
        x, y = 100, 100
        esp_node = None

        for i, block_id in enumerate(block_ids):
            block = self._hw_blocks.get(block_id, {})
            node_id = f"node_{i}"
            category = block.get("_category", block.get("category", ""))

            node = {
                "id": node_id,
                "block_id": block_id,
                "name": block.get("name", block_id),
                "category": category,
                "position": {"x": x, "y": y},
                "config": {},
            }

            # Add I2C address
            if block_id in I2C_ADDRESSES:
                node["config"]["i2c_address"] = I2C_ADDRESSES[block_id]

            # Track ESP node for edges
            if block_id == "esp32_manifest":
                esp_node = node_id

            nodes.append(node)

            # Grid layout
            x += 250
            if x > 900:
                x = 100
                y += 200

        # Create edges: ESP32 → all peripherals
        if esp_node:
            for node in nodes:
                if node["id"] != esp_node:
                    bus = "I2C" if node["block_id"] in I2C_ADDRESSES else "GPIO"
                    edges.append({
                        "source": esp_node,
                        "target": node["id"],
                        "label": bus,
                    })

        # Logical data flow edges (sensor → display, sensor → MQTT)
        sensor_nodes = [n for n in nodes if n["category"] in ("sensor", "sensors")]
        display_nodes = [n for n in nodes if n["category"] == "display"]
        mqtt_nodes = [n for n in nodes if n["block_id"] == "mqtt_client"]

        for sensor in sensor_nodes:
            for display in display_nodes:
                edges.append({
                    "source": sensor["id"],
                    "target": display["id"],
                    "label": "data",
                })
            for mqtt in mqtt_nodes:
                edges.append({
                    "source": sensor["id"],
                    "target": mqtt["id"],
                    "label": "publish",
                })

        return {
            "prompt": prompt,
            "nodes": nodes,
            "edges": edges,
            "board": "esp32dev",
            "block_count": len(nodes),
            "description": f"Auto-generated from: '{prompt}'",
        }

    async def generate_with_llm(self, prompt: str) -> dict:
        """
        Use LLM for complex/ambiguous prompts that concept matching can't handle.
        Falls back to concept matching if LLM fails.
        """
        # Try concept matching first
        blocks = self.extract_blocks(prompt)
        if len(blocks) >= 3:
            return self.build_graph(prompt)

        # Use LLM Router for complex reasoning
        llm_prompt = f"""Given this user request for an embedded system:
"{prompt}"

List the hardware components needed. For each, give:
- component name (e.g., BME280, DHT22, Servo, OLED)
- category (sensor, actuator, display, communication, storage, power)
- connection type (I2C, SPI, GPIO, UART)

Format: one component per line as "name|category|connection"
"""
        try:
            from agents.llm_provider import get_router
            router = get_router()
            text = await router.generate(llm_prompt, max_tokens=500, temperature=0.2)

            # Parse LLM response and map to blocks
            for line in text.strip().split("\n"):
                parts = line.strip().split("|")
                if len(parts) >= 2:
                    name = parts[0].strip().lower()
                    # Find matching block
                    for concept, block_ids in CONCEPT_TO_BLOCKS.items():
                        if name in concept or concept in name:
                            for bid in block_ids:
                                blocks.append(bid)
                            break

        except Exception as e:
            print(f"[nl_agent] LLM fallback: {e}")

        # Deduplicate
        blocks = sorted(set(blocks))
        if not blocks:
            blocks = self.extract_blocks(prompt)

        # Build graph from whatever we got
        return self.build_graph(prompt)
