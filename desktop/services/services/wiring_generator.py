"""
Wiring Diagram Generator — Auto-generate connection tables and wiring instructions.

Given a list of components and target board, generates:
  - Pin-to-pin wiring table (component pin → MCU pin)
  - Power rail connections
  - Pull-up/pull-down resistor requirements
  - I2C bus addressing (when multiple I2C devices)
  - SPI chip select assignments
  - Breadboard layout suggestions
  - Copy-paste Arduino/ESP-IDF pin definitions

Parakram exclusive — Embedder doesn't have visual wiring assistance.
"""

from dataclasses import dataclass, field


@dataclass
class WireConnection:
    component: str
    component_pin: str
    mcu_pin: str
    gpio: str
    wire_color: str
    notes: str = ""


# ── Component Pinout Database ──────────────────────────────

COMPONENT_PINS = {
    "BME280": {
        "interface": "I2C",
        "vcc": "3.3V",
        "gnd": "GND",
        "pins": {"SDA": "I2C_SDA", "SCL": "I2C_SCL"},
        "i2c_addr": "0x76 (or 0x77 with SDO pulled HIGH)",
        "pull_ups": "4.7kΩ on SDA and SCL (if not on breakout)",
        "notes": "3.3V only — do NOT connect to 5V",
    },
    "SSD1306": {
        "interface": "I2C",
        "vcc": "3.3V",
        "gnd": "GND",
        "pins": {"SDA": "I2C_SDA", "SCL": "I2C_SCL"},
        "i2c_addr": "0x3C (128x64) or 0x3D (128x32)",
        "pull_ups": "Already on most breakouts",
        "notes": "Works at 3.3V or 5V (check your module)",
    },
    "MPU6050": {
        "interface": "I2C",
        "vcc": "3.3V",
        "gnd": "GND",
        "pins": {"SDA": "I2C_SDA", "SCL": "I2C_SCL", "INT": "GPIO (optional)"},
        "i2c_addr": "0x68 (AD0 LOW) or 0x69 (AD0 HIGH)",
        "pull_ups": "Already on GY-521 breakout",
        "notes": "AD0 pin sets I2C address",
    },
    "DHT22": {
        "interface": "OneWire",
        "vcc": "3.3V-5V",
        "gnd": "GND",
        "pins": {"DATA": "GPIO (any)"},
        "pull_ups": "10kΩ pull-up on DATA pin",
        "notes": "2-second minimum between reads",
    },
    "HC-SR04": {
        "interface": "GPIO",
        "vcc": "5V",
        "gnd": "GND",
        "pins": {"TRIG": "GPIO (any)", "ECHO": "GPIO (any)"},
        "notes": "ECHO returns 5V — use voltage divider for 3.3V MCUs!",
    },
    "MCP2515": {
        "interface": "SPI",
        "vcc": "5V",
        "gnd": "GND",
        "pins": {"SCK": "SPI_CLK", "MOSI": "SPI_MOSI", "MISO": "SPI_MISO", "CS": "GPIO (any)", "INT": "GPIO (any)"},
        "notes": "CAN transceiver — needs CAN bus termination (120Ω)",
    },
    "NeoPixel": {
        "interface": "GPIO",
        "vcc": "5V",
        "gnd": "GND",
        "pins": {"DIN": "GPIO (any)"},
        "notes": "Use 300-500Ω series resistor on DIN, 1000µF cap on power",
    },
    "SX1276": {
        "interface": "SPI",
        "vcc": "3.3V",
        "gnd": "GND",
        "pins": {"SCK": "SPI_CLK", "MOSI": "SPI_MOSI", "MISO": "SPI_MISO", "NSS": "GPIO", "DIO0": "GPIO", "RST": "GPIO"},
        "notes": "LoRa module — requires antenna, DO NOT transmit without antenna!",
    },
    "MAX30102": {
        "interface": "I2C",
        "vcc": "3.3V",
        "gnd": "GND",
        "pins": {"SDA": "I2C_SDA", "SCL": "I2C_SCL", "INT": "GPIO"},
        "i2c_addr": "0x57",
        "notes": "Heart rate + SpO2 sensor",
    },
    "Relay": {
        "interface": "GPIO",
        "vcc": "5V",
        "gnd": "GND",
        "pins": {"IN": "GPIO (any)"},
        "notes": "Active LOW — use transistor/MOSFET for ESP32 (3.3V GPIO may not trigger 5V relay)",
    },
    "SD_Card": {
        "interface": "SPI",
        "vcc": "3.3V",
        "gnd": "GND",
        "pins": {"CLK": "SPI_CLK", "MOSI": "SPI_MOSI", "MISO": "SPI_MISO", "CS": "GPIO"},
        "notes": "Use level shifter if MCU is 5V",
    },
    "ADS1115": {
        "interface": "I2C",
        "vcc": "3.3V",
        "gnd": "GND",
        "pins": {"SDA": "I2C_SDA", "SCL": "I2C_SCL", "ALRT": "GPIO (optional)"},
        "i2c_addr": "0x48 (ADDR→GND), 0x49 (ADDR→VDD)",
        "notes": "16-bit ADC, 4 channels",
    },
}

# ── Board Default Pin Assignments ──────────────────────────

BOARD_DEFAULTS = {
    "esp32dev": {
        "I2C_SDA": ("GPIO21", "D21"), "I2C_SCL": ("GPIO22", "D22"),
        "SPI_CLK": ("GPIO18", "D18"), "SPI_MOSI": ("GPIO23", "D23"),
        "SPI_MISO": ("GPIO19", "D19"), "SPI_CS": ("GPIO5", "D5"),
        "UART_TX": ("GPIO17", "TX2"), "UART_RX": ("GPIO16", "RX2"),
        "GPIO_POOL": ["GPIO4", "GPIO13", "GPIO14", "GPIO25", "GPIO26", "GPIO27", "GPIO32", "GPIO33"],
    },
    "uno": {
        "I2C_SDA": ("A4", "A4/SDA"), "I2C_SCL": ("A5", "A5/SCL"),
        "SPI_CLK": ("D13", "D13"), "SPI_MOSI": ("D11", "D11"),
        "SPI_MISO": ("D12", "D12"), "SPI_CS": ("D10", "D10"),
        "UART_TX": ("D1", "TX"), "UART_RX": ("D0", "RX"),
        "GPIO_POOL": ["D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9"],
    },
    "pico": {
        "I2C_SDA": ("GP4", "GP4"), "I2C_SCL": ("GP5", "GP5"),
        "SPI_CLK": ("GP18", "GP18"), "SPI_MOSI": ("GP19", "GP19"),
        "SPI_MISO": ("GP16", "GP16"), "SPI_CS": ("GP17", "GP17"),
        "UART_TX": ("GP0", "GP0"), "UART_RX": ("GP1", "GP1"),
        "GPIO_POOL": ["GP2", "GP3", "GP6", "GP7", "GP8", "GP9", "GP10", "GP11"],
    },
}


class WiringGenerator:
    """Generate wiring diagrams and connection tables."""

    def generate(self, components: list[str], board: str = "esp32dev") -> dict:
        """Generate wiring table for components on a board."""
        board_pins = BOARD_DEFAULTS.get(board, BOARD_DEFAULTS["esp32dev"])
        connections: list[dict] = []
        gpio_pool = list(board_pins.get("GPIO_POOL", []))
        gpio_idx = 0
        i2c_devices = []
        spi_devices = []
        power_notes = []
        pin_defines = []

        for comp_name in components:
            comp = COMPONENT_PINS.get(comp_name)
            if not comp:
                connections.append({
                    "component": comp_name, "component_pin": "?", "mcu_pin": "?",
                    "gpio": "?", "wire_color": "gray", "notes": f"Unknown component — check datasheet"
                })
                continue

            # Power connections
            connections.append({
                "component": comp_name, "component_pin": "VCC",
                "mcu_pin": comp["vcc"], "gpio": "—",
                "wire_color": "red", "notes": f"Power: {comp['vcc']}"
            })
            connections.append({
                "component": comp_name, "component_pin": "GND",
                "mcu_pin": "GND", "gpio": "—",
                "wire_color": "black", "notes": "Ground"
            })

            # Signal connections
            for pin_name, pin_type in comp["pins"].items():
                if pin_type in board_pins:
                    gpio, label = board_pins[pin_type]
                    wire = "green" if "SDA" in pin_name else "yellow" if "SCL" in pin_name else "blue" if "CLK" in pin_name else "orange"
                    connections.append({
                        "component": comp_name, "component_pin": pin_name,
                        "mcu_pin": label, "gpio": gpio,
                        "wire_color": wire, "notes": pin_type
                    })
                    pin_defines.append(f"#define {comp_name.upper()}_{pin_name.upper()}_PIN {gpio.replace('GPIO', '').replace('GP', '').replace('D', '')}")
                elif "GPIO" in pin_type and gpio_idx < len(gpio_pool):
                    gpio = gpio_pool[gpio_idx]
                    gpio_idx += 1
                    connections.append({
                        "component": comp_name, "component_pin": pin_name,
                        "mcu_pin": gpio, "gpio": gpio,
                        "wire_color": "white", "notes": f"Any GPIO — assigned {gpio}"
                    })
                    pin_defines.append(f"#define {comp_name.upper()}_{pin_name.upper()}_PIN {gpio.replace('GPIO', '').replace('GP', '').replace('D', '')}")

            # Track bus devices
            if comp["interface"] == "I2C":
                i2c_devices.append({"name": comp_name, "addr": comp.get("i2c_addr", "?")})
            elif comp["interface"] == "SPI":
                spi_devices.append(comp_name)

            # Notes
            if comp.get("pull_ups"):
                power_notes.append(f"{comp_name}: {comp['pull_ups']}")
            if comp.get("notes"):
                power_notes.append(f"⚠️ {comp_name}: {comp['notes']}")

        return {
            "board": board,
            "components": components,
            "connections": connections,
            "i2c_bus": i2c_devices,
            "spi_devices": spi_devices,
            "power_notes": power_notes,
            "pin_defines": "\n".join(pin_defines),
            "total_wires": len(connections),
        }


def get_wiring_generator() -> WiringGenerator:
    return WiringGenerator()
