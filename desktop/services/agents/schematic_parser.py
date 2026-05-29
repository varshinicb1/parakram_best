"""
Schematic Parser — Reads KiCad and EasyEDA schematics.

Extracts components, pin connections, I2C addresses, and generates
Parakram block graphs from circuit diagrams.
"""

import os
import re
import json
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class SchematicComponent:
    """A component extracted from a schematic."""
    ref: str              # Reference designator (U1, R1, C1)
    value: str            # Component value (ESP32, 10K, 100nF)
    footprint: str = ""   # Package footprint
    lib_id: str = ""      # Library component ID
    pins: dict = field(default_factory=dict)  # pin_name -> net_name
    properties: dict = field(default_factory=dict)


@dataclass
class SchematicNet:
    """An electrical net (wire) connecting pins."""
    name: str
    pins: list = field(default_factory=list)  # [(ref, pin_name), ...]


# ── Map schematic component values to Parakram blocks ────
COMPONENT_TO_BLOCK = {
    # Sensors
    "DHT22": "dht22", "DHT11": "dht22", "AM2302": "dht22",
    "BME280": "bme280", "BMP280": "bmp280",
    "MPU6050": "mpu6050", "MPU-6050": "mpu6050",
    "BH1750": "bh1750", "BH1750FVI": "bh1750",
    "ADS1115": "ads1115", "ADS1015": "ads1115",
    "INA219": "ina219",
    "VL53L0X": "vl53l0x",
    "SHT31": "sht31", "SHT30": "sht31",
    "MAX30102": "max30102",

    # Displays
    "SSD1306": "i2c_oled", "SSD1309": "i2c_oled",
    "ILI9341": "spi_display", "ST7789": "spi_display",

    # Communication
    "ESP32": "esp32_manifest",
    "ESP-WROOM-32": "esp32_manifest",
    "ESP32-S3": "esp32_manifest",
    "ESP32-C3": "esp32_manifest",

    # Actuators
    "SG90": "servo_motor", "MG996R": "servo_motor",
    "LED": "led_output",

    # Audio
    "INMP441": "i2s_microphone",
    "MAX98357": "i2s_speaker", "MAX98357A": "i2s_speaker",
}

# I2C address defaults
I2C_ADDRESSES = {
    "bme280": "0x76", "bmp280": "0x76",
    "mpu6050": "0x68", "bh1750": "0x23",
    "ads1115": "0x48", "ina219": "0x40",
    "vl53l0x": "0x29", "ssd1306": "0x3C",
    "sht31": "0x44",
}


class SchematicParser:
    """Parse schematics from KiCad and EasyEDA formats."""

    def parse_kicad(self, filepath: str) -> dict:
        """
        Parse KiCad 6+ schematic (.kicad_sch) file.
        Returns components, nets, and inferred block graph.
        """
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        components = self._parse_kicad_symbols(content)
        nets = self._parse_kicad_wires(content, components)
        graph = self._infer_block_graph(components, nets)

        return {
            "format": "kicad",
            "components": [self._comp_to_dict(c) for c in components],
            "nets": [{"name": n.name, "pins": n.pins} for n in nets],
            "block_graph": graph,
        }

    def parse_easyeda(self, filepath: str) -> dict:
        """
        Parse EasyEDA JSON export.
        Returns components, nets, and inferred block graph.
        """
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        components = []
        nets = []

        # EasyEDA stores components in "schlib" or "components"
        for sheet in data.get("schematics", [data]):
            for comp_data in sheet.get("components", []):
                comp = SchematicComponent(
                    ref=comp_data.get("ref", ""),
                    value=comp_data.get("value", ""),
                    footprint=comp_data.get("footprint", ""),
                    lib_id=comp_data.get("lib_id", ""),
                )
                # Extract pin mappings
                for pin in comp_data.get("pins", []):
                    comp.pins[pin.get("name", "")] = pin.get("net", "")
                components.append(comp)

            for net_data in sheet.get("nets", []):
                net = SchematicNet(
                    name=net_data.get("name", ""),
                    pins=[(p.get("ref", ""), p.get("pin", "")) for p in net_data.get("pins", [])],
                )
                nets.append(net)

        graph = self._infer_block_graph(components, nets)

        return {
            "format": "easyeda",
            "components": [self._comp_to_dict(c) for c in components],
            "nets": [{"name": n.name, "pins": n.pins} for n in nets],
            "block_graph": graph,
        }

    def _parse_kicad_symbols(self, content: str) -> list[SchematicComponent]:
        """Extract component symbols from KiCad schematic."""
        components = []

        # KiCad 6+ S-expression format: (symbol (lib_id "...") (at x y angle) ...)
        sym_pattern = re.compile(
            r'\(symbol\s+\(lib_id\s+"([^"]+)"\)'
            r'.*?\(property\s+"Reference"\s+"([^"]+)".*?'
            r'\(property\s+"Value"\s+"([^"]+)"',
            re.DOTALL
        )

        for match in sym_pattern.finditer(content):
            lib_id = match.group(1)
            ref = match.group(2)
            value = match.group(3)

            comp = SchematicComponent(
                ref=ref,
                value=value,
                lib_id=lib_id,
            )
            components.append(comp)

        return components

    def _parse_kicad_wires(self, content: str, components: list) -> list[SchematicNet]:
        """Extract wire/net connections from KiCad schematic."""
        nets = []

        # Parse labels and global labels as nets
        label_pattern = re.compile(r'\((?:label|global_label)\s+"([^"]+)"')
        for match in label_pattern.finditer(content):
            net_name = match.group(1)
            if not any(n.name == net_name for n in nets):
                nets.append(SchematicNet(name=net_name))

        # Common net names
        for name in ["SDA", "SCL", "MOSI", "MISO", "SCK", "VCC", "GND", "3V3", "5V"]:
            if name in content and not any(n.name == name for n in nets):
                nets.append(SchematicNet(name=name))

        return nets

    def _infer_block_graph(
        self, components: list[SchematicComponent], nets: list[SchematicNet]
    ) -> dict:
        """Convert schematic components into a Parakram block graph."""
        nodes = []
        edges = []

        esp_node_id = None

        for comp in components:
            # Map component value to Parakram block
            value_upper = comp.value.upper().replace("-", "").replace("_", "")
            block_id = None
            for key, bid in COMPONENT_TO_BLOCK.items():
                if key.upper().replace("-", "").replace("_", "") in value_upper:
                    block_id = bid
                    break

            if not block_id:
                continue

            # Determine category
            if block_id == "esp32_manifest":
                category = "board"
                esp_node_id = comp.ref
            elif block_id in ("dht22", "bme280", "bmp280", "mpu6050", "bh1750",
                              "ads1115", "ina219", "vl53l0x", "sht31", "max30102"):
                category = "sensor"
            elif block_id in ("i2c_oled", "spi_display"):
                category = "display"
            elif block_id in ("servo_motor", "led_output"):
                category = "actuator"
            elif block_id in ("i2s_microphone", "i2s_speaker"):
                category = "audio"
            else:
                category = "other"

            node = {
                "id": comp.ref,
                "block_id": block_id,
                "name": comp.value,
                "category": category,
                "schematic_ref": comp.ref,
            }

            # Add I2C address if known
            if block_id in I2C_ADDRESSES:
                node["i2c_address"] = I2C_ADDRESSES[block_id]

            nodes.append(node)

        # Create edges based on shared nets (especially I2C SDA/SCL)
        i2c_nodes = [n for n in nodes if n.get("i2c_address")]
        for node in i2c_nodes:
            if esp_node_id:
                edges.append({
                    "source": esp_node_id,
                    "target": node["id"],
                    "bus": "I2C",
                    "label": f"I2C ({node.get('i2c_address', '?')})",
                })

        return {
            "nodes": nodes,
            "edges": edges,
            "board": esp_node_id,
            "i2c_bus": [n["id"] for n in i2c_nodes],
        }

    def _comp_to_dict(self, comp: SchematicComponent) -> dict:
        return {
            "ref": comp.ref,
            "value": comp.value,
            "footprint": comp.footprint,
            "lib_id": comp.lib_id,
            "pins": comp.pins,
        }


class HardwareValidator:
    """
    Cross-reference schematic with firmware.
    Validates electrical correctness.
    """

    def validate(self, schematic: dict, firmware_source: str) -> list[dict]:
        """Check firmware against schematic for mismatches."""
        issues = []

        # Check all I2C devices have pull-up resistors
        i2c_nodes = schematic.get("block_graph", {}).get("i2c_bus", [])
        components = schematic.get("components", [])
        resistor_values = [c["value"] for c in components if c["ref"].startswith("R")]

        if i2c_nodes:
            has_pullup = any(
                "4.7" in v or "4K7" in v.upper() or "10K" in v.upper()
                for v in resistor_values
            )
            if not has_pullup:
                issues.append({
                    "severity": "warning",
                    "message": "I2C bus has no pull-up resistors",
                    "fix": "Add 4.7KΩ pull-ups on SDA and SCL lines",
                })

        # Check voltage levels
        has_5v = any(c["value"] in ("5V", "VCC") for c in components)
        has_3v3 = any("3.3" in c["value"] or "3V3" in c["value"] for c in components)
        if has_5v and has_3v3:
            # Check for level shifter
            has_level_shift = any(
                "level" in c["value"].lower() or "txb" in c["value"].lower()
                for c in components
            )
            if not has_level_shift:
                issues.append({
                    "severity": "warning",
                    "message": "Mixed 3.3V and 5V components without level shifter",
                    "fix": "Add bidirectional level shifter (TXB0108 or equivalent)",
                })

        # Check pin usage matches firmware
        gpio_in_firmware = set(re.findall(r'(?:GPIO|pinMode\()\s*(\d+)', firmware_source))
        gpio_in_schematic = set()
        for net in schematic.get("nets", []):
            pin_match = re.search(r'GPIO(\d+)', net.get("name", ""))
            if pin_match:
                gpio_in_schematic.add(pin_match.group(1))

        # Find pins in firmware but not schematic
        orphan_pins = gpio_in_firmware - gpio_in_schematic
        if orphan_pins and gpio_in_schematic:
            issues.append({
                "severity": "info",
                "message": f"GPIO pins in firmware but not in schematic: {orphan_pins}",
                "fix": "Verify pin assignments match the schematic",
            })

        return issues
