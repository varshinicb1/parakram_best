"""
Multi-Board Support — Board profiles for ESP32, STM32, and RP2040.

Each profile defines:
  - PlatformIO board ID and framework
  - Default pin mappings (I2C, SPI, UART)
  - Flash/RAM specs
  - platformio.ini template
"""

BOARD_PROFILES = {
    # ── ESP32 Family ──
    "esp32dev": {
        "name": "ESP32 DevKit V1",
        "platform": "espressif32",
        "framework": "arduino",
        "mcu": "esp32",
        "f_cpu": 240000000,
        "flash": "4MB",
        "ram": "520KB",
        "pins": {"sda": 21, "scl": 22, "mosi": 23, "miso": 19, "sck": 18, "cs": 5, "rx": 16, "tx": 17},
        "features": ["wifi", "ble", "hall_sensor", "touch", "dac", "adc", "i2s", "can"],
        "platformio_ini": """[env:esp32dev]
platform = espressif32
board = esp32dev
framework = arduino
monitor_speed = 115200
board_build.f_cpu = 240000000L
build_flags = -DCORE_DEBUG_LEVEL=1
""",
    },
    "esp32s3": {
        "name": "ESP32-S3 DevKit",
        "platform": "espressif32",
        "framework": "arduino",
        "mcu": "esp32s3",
        "f_cpu": 240000000,
        "flash": "16MB",
        "ram": "512KB + 8MB PSRAM",
        "pins": {"sda": 8, "scl": 9, "mosi": 11, "miso": 13, "sck": 12, "cs": 10, "rx": 44, "tx": 43},
        "features": ["wifi", "ble5", "usb_otg", "lcd_cam", "touch", "adc", "i2s"],
        "platformio_ini": """[env:esp32s3]
platform = espressif32
board = esp32-s3-devkitc-1
framework = arduino
monitor_speed = 115200
board_build.f_cpu = 240000000L
board_build.flash_mode = qio
board_build.psram = enabled
""",
    },
    "esp32c3": {
        "name": "ESP32-C3 Mini",
        "platform": "espressif32",
        "framework": "arduino",
        "mcu": "esp32c3",
        "f_cpu": 160000000,
        "flash": "4MB",
        "ram": "400KB",
        "pins": {"sda": 8, "scl": 9, "mosi": 6, "miso": 5, "sck": 4, "cs": 7, "rx": 20, "tx": 21},
        "features": ["wifi", "ble5", "usb_serial"],
        "platformio_ini": """[env:esp32c3]
platform = espressif32
board = esp32-c3-devkitm-1
framework = arduino
monitor_speed = 115200
""",
    },

    # ── STM32 Family ──
    "stm32f411": {
        "name": "STM32F411 BlackPill",
        "platform": "ststm32",
        "framework": "arduino",
        "mcu": "stm32f411ceu6",
        "f_cpu": 100000000,
        "flash": "512KB",
        "ram": "128KB",
        "pins": {"sda": "PB7", "scl": "PB6", "mosi": "PA7", "miso": "PA6", "sck": "PA5", "cs": "PA4", "rx": "PA10", "tx": "PA9"},
        "features": ["usb", "i2c", "spi", "uart", "adc", "dac", "pwm", "dma"],
        "platformio_ini": """[env:stm32f411]
platform = ststm32
board = blackpill_f411ce
framework = arduino
monitor_speed = 115200
upload_protocol = dfu
""",
    },
    "stm32f103": {
        "name": "STM32F103 BluePill",
        "platform": "ststm32",
        "framework": "arduino",
        "mcu": "stm32f103c8t6",
        "f_cpu": 72000000,
        "flash": "64KB",
        "ram": "20KB",
        "pins": {"sda": "PB7", "scl": "PB6", "mosi": "PA7", "miso": "PA6", "sck": "PA5", "cs": "PA4", "rx": "PA10", "tx": "PA9"},
        "features": ["usb", "i2c", "spi", "uart", "adc", "pwm", "can"],
        "platformio_ini": """[env:stm32f103]
platform = ststm32
board = bluepill_f103c8
framework = arduino
monitor_speed = 115200
upload_protocol = stlink
""",
    },
    "nucleo_f446re": {
        "name": "STM32 Nucleo F446RE",
        "platform": "ststm32",
        "framework": "arduino",
        "mcu": "stm32f446ret6",
        "f_cpu": 180000000,
        "flash": "512KB",
        "ram": "128KB",
        "pins": {"sda": "PB9", "scl": "PB8", "mosi": "PA7", "miso": "PA6", "sck": "PA5", "cs": "PB6", "rx": "PA10", "tx": "PA9"},
        "features": ["usb", "i2c", "spi", "uart", "adc", "dac", "pwm", "dma", "can", "i2s"],
        "platformio_ini": """[env:nucleo_f446re]
platform = ststm32
board = nucleo_f446re
framework = arduino
monitor_speed = 115200
""",
    },

    # ── RP2040 Family ──
    "pico": {
        "name": "Raspberry Pi Pico",
        "platform": "raspberrypi",
        "framework": "arduino",
        "mcu": "rp2040",
        "f_cpu": 133000000,
        "flash": "2MB",
        "ram": "264KB",
        "pins": {"sda": 4, "scl": 5, "mosi": 19, "miso": 16, "sck": 18, "cs": 17, "rx": 1, "tx": 0},
        "features": ["pio", "usb", "i2c", "spi", "uart", "adc", "pwm", "dma"],
        "platformio_ini": """[env:pico]
platform = raspberrypi
board = pico
framework = arduino
monitor_speed = 115200
""",
    },
    "pico_w": {
        "name": "Raspberry Pi Pico W",
        "platform": "raspberrypi",
        "framework": "arduino",
        "mcu": "rp2040",
        "f_cpu": 133000000,
        "flash": "2MB",
        "ram": "264KB",
        "pins": {"sda": 4, "scl": 5, "mosi": 19, "miso": 16, "sck": 18, "cs": 17, "rx": 1, "tx": 0},
        "features": ["wifi", "ble", "pio", "usb", "i2c", "spi", "uart", "adc", "pwm"],
        "platformio_ini": """[env:pico_w]
platform = raspberrypi
board = rpipicow
framework = arduino
monitor_speed = 115200
""",
    },
}


def get_board_profile(board_id: str) -> dict | None:
    """Get a board profile by ID."""
    return BOARD_PROFILES.get(board_id)


def list_boards() -> list[dict]:
    """List all supported boards with summary info."""
    return [
        {
            "id": bid,
            "name": bp["name"],
            "mcu": bp["mcu"],
            "platform": bp["platform"],
            "flash": bp["flash"],
            "ram": bp["ram"],
            "features": bp["features"],
        }
        for bid, bp in BOARD_PROFILES.items()
    ]


def get_pin_mapping(board_id: str) -> dict:
    """Get default pin mapping for a board."""
    bp = BOARD_PROFILES.get(board_id, {})
    return bp.get("pins", {})


def generate_platformio_ini(board_id: str, lib_deps: list[str] | None = None) -> str:
    """Generate complete platformio.ini for a board."""
    bp = BOARD_PROFILES.get(board_id)
    if not bp:
        return f"; Unknown board: {board_id}\n"

    ini: str = bp["platformio_ini"]
    if lib_deps:
        ini += "lib_deps =\n"
        for dep in lib_deps:
            ini += f"    {dep}\n"
    return ini
