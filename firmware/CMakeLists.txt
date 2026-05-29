cmake_minimum_required(VERSION 3.16)

# ═══════════════════════════════════════════════════════════════════════════
# Parakram Universal Factory Firmware — ESP32-S3 N16R8
# Vidyuthlabs (c) 2025
#
# Board:    S3-PRO (ESP32-S3-WROOM-1, 16 MB flash, 8 MB OPI PSRAM)
# Features: Bytecode VM (48 ops), 67 drivers, NimBLE, WiFi, OTA,
#           DumbDisplay, I2C auto-detect, board authentication,
#           Secure Boot v2 ready, flash encryption ready
# ═══════════════════════════════════════════════════════════════════════════

set(EXTRA_COMPONENT_DIRS "components")

# Development mode: set to 0 for production (enforces board auth + eFuse lock)
set(PARAKRAM_DEV_MODE 1 CACHE STRING "Development mode (1=dev, 0=production)")
add_compile_definitions(PARAKRAM_DEV_MODE=${PARAKRAM_DEV_MODE})

include($ENV{IDF_PATH}/tools/cmake/project.cmake)

project(parakram_firmware VERSION 1.0.0)
