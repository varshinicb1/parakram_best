"""
Wokwi Simulator Integration — Deep API for loading firmware into simulation.

Generates Wokwi diagram.json from golden blocks, creates simulation configs,
and provides URLs for embedded simulation.
"""
import json
from typing import Optional


# Wokwi component part IDs for common hardware
WOKWI_PARTS = {
    # MCUs
    "esp32_manifest":     {"type": "wokwi-esp32-devkit-v1", "attrs": {}},
    "esp32s3_manifest":   {"type": "board-esp32-s3-devkitc-1", "attrs": {}},
    "esp32c3_manifest":   {"type": "board-esp32-c3-devkitm-1", "attrs": {}},
    # Sensors
    "bme280":             {"type": "wokwi-bme280", "attrs": {"temperature": "24.5", "humidity": "65"}},
    "dht22":              {"type": "wokwi-dht22", "attrs": {"temperature": "26", "humidity": "55"}},
    "ds18b20":            {"type": "wokwi-ds18b20", "attrs": {"temperature": "22"}},
    "hcsr04_ultrasonic":  {"type": "wokwi-hc-sr04", "attrs": {"distance": "100"}},
    "pir_sensor":         {"type": "wokwi-pir-motion-sensor", "attrs": {}},
    "potentiometer":      {"type": "wokwi-potentiometer", "attrs": {"value": "512"}},
    "photoresistor":      {"type": "wokwi-photoresistor-sensor", "attrs": {}},
    "slide_switch":       {"type": "wokwi-slide-switch", "attrs": {}},
    # Displays
    "ssd1306_oled":       {"type": "wokwi-ssd1306", "attrs": {}},
    "lcd_i2c_16x2":       {"type": "wokwi-lcd1602", "attrs": {"pins": "i2c"}},
    "lcd_20x4":           {"type": "wokwi-lcd2004", "attrs": {"pins": "i2c"}},
    "neopixel_strip":     {"type": "wokwi-neopixel", "attrs": {"pixels": "8"}},
    "seven_segment":      {"type": "wokwi-7segment", "attrs": {}},
    # Actuators
    "servo_sg90":         {"type": "wokwi-servo", "attrs": {}},
    "dc_motor_l298n":     {"type": "wokwi-l298n", "attrs": {}},
    "buzzer_passive":     {"type": "wokwi-buzzer", "attrs": {}},
    "relay_module":       {"type": "wokwi-relay-module", "attrs": {}},
    "led_rgb":            {"type": "wokwi-rgb-led", "attrs": {}},
    "led_single":         {"type": "wokwi-led", "attrs": {"color": "green"}},
    # Communication
    "push_button":        {"type": "wokwi-pushbutton", "attrs": {"color": "green"}},
    "resistor":           {"type": "wokwi-resistor", "attrs": {"resistance": "10000"}},
}

# Default wiring for common I2C/SPI/OneWire connections
WIRING_TEMPLATES = {
    "i2c": [
        {"from": "{part}:SDA", "to": "esp:21", "color": "blue"},
        {"from": "{part}:SCL", "to": "esp:22", "color": "purple"},
        {"from": "{part}:VCC", "to": "esp:3V3", "color": "red"},
        {"from": "{part}:GND", "to": "esp:GND.1", "color": "black"},
    ],
    "spi": [
        {"from": "{part}:SDI", "to": "esp:23", "color": "blue"},
        {"from": "{part}:SDO", "to": "esp:19", "color": "green"},
        {"from": "{part}:SCK", "to": "esp:18", "color": "yellow"},
        {"from": "{part}:CS",  "to": "esp:5",  "color": "orange"},
        {"from": "{part}:VCC", "to": "esp:3V3", "color": "red"},
        {"from": "{part}:GND", "to": "esp:GND.1", "color": "black"},
    ],
    "onewire": [
        {"from": "{part}:DQ",  "to": "esp:4",  "color": "green"},
        {"from": "{part}:VCC", "to": "esp:3V3", "color": "red"},
        {"from": "{part}:GND", "to": "esp:GND.1", "color": "black"},
    ],
    "analog": [
        {"from": "{part}:SIG", "to": "esp:36", "color": "green"},
        {"from": "{part}:VCC", "to": "esp:3V3", "color": "red"},
        {"from": "{part}:GND", "to": "esp:GND.1", "color": "black"},
    ],
    "digital": [
        {"from": "{part}:SIG", "to": "esp:25", "color": "green"},
        {"from": "{part}:VCC", "to": "esp:3V3", "color": "red"},
        {"from": "{part}:GND", "to": "esp:GND.1", "color": "black"},
    ],
    "servo": [
        {"from": "{part}:PWM", "to": "esp:13", "color": "orange"},
        {"from": "{part}:V+",  "to": "esp:3V3", "color": "red"},
        {"from": "{part}:GND", "to": "esp:GND.1", "color": "black"},
    ],
}


class WokwiSimulator:
    """Generates Wokwi simulation configurations from golden blocks."""

    def generate_diagram(
        self,
        block_ids: list[str],
        board: str = "esp32dev",
    ) -> dict:
        """Generate a complete Wokwi diagram.json from block IDs."""
        parts = []
        connections = []

        # Add MCU
        mcu_part = self._get_mcu_part(board)
        parts.append({
            "type": mcu_part,
            "id": "esp",
            "top": 0,
            "left": 0,
            "attrs": {},
        })

        # Add components
        x_offset = 300
        y_offset = 0
        used_pins = {"21": False, "22": False}  # Track used GPIO pins

        for i, block_id in enumerate(block_ids):
            wokwi = WOKWI_PARTS.get(block_id)
            if not wokwi or block_id.endswith("_manifest"):
                continue

            part_id = f"part{i}"
            parts.append({
                "type": wokwi["type"],
                "id": part_id,
                "top": y_offset,
                "left": x_offset,
                "attrs": wokwi.get("attrs", {}),
            })

            # Auto-wire based on bus type
            bus = self._detect_bus(block_id)
            template = WIRING_TEMPLATES.get(bus, WIRING_TEMPLATES["digital"])
            for wire in template:
                connections.append([
                    wire["from"].replace("{part}", part_id),
                    wire["to"],
                    wire["color"],
                    [],
                ])

            y_offset += 120

        return {
            "version": 1,
            "author": "Parakram AI",
            "editor": "wokwi",
            "parts": parts,
            "connections": connections,
            "serialMonitor": {"display": "auto"},
        }

    def get_simulation_url(self, diagram: dict, firmware_hex: Optional[str] = None) -> str:
        """Generate a Wokwi simulation URL."""
        base = "https://wokwi.com/projects/new/esp32"
        # In a real integration, you'd POST to Wokwi's API
        # For now, return the basic URL with diagram hash
        return base

    def generate_wokwi_toml(self, board: str = "esp32dev") -> str:
        """Generate wokwi.toml for PlatformIO integration."""
        firmware_path = ".pio/build/esp32dev/firmware.bin"
        if "s3" in board:
            firmware_path = ".pio/build/esp32s3/firmware.bin"
        elif "c3" in board:
            firmware_path = ".pio/build/esp32c3/firmware.bin"

        return f"""[wokwi]
version = 1
firmware = "{firmware_path}"
elf = "{firmware_path.replace('.bin', '.elf')}"
"""

    def _get_mcu_part(self, board: str) -> str:
        """Map board ID to Wokwi MCU part type."""
        mapping = {
            "esp32dev": "wokwi-esp32-devkit-v1",
            "esp32s3": "board-esp32-s3-devkitc-1",
            "esp32c3": "board-esp32-c3-devkitm-1",
        }
        return mapping.get(board, "wokwi-esp32-devkit-v1")

    def _detect_bus(self, block_id: str) -> str:
        """Detect the likely bus type for a block."""
        i2c_blocks = {"bme280", "ssd1306_oled", "lcd_i2c_16x2", "lcd_20x4", "mpu6050_imu",
                       "ina219_current", "ads1115_adc", "bh1750_light", "vl53l0x_tof"}
        spi_blocks = {"rfid_rc522", "sd_card", "max31855_thermocouple", "w5500_ethernet"}
        onewire_blocks = {"ds18b20"}
        analog_blocks = {"potentiometer", "photoresistor", "soil_moisture", "mq2_gas",
                          "tds_meter", "ph_sensor", "turbidity_sensor"}
        servo_blocks = {"servo_sg90", "servo_mg996r"}

        if block_id in i2c_blocks: return "i2c"
        if block_id in spi_blocks: return "spi"
        if block_id in onewire_blocks: return "onewire"
        if block_id in analog_blocks: return "analog"
        if block_id in servo_blocks: return "servo"
        return "digital"
