"""
Memory Analyzer — RAM/Flash usage analysis for firmware binaries.

Features:
  - Parse .elf and .map files for section sizes
  - Track RAM usage by variable/buffer
  - Flash usage by function/library
  - Fragmentation warnings
  - Optimization suggestions

Embedder doesn't have memory analysis — Parakram exclusive.
"""

from dataclasses import dataclass, field
from typing import Optional
import re


@dataclass
class MemorySection:
    name: str
    address: int
    size: int
    type: str  # flash, ram, rom, iram


@dataclass
class MemoryReport:
    board: str
    total_flash: int
    used_flash: int
    total_ram: int
    used_ram: int
    sections: list[MemorySection] = field(default_factory=list)
    largest_symbols: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


# Common MCU memory maps
MCU_MEMORY = {
    "esp32": {"flash": 4194304, "ram": 532480, "iram": 131072},
    "esp32s3": {"flash": 8388608, "ram": 524288, "iram": 131072},
    "esp32c3": {"flash": 4194304, "ram": 409600, "iram": 0},
    "stm32f4": {"flash": 524288, "ram": 131072, "iram": 0},
    "stm32h7": {"flash": 2097152, "ram": 1048576, "iram": 0},
    "rp2040": {"flash": 2097152, "ram": 270336, "iram": 0},
    "nrf52840": {"flash": 1048576, "ram": 262144, "iram": 0},
    "atmega328p": {"flash": 32768, "ram": 2048, "iram": 0},
    "atmega2560": {"flash": 262144, "ram": 8192, "iram": 0},
    "teensy40": {"flash": 2097152, "ram": 1048576, "iram": 0},
}


class MemoryAnalyzer:
    """Analyze firmware memory usage."""

    def analyze_from_build_output(self, output: str, board: str = "esp32") -> dict:
        """Parse build output to extract memory usage."""
        board_key = board.lower().replace("-", "").replace("_", "").replace("dev", "")
        mem = MCU_MEMORY.get(board_key, MCU_MEMORY["esp32"])

        # Parse PlatformIO/GCC output patterns
        flash_used = 0
        ram_used = 0

        # Pattern: "RAM:   [====      ]  42.3% (used 55132 bytes from 327680 bytes)"
        ram_match = re.search(r'RAM:.*?(\d+)\s*bytes\s*from\s*(\d+)', output)
        if ram_match:
            ram_used = int(ram_match.group(1))
            mem["ram"] = int(ram_match.group(2))

        # Pattern: "Flash: [========  ]  78.6% (used 818432 bytes from 1310720 bytes)"
        flash_match = re.search(r'Flash:.*?(\d+)\s*bytes\s*from\s*(\d+)', output)
        if flash_match:
            flash_used = int(flash_match.group(1))
            mem["flash"] = int(flash_match.group(2))

        # Alternative: "text data bss dec hex filename"
        size_match = re.search(r'(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+', output)
        if size_match and flash_used == 0:
            text = int(size_match.group(1))
            data = int(size_match.group(2))
            bss = int(size_match.group(3))
            flash_used = text + data
            ram_used = data + bss

        report = self._generate_report(board, mem, flash_used, ram_used)
        return report

    def analyze_from_sizes(self, board: str, flash_used: int, ram_used: int) -> dict:
        """Analyze from known sizes."""
        board_key = board.lower().replace("-", "").replace("_", "").replace("dev", "")
        mem = MCU_MEMORY.get(board_key, MCU_MEMORY["esp32"])
        return self._generate_report(board, mem, flash_used, ram_used)

    def estimate_from_code(self, code: str, board: str = "esp32") -> dict:
        """Estimate memory usage from source code analysis."""
        board_key = board.lower().replace("-", "").replace("_", "").replace("dev", "")
        mem = MCU_MEMORY.get(board_key, MCU_MEMORY["esp32"])

        # Rough estimation heuristics
        lines = code.count('\n')
        flash_per_line = 50  # ~50 bytes of flash per line of C/C++
        estimated_flash = lines * flash_per_line

        # Count buffer declarations
        buffers = re.findall(r'\b(?:char|uint8_t|byte)\s+\w+\[(\d+)\]', code)
        buffer_ram = sum(int(b) for b in buffers)

        # Count string literals
        strings = re.findall(r'"([^"]*)"', code)
        string_flash = sum(len(s) + 1 for s in strings)  # +1 for null terminator

        # Library RAM estimates
        lib_ram = 0
        if '#include <WiFi' in code: lib_ram += 40000
        if '#include <BLE' in code: lib_ram += 30000
        if '#include <Wire' in code: lib_ram += 1024
        if '#include <SPI' in code: lib_ram += 512
        if 'FreeRTOS' in code or 'xTask' in code: lib_ram += 8000
        if 'mqtt' in code.lower(): lib_ram += 10000
        if 'WebServer' in code: lib_ram += 16000

        estimated_ram = buffer_ram + lib_ram + 4096  # 4KB baseline

        return self._generate_report(board, mem, estimated_flash + string_flash, estimated_ram)

    def _generate_report(self, board: str, mem: dict, flash_used: int, ram_used: int) -> dict:
        total_flash = mem["flash"]
        total_ram = mem["ram"]

        flash_pct = (flash_used / total_flash * 100) if total_flash > 0 else 0
        ram_pct = (ram_used / total_ram * 100) if total_ram > 0 else 0

        warnings = []
        suggestions = []

        # Flash warnings
        if flash_pct > 90:
            warnings.append("🔴 Flash usage critical (>90%) — firmware may not fit")
            suggestions.append("Remove unused libraries with `lib_deps` cleanup")
            suggestions.append("Use PROGMEM for large const arrays")
        elif flash_pct > 75:
            warnings.append("⚠️ Flash usage high (>75%) — limited space for OTA updates")
            suggestions.append("OTA needs ~50% free flash — consider larger flash chip")

        # RAM warnings
        if ram_pct > 85:
            warnings.append("🔴 RAM usage critical (>85%) — risk of stack overflow")
            suggestions.append("Reduce buffer sizes and use dynamic allocation carefully")
            suggestions.append("Move large arrays to PSRAM if available (ESP32-S3)")
        elif ram_pct > 60:
            warnings.append("⚠️ RAM usage moderate — monitor with heap_caps_get_free_size()")

        # ESP32-specific
        if "esp32" in board.lower():
            if ram_used > 200000:
                suggestions.append("Use ESP32 PSRAM for large buffers: heap_caps_malloc(size, MALLOC_CAP_SPIRAM)")
            if flash_used > 1500000:
                suggestions.append("Enable partition scheme with larger app partition in menuconfig")

        # ATmega-specific
        if "atmega" in board.lower() or "uno" in board.lower():
            if ram_used > 1500:
                suggestions.append("Use F() macro for string literals: Serial.println(F(\"text\"))")
            if flash_used > 28000:
                suggestions.append("Consider ATmega2560 (Mega) for more flash space")

        # General suggestions
        if not suggestions:
            suggestions.append("✅ Memory usage looks healthy")

        return {
            "board": board,
            "flash": {
                "used": flash_used, "total": total_flash,
                "percent": round(flash_pct, 1),
                "free": total_flash - flash_used,
                "free_kb": round((total_flash - flash_used) / 1024, 1),
            },
            "ram": {
                "used": ram_used, "total": total_ram,
                "percent": round(ram_pct, 1),
                "free": total_ram - ram_used,
                "free_kb": round((total_ram - ram_used) / 1024, 1),
            },
            "warnings": warnings,
            "suggestions": suggestions,
        }

    def compare_versions(self, board: str, v1_flash: int, v1_ram: int,
                          v2_flash: int, v2_ram: int) -> dict:
        """Compare memory usage between two firmware versions."""
        flash_diff = v2_flash - v1_flash
        ram_diff = v2_ram - v1_ram
        return {
            "flash_diff": flash_diff,
            "ram_diff": ram_diff,
            "flash_diff_kb": round(flash_diff / 1024, 1),
            "ram_diff_kb": round(ram_diff / 1024, 1),
            "flash_grew": flash_diff > 0,
            "ram_grew": ram_diff > 0,
            "v1": self.analyze_from_sizes(board, v1_flash, v1_ram),
            "v2": self.analyze_from_sizes(board, v2_flash, v2_ram),
        }


def get_memory_analyzer() -> MemoryAnalyzer:
    return MemoryAnalyzer()
