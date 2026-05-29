"""
Pinout Visualizer — Generate MCU pinout data for visual rendering.

Provides pin maps, alternate functions, and electrical specs for
popular development boards. Used by the frontend to render interactive
pinout diagrams — a feature Embedder doesn't have.
"""

from dataclasses import dataclass, field


@dataclass
class Pin:
    number: int
    name: str
    gpio: str = ""
    functions: list[str] = field(default_factory=list)
    type: str = "gpio"  # gpio, power, gnd, nc, analog, special
    voltage: str = "3.3V"
    max_current_ma: float = 40
    adc: bool = False
    dac: bool = False
    touch: bool = False
    pwm: bool = False
    pull_up: bool = True
    pull_down: bool = True
    notes: str = ""


# ── ESP32 DevKit V1 Pinout ─────────────────────────────────

ESP32_DEVKIT = {
    "board": "ESP32 DevKit V1",
    "mcu": "ESP32-D0WDQ6",
    "pin_count": 30,
    "sides": {
        "left": [
            Pin(1, "3V3", type="power", voltage="3.3V", notes="3.3V output"),
            Pin(2, "EN", gpio="EN", type="special", notes="Reset/Enable"),
            Pin(3, "VP", gpio="GPIO36", functions=["ADC1_CH0", "SENSOR_VP"], adc=True, type="analog", notes="Input only"),
            Pin(4, "VN", gpio="GPIO39", functions=["ADC1_CH3", "SENSOR_VN"], adc=True, type="analog", notes="Input only"),
            Pin(5, "D34", gpio="GPIO34", functions=["ADC1_CH6"], adc=True, type="analog", notes="Input only"),
            Pin(6, "D35", gpio="GPIO35", functions=["ADC1_CH7"], adc=True, type="analog", notes="Input only"),
            Pin(7, "D32", gpio="GPIO32", functions=["ADC1_CH4", "TOUCH9", "XTAL32"], adc=True, touch=True, pwm=True),
            Pin(8, "D33", gpio="GPIO33", functions=["ADC1_CH5", "TOUCH8", "XTAL32"], adc=True, touch=True, pwm=True),
            Pin(9, "D25", gpio="GPIO25", functions=["ADC2_CH8", "DAC1"], adc=True, dac=True, pwm=True),
            Pin(10, "D26", gpio="GPIO26", functions=["ADC2_CH9", "DAC2"], adc=True, dac=True, pwm=True),
            Pin(11, "D27", gpio="GPIO27", functions=["ADC2_CH7", "TOUCH7"], adc=True, touch=True, pwm=True),
            Pin(12, "D14", gpio="GPIO14", functions=["ADC2_CH6", "TOUCH6", "HSPI_CLK"], adc=True, touch=True, pwm=True),
            Pin(13, "D12", gpio="GPIO12", functions=["ADC2_CH5", "TOUCH5", "HSPI_MISO"], adc=True, touch=True, pwm=True, notes="Boot fail if pulled HIGH"),
            Pin(14, "GND", type="gnd", notes="Ground"),
            Pin(15, "D13", gpio="GPIO13", functions=["ADC2_CH4", "TOUCH4", "HSPI_MOSI"], adc=True, touch=True, pwm=True),
        ],
        "right": [
            Pin(16, "VIN", type="power", voltage="5V", notes="5V input (USB)"),
            Pin(17, "GND", type="gnd", notes="Ground"),
            Pin(18, "D15", gpio="GPIO15", functions=["ADC2_CH3", "TOUCH3", "HSPI_CS"], adc=True, touch=True, pwm=True, notes="PWM at boot"),
            Pin(19, "D2", gpio="GPIO2", functions=["ADC2_CH2", "TOUCH2", "LED"], adc=True, touch=True, pwm=True, notes="On-board LED"),
            Pin(20, "D4", gpio="GPIO4", functions=["ADC2_CH0", "TOUCH0"], adc=True, touch=True, pwm=True),
            Pin(21, "RX2", gpio="GPIO16", functions=["UART2_RX"], pwm=True),
            Pin(22, "TX2", gpio="GPIO17", functions=["UART2_TX"], pwm=True),
            Pin(23, "D5", gpio="GPIO5", functions=["VSPI_CS"], pwm=True, notes="Outputs PWM at boot"),
            Pin(24, "D18", gpio="GPIO18", functions=["VSPI_CLK"], pwm=True),
            Pin(25, "D19", gpio="GPIO19", functions=["VSPI_MISO"], pwm=True),
            Pin(26, "D21", gpio="GPIO21", functions=["I2C_SDA"], pwm=True, notes="Default I2C SDA"),
            Pin(27, "RX0", gpio="GPIO3", functions=["UART0_RX"], notes="Serial monitor RX"),
            Pin(28, "TX0", gpio="GPIO1", functions=["UART0_TX"], notes="Serial monitor TX"),
            Pin(29, "D22", gpio="GPIO22", functions=["I2C_SCL"], pwm=True, notes="Default I2C SCL"),
            Pin(30, "D23", gpio="GPIO23", functions=["VSPI_MOSI"], pwm=True),
        ],
    },
}

# ── Arduino Uno Pinout ─────────────────────────────────────

ARDUINO_UNO = {
    "board": "Arduino Uno",
    "mcu": "ATmega328P",
    "pin_count": 28,
    "sides": {
        "digital": [
            Pin(1, "D0/RX", gpio="PD0", functions=["UART_RX"], notes="Serial RX"),
            Pin(2, "D1/TX", gpio="PD1", functions=["UART_TX"], notes="Serial TX"),
            Pin(3, "D2", gpio="PD2", functions=["INT0"], pwm=False),
            Pin(4, "D3~", gpio="PD3", functions=["INT1", "PWM"], pwm=True),
            Pin(5, "D4", gpio="PD4", functions=["T0"]),
            Pin(6, "D5~", gpio="PD5", functions=["PWM", "T1"], pwm=True),
            Pin(7, "D6~", gpio="PD6", functions=["PWM"], pwm=True),
            Pin(8, "D7", gpio="PD7"),
            Pin(9, "D8", gpio="PB0", functions=["ICP1"]),
            Pin(10, "D9~", gpio="PB1", functions=["PWM"], pwm=True),
            Pin(11, "D10~", gpio="PB2", functions=["PWM", "SPI_SS"], pwm=True),
            Pin(12, "D11~", gpio="PB3", functions=["PWM", "SPI_MOSI"], pwm=True),
            Pin(13, "D12", gpio="PB4", functions=["SPI_MISO"]),
            Pin(14, "D13", gpio="PB5", functions=["SPI_SCK", "LED"], notes="On-board LED"),
        ],
        "analog": [
            Pin(15, "A0", gpio="PC0", functions=["ADC0"], adc=True, type="analog"),
            Pin(16, "A1", gpio="PC1", functions=["ADC1"], adc=True, type="analog"),
            Pin(17, "A2", gpio="PC2", functions=["ADC2"], adc=True, type="analog"),
            Pin(18, "A3", gpio="PC3", functions=["ADC3"], adc=True, type="analog"),
            Pin(19, "A4/SDA", gpio="PC4", functions=["ADC4", "I2C_SDA"], adc=True, type="analog"),
            Pin(20, "A5/SCL", gpio="PC5", functions=["ADC5", "I2C_SCL"], adc=True, type="analog"),
        ],
        "power": [
            Pin(21, "VIN", type="power", voltage="7-12V"),
            Pin(22, "5V", type="power", voltage="5V"),
            Pin(23, "3.3V", type="power", voltage="3.3V"),
            Pin(24, "GND", type="gnd"),
            Pin(25, "GND", type="gnd"),
            Pin(26, "RESET", type="special"),
            Pin(27, "IOREF", type="power", voltage="5V"),
            Pin(28, "AREF", type="special", notes="ADC reference voltage"),
        ],
    },
}

BOARD_PINOUTS = {
    "esp32dev": ESP32_DEVKIT,
    "esp32-devkitc": ESP32_DEVKIT,
    "uno": ARDUINO_UNO,
    "arduino_uno": ARDUINO_UNO,
}


def get_pinout(board_id: str) -> dict | None:
    """Get pinout data for a board."""
    key = board_id.lower().replace("-", "").replace("_", "")
    for k, v in BOARD_PINOUTS.items():
        if k.replace("-", "").replace("_", "") == key:
            return _serialize_pinout(v)
    return None


def _serialize_pinout(pinout: dict) -> dict:
    """Convert pinout to JSON-safe dict."""
    result = {
        "board": pinout["board"],
        "mcu": pinout["mcu"],
        "pin_count": pinout["pin_count"],
        "sides": {},
    }
    for side_name, pins in pinout["sides"].items():
        result["sides"][side_name] = [
            {
                "number": p.number, "name": p.name, "gpio": p.gpio,
                "functions": p.functions, "type": p.type, "voltage": p.voltage,
                "adc": p.adc, "dac": p.dac, "touch": p.touch, "pwm": p.pwm,
                "notes": p.notes,
            }
            for p in pins
        ]
    return result


def list_available_pinouts() -> list[str]:
    return list(BOARD_PINOUTS.keys())
