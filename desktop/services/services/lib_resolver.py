"""
PlatformIO Library Auto-Resolver — scans generated firmware code for
#include statements and automatically adds lib_deps to platformio.ini.

Also provides a verification pipeline that compiles firmware and
optionally runs Wokwi simulation to validate correctness.
"""

import os
import re
import json
import asyncio
from typing import Optional

from agents.library_registry import LIBRARY_REGISTRY, get_platformio_deps


# Map common #include patterns to PlatformIO lib_deps
INCLUDE_TO_LIBDEPS: dict[str, str] = {
    "Adafruit_BME280.h": "adafruit/Adafruit BME280 Library@^2.2.4",
    "Adafruit_BMP280.h": "adafruit/Adafruit BMP280 Library@^2.6.8",
    "Adafruit_Sensor.h": "adafruit/Adafruit Unified Sensor@^1.1.14",
    "DHT.h": "adafruit/DHT sensor library@^1.4.6",
    "BH1750.h": "claws/BH1750@^1.3.0",
    "Adafruit_MPU6050.h": "adafruit/Adafruit MPU6050@^2.2.6",
    "Adafruit_ADS1X15.h": "adafruit/Adafruit ADS1X15@^2.5.0",
    "Adafruit_INA219.h": "adafruit/Adafruit INA219@^1.2.2",
    "VL53L0X.h": "pololu/VL53L0X@^1.3.1",
    "PubSubClient.h": "knolleary/PubSubClient@^2.8",
    "ESP32Servo.h": "madhephaestus/ESP32Servo@^3.0.5",
    "Adafruit_SSD1306.h": "adafruit/Adafruit SSD1306@^2.5.9",
    "Adafruit_GFX.h": "adafruit/Adafruit GFX Library@^1.11.9",
    "TFT_eSPI.h": "bodmer/TFT_eSPI@^2.5.43",
    "lvgl.h": "lvgl/lvgl@^8.3.11",
    "ArduinoJson.h": "bblanchon/ArduinoJson@^7.0.4",
    "WebSocketsClient.h": "links2004/WebSockets@^2.4.1",
    "NTPClient.h": "arduino-libraries/NTPClient@^3.2.1",
    "Preferences.h": None,  # Built-in ESP32
    "WiFi.h": None,
    "Wire.h": None,
    "SPI.h": None,
    "SPIFFS.h": None,
    "FS.h": None,
    "HTTPClient.h": None,
    "Update.h": None,
    "ESPmDNS.h": None,
    "driver/i2s.h": None,
    "mbedtls/aes.h": None,
    "esp_system.h": None,
    "freertos/FreeRTOS.h": None,
    "freertos/task.h": None,
    "freertos/semphr.h": None,
    "freertos/queue.h": None,
    "freertos/event_groups.h": None,
    "freertos/timers.h": None,
}


def scan_includes(source_files: list[str]) -> set[str]:
    """Scan C++ source files for #include statements."""
    includes = set()
    pattern = re.compile(r'#include\s*[<"]([^>"]+)[>"]')

    for filepath in source_files:
        if not os.path.exists(filepath):
            continue
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    match = pattern.search(line)
                    if match:
                        includes.add(match.group(1))
        except Exception:
            pass

    return includes


def resolve_lib_deps(includes: set[str]) -> list[str]:
    """Convert #include names to PlatformIO lib_deps entries."""
    deps = set()

    for inc in includes:
        # Direct lookup
        if inc in INCLUDE_TO_LIBDEPS:
            dep = INCLUDE_TO_LIBDEPS[inc]
            if dep:  # Skip None (built-in)
                deps.add(dep)
        else:
            # Try partial match from library registry
            for lib_name, info in LIBRARY_REGISTRY.items():
                lib_include = info.get("include", "")
                if inc in lib_include:
                    pio_dep = info.get("platformio_lib", "")
                    if pio_dep and not pio_dep.startswith("//"):
                        deps.add(pio_dep)
                    break

    return sorted(deps)


def update_platformio_ini(project_dir: str, lib_deps: list[str]) -> bool:
    """Update platformio.ini with resolved lib_deps."""
    ini_path = os.path.join(project_dir, "firmware", "platformio.ini")
    if not os.path.exists(ini_path):
        return False

    try:
        with open(ini_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check if lib_deps section exists
        if "lib_deps" in content:
            # Parse existing lib_deps
            existing = set()
            in_deps = False
            lines = content.split("\n")
            new_lines = []
            for line in lines:
                if "lib_deps" in line and "=" in line:
                    in_deps = True
                    new_lines.append(line)
                    # Add the value on the same line if present
                    after_eq = line.split("=", 1)[1].strip()
                    if after_eq:
                        existing.add(after_eq)
                    continue
                elif in_deps and line.strip().startswith(("  ", "\t")) and line.strip():
                    existing.add(line.strip())
                    new_lines.append(line)
                    continue
                elif in_deps and (not line.strip() or not line.startswith((" ", "\t"))):
                    # End of lib_deps section — inject new deps before continuing
                    in_deps = False
                    for dep in lib_deps:
                        if dep not in existing:
                            new_lines.append(f"    {dep}")
                            existing.add(dep)
                    new_lines.append(line)
                    continue
                else:
                    new_lines.append(line)

            # If still in_deps at end of file
            if in_deps:
                for dep in lib_deps:
                    if dep not in existing:
                        new_lines.append(f"    {dep}")

            content = "\n".join(new_lines)
        else:
            # No lib_deps section — add one
            deps_section = "\nlib_deps =\n" + "\n".join(f"    {dep}" for dep in lib_deps) + "\n"
            content += deps_section

        with open(ini_path, "w", encoding="utf-8") as f:
            f.write(content)

        return True
    except Exception as e:
        print(f"[LibResolver] Error updating platformio.ini: {e}")
        return False


async def resolve_and_update(project_dir: str) -> dict:
    """
    Scan project source files, resolve libraries, update platformio.ini.

    Returns:
        {"includes": [...], "lib_deps": [...], "updated": bool}
    """
    firmware_dir = os.path.join(project_dir, "firmware")
    src_dir = os.path.join(firmware_dir, "src")
    include_dir = os.path.join(firmware_dir, "include")

    # Collect all source files
    source_files = []
    for search_dir in [src_dir, include_dir]:
        if os.path.isdir(search_dir):
            for fname in os.listdir(search_dir):
                if fname.endswith((".cpp", ".h", ".c", ".ino")):
                    source_files.append(os.path.join(search_dir, fname))

    if not source_files:
        return {"includes": [], "lib_deps": [], "updated": False}

    # Scan includes
    includes = scan_includes(source_files)

    # Resolve to PlatformIO libs
    lib_deps = resolve_lib_deps(includes)

    # Update platformio.ini
    updated = update_platformio_ini(project_dir, lib_deps) if lib_deps else False

    print(f"[LibResolver] Found {len(includes)} includes -> {len(lib_deps)} lib_deps (updated={updated})")

    return {
        "includes": sorted(includes),
        "lib_deps": lib_deps,
        "updated": updated,
    }
