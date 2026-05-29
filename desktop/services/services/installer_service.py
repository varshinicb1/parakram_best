"""
Toolchain & Library Auto-Installer Service.
Detects OS, downloads, and installs PlatformIO, ESP-IDF, Arduino CLI etc.
Also auto-resolves library dependencies from generated firmware code.
"""

import os
import re
import json
import asyncio
import platform
import subprocess
from pathlib import Path
from typing import Optional


class ToolchainInstaller:
    """Manages installation of embedded development toolchains."""

    TOOLCHAINS = {
        "platformio": {
            "name": "PlatformIO Core",
            "check_cmd": ["pio", "--version"],
            "install": {
                "windows": "pip install -U platformio",
                "linux": "pip install -U platformio",
                "darwin": "pip install -U platformio",
            },
            "post_install": "pio platform install espressif32",
        },
        "arduino-cli": {
            "name": "Arduino CLI",
            "check_cmd": ["arduino-cli", "version"],
            "install": {
                "windows": 'powershell -Command "Invoke-WebRequest -Uri https://downloads.arduino.cc/arduino-cli/arduino-cli_latest_Windows_64bit.zip -OutFile arduino-cli.zip; Expand-Archive arduino-cli.zip -DestinationPath $env:USERPROFILE\\arduino-cli"',
                "linux": "curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | sh",
                "darwin": "brew install arduino-cli",
            },
        },
        "esp-idf": {
            "name": "ESP-IDF",
            "check_cmd": ["idf.py", "--version"],
            "install": {
                "windows": "pip install esptool && git clone --recursive https://github.com/espressif/esp-idf.git %USERPROFILE%\\esp-idf",
                "linux": "pip install esptool && git clone --recursive https://github.com/espressif/esp-idf.git ~/esp-idf && ~/esp-idf/install.sh",
                "darwin": "pip install esptool && git clone --recursive https://github.com/espressif/esp-idf.git ~/esp-idf && ~/esp-idf/install.sh",
            },
        },
    }

    @staticmethod
    def get_os() -> str:
        system = platform.system().lower()
        if system == "windows":
            return "windows"
        elif system == "darwin":
            return "darwin"
        return "linux"

    @classmethod
    async def check_installed(cls, toolchain_id: str) -> dict:
        """Check if a toolchain is installed."""
        tc = cls.TOOLCHAINS.get(toolchain_id)
        if not tc:
            return {"id": toolchain_id, "installed": False, "error": "Unknown toolchain"}

        try:
            proc = await asyncio.create_subprocess_exec(
                *tc["check_cmd"],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            version = stdout.decode().strip() if proc.returncode == 0 else ""
            return {
                "id": toolchain_id,
                "name": tc["name"],
                "installed": proc.returncode == 0,
                "version": version,
            }
        except FileNotFoundError:
            return {"id": toolchain_id, "name": tc["name"], "installed": False}

    @classmethod
    async def install(cls, toolchain_id: str) -> dict:
        """Install a toolchain."""
        tc = cls.TOOLCHAINS.get(toolchain_id)
        if not tc:
            return {"error": f"Unknown toolchain: {toolchain_id}"}

        os_type = cls.get_os()
        cmd = tc["install"].get(os_type, "")
        if not cmd:
            return {"error": f"No install command for OS: {os_type}"}

        try:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            result = {
                "id": toolchain_id,
                "name": tc["name"],
                "success": proc.returncode == 0,
                "stdout": stdout.decode()[-500:],
                "stderr": stderr.decode()[-500:] if proc.returncode != 0 else "",
            }

            # Run post-install if available
            if proc.returncode == 0 and "post_install" in tc:
                post_proc = await asyncio.create_subprocess_shell(
                    tc["post_install"],
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await post_proc.communicate()

            return result
        except Exception as e:
            return {"id": toolchain_id, "error": str(e)}

    @classmethod
    async def check_all(cls) -> list[dict]:
        """Check status of all toolchains."""
        results = await asyncio.gather(
            *[cls.check_installed(tid) for tid in cls.TOOLCHAINS]
        )
        return list(results)


class LibraryAutoInstaller:
    """Auto-detects and installs Arduino/PlatformIO libraries from code."""

    # Map #include directives to PlatformIO library names
    INCLUDE_TO_LIB = {
        "Adafruit_BME280.h": "adafruit/Adafruit BME280 Library",
        "Adafruit_NeoPixel.h": "adafruit/Adafruit NeoPixel",
        "Adafruit_SSD1306.h": "adafruit/Adafruit SSD1306",
        "Adafruit_GFX.h": "adafruit/Adafruit GFX Library",
        "PubSubClient.h": "knolleary/PubSubClient",
        "ArduinoJson.h": "bblanchon/ArduinoJson",
        "FastLED.h": "fastled/FastLED",
        "TFT_eSPI.h": "bodmer/TFT_eSPI",
        "ESPAsyncWebServer.h": "me-no-dev/ESPAsyncWebServer",
        "AsyncTCP.h": "me-no-dev/AsyncTCP",
        "MPU6050.h": "electroniccats/MPU6050",
        "Wire.h": None,  # Built-in
        "SPI.h": None,   # Built-in
        "WiFi.h": None,  # Built-in, ESP32 framework
        "SPIFFS.h": None,  # Built-in
        "SD.h": None,    # Built-in
        "Servo.h": None,  # Built-in
    }

    @classmethod
    def detect_includes(cls, source_code: str) -> list[str]:
        """Extract #include directives from source code."""
        pattern = r'#include\s*[<"]([^>"]+)[>"]'
        includes = re.findall(pattern, source_code)
        return includes

    @classmethod
    def resolve_libraries(cls, source_code: str) -> dict:
        """Resolve library dependencies from code includes."""
        includes = cls.detect_includes(source_code)
        needed = []
        builtin = []
        unknown = []

        for inc in includes:
            basename = os.path.basename(inc)
            if basename in cls.INCLUDE_TO_LIB:
                lib = cls.INCLUDE_TO_LIB[basename]
                if lib is None:
                    builtin.append(basename)
                else:
                    needed.append({"include": basename, "library": lib})
            else:
                unknown.append(basename)

        return {
            "needed": needed,
            "builtin": builtin,
            "unknown": unknown,
        }

    @classmethod
    async def install_libraries(cls, project_dir: str, libraries: list[str]) -> dict:
        """Install libraries via PlatformIO."""
        results = []
        for lib in libraries:
            try:
                proc = await asyncio.create_subprocess_exec(
                    "pio", "pkg", "install", "-l", lib,
                    cwd=project_dir,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await proc.communicate()
                results.append({
                    "library": lib,
                    "success": proc.returncode == 0,
                    "message": stdout.decode()[-200:] if proc.returncode == 0 else stderr.decode()[-200:],
                })
            except Exception as e:
                results.append({"library": lib, "success": False, "error": str(e)})
        return {"installed": results}

    @classmethod
    async def auto_install_from_code(cls, project_dir: str, source_code: str) -> dict:
        """Auto-detect and install all needed libraries from code."""
        resolution = cls.resolve_libraries(source_code)
        if not resolution["needed"]:
            return {"message": "No external libraries needed", **resolution}

        lib_names = [item["library"] for item in resolution["needed"]]
        install_result = await cls.install_libraries(project_dir, lib_names)
        return {**resolution, **install_result}
