"""Upstream source definitions for the CodeLM corpus."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceRepo:
    name: str
    url: str
    ref: str
    tier: int
    license: str
    description: str
    shallow: bool = False


TIER_1_SOURCES = [
    SourceRepo("CMSIS_6", "https://github.com/ARM-software/CMSIS_6.git", "main", 1, "Apache-2.0", "ARM Cortex-M HAL"),
    SourceRepo("CMSIS-DSP", "https://github.com/ARM-software/CMSIS-DSP.git", "main", 1, "Apache-2.0", "SIMD signal processing"),
    SourceRepo("CMSIS-NN", "https://github.com/ARM-software/CMSIS-NN.git", "main", 1, "Apache-2.0", "Neural net inference kernels"),
    SourceRepo("FreeRTOS-Kernel", "https://github.com/FreeRTOS/FreeRTOS-Kernel.git", "V11.1.0", 1, "MIT", "RTOS kernel"),
]

TIER_2_SOURCES = [
    SourceRepo("STM32CubeF4", "https://github.com/STMicroelectronics/STM32CubeF4.git", "master", 2, "BSD-3-Clause", "STM32F4 HAL+LL", shallow=True),
    SourceRepo("STM32CubeH7", "https://github.com/STMicroelectronics/STM32CubeH7.git", "master", 2, "BSD-3-Clause", "STM32H7 HAL+LL", shallow=True),
    SourceRepo("STM32CubeWL", "https://github.com/STMicroelectronics/STM32CubeWL.git", "main", 2, "BSD-3-Clause", "STM32WL LoRa", shallow=True),
    SourceRepo("pico-sdk", "https://github.com/raspberrypi/pico-sdk.git", "2.0.0", 2, "BSD-3-Clause", "RP2040/RP2350 SDK"),
    SourceRepo("esp-idf", "https://github.com/espressif/esp-idf.git", "v5.3.2", 2, "Apache-2.0", "ESP32 SDK", shallow=True),
]

TIER_3_SOURCES = [
    SourceRepo("Arduino-core-avr", "https://github.com/arduino/ArduinoCore-avr.git", "master", 3, "LGPL-2.1", "Arduino AVR core"),
    SourceRepo("arduino-esp32", "https://github.com/espressif/arduino-esp32.git", "3.1.1", 3, "Apache-2.0", "Arduino ESP32 core"),
    SourceRepo("mbed-os", "https://github.com/ARMmbed/mbed-os.git", "master", 3, "Apache-2.0", "Mbed OS HAL", shallow=True),
    SourceRepo("tinyusb", "https://github.com/hathach/tinyusb.git", "0.16.0", 3, "MIT", "USB device/host stack"),
    SourceRepo("lwip", "https://github.com/lwip-tcpip/lwip.git", "STABLE-2_2_0_2", 3, "BSD-3-Clause", "Lightweight TCP/IP"),
    SourceRepo("littlefs", "https://github.com/littlefs-project/littlefs.git", "v2.9.3", 3, "BSD-3-Clause", "Flash filesystem"),
    SourceRepo("nanopb", "https://github.com/nanopb/nanopb.git", "0.4.9.1", 3, "Zlib", "Protobuf for embedded"),
]

ALL_SOURCES = TIER_1_SOURCES + TIER_2_SOURCES + TIER_3_SOURCES
