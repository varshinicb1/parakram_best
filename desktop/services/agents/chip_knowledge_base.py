"""
Chip Knowledge Base — Pre-indexed hardware intelligence for Parakram OS.

Provides register maps, peripheral capabilities, pin constraints, and known errata
for major MCU families. This context is injected into LLM prompts to eliminate
hallucinated register addresses and incorrect peripheral configurations.

This is what makes Parakram beats Embedder — built-in chip intelligence
combined with user-uploadable datasheets.
"""

# ── Per-chip knowledge ─────────────────────────────────────

CHIP_KNOWLEDGE = {
    "esp32dev": """## ESP32 (Xtensa LX6 Dual-Core, 240 MHz)
- Flash: 4 MB, SRAM: 520 KB, RTC SRAM: 16 KB
- GPIO: 34 pins (GPIO0-39), but GPIO34-39 are INPUT ONLY
- ADC: 2x 12-bit SAR ADC (ADC1: GPIO32-39, ADC2: GPIO0,2,4,12-15,25-27)
  ⚠ ADC2 cannot be used when WiFi is active
- DAC: 2x 8-bit (GPIO25, GPIO26)
- Touch: 10 capacitive touch pins (T0-T9 on GPIO4,0,2,15,13,12,14,27,33,32)
- PWM: 16 channels (LEDC), any GPIO can output PWM
- I2C: 2 buses (default SDA=21, SCL=22, frequency up to 1 MHz)
- SPI: 3 buses (HSPI: GPIO12-15, VSPI: GPIO18-19,23,5)
  ⚠ SPI0/SPI1 reserved for flash, use HSPI or VSPI only
- UART: 3 (UART0: GPIO1/3 [serial monitor], UART1: GPIO9/10, UART2: GPIO16/17)
  ⚠ UART1 default pins connected to flash — remap to other GPIOs
- WiFi: 802.11 b/g/n, max 150 Mbps, STA+AP mode
- Bluetooth: Classic + BLE 4.2
- Deep sleep current: ~10 µA (RTC memory preserved)
- Boot pins: GPIO0 (LOW=download), GPIO2 (must be LOW or floating), GPIO12 (flash voltage)
  ⚠ Do NOT put external pullups on GPIO0, GPIO2, GPIO12 — can prevent boot

### Known Errata
- GPIO36/39 can cause spurious interrupts when WiFi is scanning (use INPUT_PULLUP on other pins)
- analogRead() on ADC2 will return 0 when WiFi is active — use ADC1 pins only
- ESP32 can brown-out during WiFi TX if supply voltage drops below 3.0V — add 100µF cap
- UART1 default pins (9,10) conflict with flash — always remap in code
""",

    "esp32-s3-devkitc-1": """## ESP32-S3 (Xtensa LX7 Dual-Core, 240 MHz)
- Flash: 8/16 MB, PSRAM: 2/8 MB, SRAM: 512 KB
- GPIO: 45 pins (GPIO0-48, some reserved)
- USB: Native USB-OTG (GPIO19=D-, GPIO20=D+)
  ⚠ Don't use GPIO19/20 for other purposes when USB is active
- ADC: 2x 12-bit (ADC1: GPIO1-10, ADC2: GPIO11-20)
- I2C: 2 buses, SPI: 4 buses, UART: 3
- Camera interface (DVP 8/16-bit)
- LCD interface (8080/SPI)
- AI acceleration: vector instructions for neural networks
- Deep sleep: ~7 µA
""",

    "esp32-c3-devkitm-1": """## ESP32-C3 (RISC-V Single-Core, 160 MHz)
- Flash: 4 MB, SRAM: 400 KB
- GPIO: 22 pins (GPIO0-21)
- ADC: 2x 12-bit (6 channels)
- I2C: 1 bus, SPI: 3 buses, UART: 2
- WiFi: 802.11 b/g/n
- Bluetooth: BLE 5.0 (no Classic BT)
- Low power: 5 µA deep sleep
- USB-Serial/JTAG built-in (GPIO18=D-, GPIO19=D+)
""",

    "nucleo_f446re": """## STM32F446RE (ARM Cortex-M4, 180 MHz, FPU)
- Flash: 512 KB, SRAM: 128 KB
- GPIO: Up to 114 I/O pins (Port A-H)
- ADC: 3x 12-bit ADC, up to 2.4 MSPS
- DAC: 2x 12-bit
- Timers: 14 (including advanced-control TIM1/TIM8)
- I2C: 3 buses (with SMBus), SPI: 4 buses, UART: 4 + 2 USART
- CAN: 2x CAN 2.0B
- USB: OTG FS
- DMA: 2x DMA controllers (16 streams total)
- FPU: Single-precision floating point
- HAL: Use STM32 HAL or LL (Low-Layer) drivers

### Pin Naming Convention
- Use PA0-PA15, PB0-PB15 etc. (not Arduino-style D0, D1)
- Alternate functions: each pin has up to 16 AF modes
- Always configure GPIO mode, speed, pull-up/down, and AF before use

### Clock Configuration
- HSE: 8 MHz crystal on Nucleo
- PLL: Configure for up to 180 MHz SYSCLK
- APB1 max: 45 MHz, APB2 max: 90 MHz
""",

    "nucleo_h743zi": """## STM32H743ZI (ARM Cortex-M7, 480 MHz, FPU+DSP)
- Flash: 2 MB (dual-bank), SRAM: 1 MB (multiple regions)
- DTCM: 128 KB (fastest), ITCM: 64 KB, AXI SRAM: 512 KB
- ADC: 3x 16-bit ADC @ 3.6 MSPS
- DAC: 2x 12-bit
- Ethernet: 10/100 Mbps MAC
- USB: OTG HS with PHY
- FDCAN: 2x CAN-FD
- SDMMC: 2 interfaces
- JPEG codec hardware accelerator

### Memory Placement (Critical!)
- DMA buffers MUST be in D2 SRAM (not DTCM — DTCM is not DMA-accessible)
- Use __attribute__((section(".RAM_D2"))) for DMA buffers
- Enable D-Cache and I-Cache for performance, but manage coherency for DMA
""",

    "pico": """## RP2040 (ARM Cortex-M0+, Dual-Core, 133 MHz)
- Flash: 2 MB external QSPI, SRAM: 264 KB (6 banks)
- GPIO: 30 pins (GPIO0-29), all 3.3V
- ADC: 4-channel 12-bit (GPIO26-29), internal temperature sensor on ADC4
- PIO: 2x Programmable I/O blocks (8 state machines total)
  → Can emulate any serial protocol (WS2812, VGA, DPI, etc.)
- I2C: 2 buses, SPI: 2 buses, UART: 2
- PWM: 16 channels (8 slices × 2 channels)
- USB: 1.1 Device and Host
- No WiFi/Bluetooth (use Pico W with CYW43439)
- Boot: Hold BOOTSEL button + plug USB = mass storage bootloader
""",

    "nrf52840_dk": """## nRF52840 (ARM Cortex-M4F, 64 MHz)
- Flash: 1 MB, RAM: 256 KB
- BLE 5.0 + Thread + Zigbee + 802.15.4
- USB 2.0 full-speed
- NFC-A tag
- ADC: 8-channel 12-bit SAADC
- PWM: 4 modules (4 channels each)
- QSPI: for external flash
- Crypto: AES-128, SHA-256, ECC hardware accelerators
- Power: 1.7-5.5V, System OFF: 0.3 µA
""",
}


# ── API ────────────────────────────────────────────────────

def get_chip_context(board_id: str) -> str:
    """Get chip-specific context for a board ID."""
    # Direct match
    if board_id in CHIP_KNOWLEDGE:
        return CHIP_KNOWLEDGE[board_id]

    # Fuzzy match
    board_lower = board_id.lower()
    for key, context in CHIP_KNOWLEDGE.items():
        if key in board_lower or board_lower in key:
            return context

    # Generic ESP32 fallback
    if "esp32" in board_lower:
        return CHIP_KNOWLEDGE["esp32dev"]
    if "stm32" in board_lower:
        return CHIP_KNOWLEDGE["nucleo_f446re"]
    if "pico" in board_lower or "rp2" in board_lower:
        return CHIP_KNOWLEDGE["pico"]
    if "nrf" in board_lower:
        return CHIP_KNOWLEDGE["nrf52840_dk"]

    return "No chip-specific context available. Generate code using standard Arduino API."


def get_all_supported_chips() -> list[dict]:
    """Return list of all supported chip families with metadata."""
    return [
        {"id": "esp32dev", "family": "ESP32", "core": "Xtensa LX6", "speed": "240 MHz", "flash": "4 MB"},
        {"id": "esp32-s3", "family": "ESP32-S3", "core": "Xtensa LX7", "speed": "240 MHz", "flash": "8 MB"},
        {"id": "esp32-c3", "family": "ESP32-C3", "core": "RISC-V", "speed": "160 MHz", "flash": "4 MB"},
        {"id": "stm32f4", "family": "STM32F4", "core": "Cortex-M4", "speed": "180 MHz", "flash": "512 KB"},
        {"id": "stm32h7", "family": "STM32H7", "core": "Cortex-M7", "speed": "480 MHz", "flash": "2 MB"},
        {"id": "rp2040", "family": "RP2040", "core": "Cortex-M0+", "speed": "133 MHz", "flash": "2 MB"},
        {"id": "nrf52840", "family": "nRF52840", "core": "Cortex-M4F", "speed": "64 MHz", "flash": "1 MB"},
    ]
