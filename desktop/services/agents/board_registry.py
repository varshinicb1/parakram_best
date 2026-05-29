"""
Board Registry — Multi-board hardware profiles.

Defines pin maps, peripherals, memory, and constraints for:
ESP32 DevKit, ESP32-S3, ESP32-C3, STM32F4, RP2040, Arduino Mega.
"""

BOARDS: dict[str, dict] = {
    "esp32dev": {
        "name": "ESP32 DevKit V1",
        "platform": "espressif32",
        "framework": "arduino",
        "mcu": "ESP32",
        "clock_mhz": 240,
        "flash_kb": 4096,
        "ram_kb": 520,
        "gpio_count": 34,
        "adc_pins": [32, 33, 34, 35, 36, 39, 25, 26, 27, 14, 12, 13, 4, 2, 15],
        "adc2_pins": [25, 26, 27, 14, 12, 13, 4, 2, 15],  # Unavailable when WiFi active
        "dac_pins": [25, 26],
        "touch_pins": [4, 2, 15, 13, 12, 14, 27, 33, 32],
        "i2c_default": {"sda": 21, "scl": 22},
        "spi_default": {"mosi": 23, "miso": 19, "sck": 18, "cs": 5},
        "uart_pins": {"tx": 1, "rx": 3, "tx2": 17, "rx2": 16},
        "pwm_channels": 16,
        "safe_gpio": [4, 5, 13, 14, 16, 17, 18, 19, 21, 22, 23, 25, 26, 27, 32, 33],
        "boot_restricted": [0, 2, 12, 15],  # Strapping pins
        "input_only": [34, 35, 36, 39],
        "flash_pins": [6, 7, 8, 9, 10, 11],  # Connected to flash, do not use
        "builtin_led": 2,
        "features": ["WiFi", "Bluetooth", "BLE", "TouchSensor", "HallSensor", "DAC", "I2S"],
        "conflicts": {
            "adc2_wifi": "ADC2 pins (25,26,27,14,12,13,4,2,15) cannot be used when WiFi is active",
            "gpio12_boot": "GPIO12 must be LOW at boot (affects flash voltage)",
        },
    },

    "esp32-s3-devkitc-1": {
        "name": "ESP32-S3 DevKitC-1",
        "platform": "espressif32",
        "framework": "arduino",
        "mcu": "ESP32-S3",
        "clock_mhz": 240,
        "flash_kb": 8192,
        "ram_kb": 512,
        "psram_kb": 8192,
        "gpio_count": 45,
        "adc_pins": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        "adc2_pins": [11, 12, 13, 14, 15, 16, 17, 18, 19, 20],
        "i2c_default": {"sda": 8, "scl": 9},
        "spi_default": {"mosi": 11, "miso": 13, "sck": 12, "cs": 10},
        "pwm_channels": 8,
        "safe_gpio": list(range(1, 22)) + list(range(35, 46)),
        "boot_restricted": [0, 3, 45, 46],
        "flash_pins": [26, 27, 28, 29, 30, 31, 32],
        "builtin_led": 48,
        "features": ["WiFi", "BLE5", "USB-OTG", "LCD", "Camera", "AI-Accel", "TouchSensor"],
        "conflicts": {},
        "usb_pins": {"dp": 20, "dm": 19},
    },

    "esp32-c3-devkitm-1": {
        "name": "ESP32-C3 DevKitM-1",
        "platform": "espressif32",
        "framework": "arduino",
        "mcu": "ESP32-C3",
        "clock_mhz": 160,
        "flash_kb": 4096,
        "ram_kb": 400,
        "gpio_count": 22,
        "adc_pins": [0, 1, 2, 3, 4],
        "i2c_default": {"sda": 8, "scl": 9},
        "spi_default": {"mosi": 7, "miso": 2, "sck": 6, "cs": 10},
        "pwm_channels": 6,
        "safe_gpio": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 18, 19, 20, 21],
        "boot_restricted": [8, 9],
        "builtin_led": 8,
        "features": ["WiFi", "BLE5", "USB-Serial"],
        "conflicts": {},
    },

    "nucleo_f446re": {
        "name": "STM32 Nucleo F446RE",
        "platform": "ststm32",
        "framework": "arduino",
        "mcu": "STM32F446RE",
        "clock_mhz": 180,
        "flash_kb": 512,
        "ram_kb": 128,
        "gpio_count": 51,
        "adc_pins": ["A0", "A1", "A2", "A3", "A4", "A5"],
        "i2c_default": {"sda": "D14", "scl": "D15"},
        "spi_default": {"mosi": "D11", "miso": "D12", "sck": "D13", "cs": "D10"},
        "pwm_channels": 12,
        "safe_gpio": [f"D{i}" for i in range(16)] + [f"A{i}" for i in range(6)],
        "builtin_led": "D13",
        "features": ["UART", "I2C", "SPI", "CAN", "USB", "DAC", "Timer"],
        "conflicts": {},
    },

    "pico": {
        "name": "Raspberry Pi Pico (RP2040)",
        "platform": "raspberrypi",
        "framework": "arduino",
        "mcu": "RP2040",
        "clock_mhz": 133,
        "flash_kb": 2048,
        "ram_kb": 264,
        "gpio_count": 26,
        "adc_pins": [26, 27, 28],
        "i2c_default": {"sda": 4, "scl": 5},
        "spi_default": {"mosi": 19, "miso": 16, "sck": 18, "cs": 17},
        "pwm_channels": 16,
        "safe_gpio": list(range(0, 29)),
        "builtin_led": 25,
        "features": ["PIO", "DualCore", "USB", "I2C", "SPI", "UART", "PWM"],
        "conflicts": {},
    },

    "megaatmega2560": {
        "name": "Arduino Mega 2560",
        "platform": "atmelavr",
        "framework": "arduino",
        "mcu": "ATmega2560",
        "clock_mhz": 16,
        "flash_kb": 256,
        "ram_kb": 8,
        "gpio_count": 54,
        "adc_pins": list(range(54, 70)),  # A0-A15
        "i2c_default": {"sda": 20, "scl": 21},
        "spi_default": {"mosi": 51, "miso": 50, "sck": 52, "cs": 53},
        "pwm_channels": 15,
        "safe_gpio": list(range(2, 54)),
        "builtin_led": 13,
        "features": ["UART", "I2C", "SPI", "PWM", "Interrupts"],
        "conflicts": {},
    },
}


def get_board(board_id: str) -> dict:
    """Get board profile by PlatformIO board ID."""
    return BOARDS.get(board_id, BOARDS.get("esp32dev"))


def get_safe_pins(board_id: str) -> list:
    """Get pins safe to use for a board."""
    board = get_board(board_id)
    return board.get("safe_gpio", [])


def get_conflicts(board_id: str) -> dict:
    """Get known pin/peripheral conflicts for a board."""
    board = get_board(board_id)
    return board.get("conflicts", {})


def get_platformio_ini(board_id: str) -> str:
    """Generate board-specific platformio.ini content."""
    board = get_board(board_id)
    return f"""[env:{board_id}]
platform = {board['platform']}
board = {board_id}
framework = {board['framework']}
monitor_speed = 115200
"""


def list_boards() -> list[dict]:
    """List all supported boards with summary info."""
    return [
        {
            "id": bid,
            "name": b["name"],
            "mcu": b["mcu"],
            "clock_mhz": b["clock_mhz"],
            "ram_kb": b["ram_kb"],
            "flash_kb": b["flash_kb"],
            "gpio_count": b["gpio_count"],
            "features": b["features"],
        }
        for bid, b in BOARDS.items()
    ]
