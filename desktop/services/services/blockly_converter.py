"""
BlocklyDuino Converter — Converts BlocklyDuino XML blocks to Parakram golden block graph.

Maps BlocklyDuino block types → golden block IDs for seamless import.
"""

import xml.etree.ElementTree as ET


# BlocklyDuino block type → Parakram golden block ID mapping
BLOCKLY_TO_GOLDEN = {
    # GPIO
    "grove_led": "led_output",
    "grove_button": "button_debounce",
    "grove_rotary_angle": "rotary_encoder",
    "grove_piezo_buzzer": "buzzer",
    "grove_relay": "relay_module",
    "grove_tilt_switch": "vibration_sw420",

    # Sensors
    "grove_temporature_sensor": "thermistor",
    "grove_sound_sensor": "sound_sensor",
    "grove_light_sensor": "light_sensor",
    "grove_moisture_sensor": "soil_moisture",
    "grove_pir_motion_sensor": "pir_sensor",
    "grove_ultrasonic_ranger": "ultrasonic_hcsr04",
    "grove_ir_receiver": "ir_receiver",
    "grove_ir_emitter": "ir_transmitter",

    # I2C Sensors
    "grove_dht": "dht22",
    "grove_barometer_sensor": "bmp280",
    "grove_rgb_lcd": "lcd_i2c",
    "grove_oled_display": "i2c_oled",

    # Actuators
    "servo_move": "servo_motor",
    "servo_read_degrees": "servo_motor",
    "grove_motor_shield": "dc_motor_l298n",
    "grove_rgb_led": "rgb_led",
    "neopixel_init": "neopixel_strip",

    # Communication
    "serial_print": "wifi_station",  # fallback to serial
    "wifi_connect": "wifi_station",
    "mqtt_connect": "mqtt_client",
    "ble_init": "ble_server",

    # Standard Arduino
    "base_delay": None,  # handled as code
    "controls_if": None,
    "controls_repeat": None,
    "math_number": None,
    "text": None,
    "variables_set": None,
    "variables_get": None,
}


class BlocklyConverter:
    """Converts BlocklyDuino XML workspace to Parakram block graph."""

    def __init__(self):
        self.blocks_used = set()
        self.pin_assignments = {}

    def parse_xml(self, xml_string: str) -> dict:
        """Parse BlocklyDuino XML and return a Parakram-compatible block graph."""
        try:
            root = ET.fromstring(xml_string)
        except ET.ParseError as e:
            return {"error": f"Invalid XML: {e}", "blocks": []}

        blocks = []
        for block_elem in root.iter("block"):
            block_type = block_elem.get("type", "")
            golden_id = BLOCKLY_TO_GOLDEN.get(block_type)

            if golden_id:
                self.blocks_used.add(golden_id)

                # Extract pin from field if present
                pin_field = block_elem.find(".//field[@name='PIN']")
                pin = pin_field.text if pin_field is not None else None

                blocks.append({
                    "blockly_type": block_type,
                    "golden_block_id": golden_id,
                    "pin": pin,
                })

            # Extract value fields for parameters
            for field in block_elem.findall("field"):
                name = field.get("name", "")
                value = field.text
                if name == "PIN" and golden_id:
                    self.pin_assignments[golden_id] = value

        return {
            "golden_blocks": list(self.blocks_used),
            "pin_assignments": self.pin_assignments,
            "block_details": blocks,
            "total_blockly_blocks": len(list(root.iter("block"))),
            "mapped_blocks": len(blocks),
            "unmapped_types": [
                b.get("type") for b in root.iter("block")
                if b.get("type") not in BLOCKLY_TO_GOLDEN
            ],
        }

    def to_parakram_prompt(self, parsed: dict) -> str:
        """Convert parsed BlocklyDuino graph to a natural language prompt for the pipeline."""
        if not parsed.get("golden_blocks"):
            return ""

        block_names = ", ".join(parsed["golden_blocks"])
        return f"Build firmware using these components: {block_names}"

    def get_supported_blockly_types(self) -> list[str]:
        """Return all supported BlocklyDuino block types."""
        return [k for k, v in BLOCKLY_TO_GOLDEN.items() if v is not None]
