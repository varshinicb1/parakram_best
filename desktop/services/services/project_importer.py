"""
Project Importer — Import existing Arduino/PlatformIO projects.

Parses source files, identifies blocks, libraries, and board,
then reverse-engineers a Parakram block graph from existing code.

Also supports diff-based editing: modify a single block without
regenerating the entire project.
"""

import os
import re
import json
from typing import Optional
from dataclasses import dataclass, field

from services.lib_resolver import scan_includes, resolve_lib_deps
from agents.library_registry import LIBRARY_REGISTRY


@dataclass
class ImportedBlock:
    """A block reverse-engineered from existing code."""
    id: str
    name: str
    category: str
    library: str
    setup_function: str = ""
    loop_function: str = ""
    source_file: str = ""
    header_file: str = ""
    pins: dict = field(default_factory=dict)
    i2c_address: str = ""


class ProjectImporter:
    """Import and understand existing Arduino/PlatformIO projects."""

    # Map common library includes to block categories
    INCLUDE_TO_CATEGORY = {
        "DHT.h": ("sensor", "DHT22"),
        "Adafruit_BME280.h": ("sensor", "BME280"),
        "Adafruit_BMP280.h": ("sensor", "BMP280"),
        "Adafruit_MPU6050.h": ("sensor", "MPU6050"),
        "BH1750.h": ("sensor", "BH1750"),
        "Adafruit_ADS1X15.h": ("sensor", "ADS1115"),
        "Adafruit_INA219.h": ("sensor", "INA219"),
        "VL53L0X.h": ("sensor", "VL53L0X"),
        "Adafruit_SSD1306.h": ("display", "SSD1306 OLED"),
        "TFT_eSPI.h": ("display", "TFT Display"),
        "PubSubClient.h": ("communication", "MQTT Client"),
        "WiFi.h": ("communication", "WiFi Station"),
        "ESP32Servo.h": ("actuator", "Servo Motor"),
        "driver/i2s.h": ("audio", "I2S Audio"),
    }

    def import_project(self, project_dir: str) -> dict:
        """
        Analyze an existing project and extract structure.

        Returns:
            {
                "board": str,
                "blocks": [ImportedBlock, ...],
                "libraries": [str, ...],
                "includes": [str, ...],
                "source_files": [str, ...],
                "platformio_ini": str,
            }
        """
        firmware_dir = project_dir
        # Try common structures
        for sub in ["firmware", "src", ""]:
            test_dir = os.path.join(project_dir, sub) if sub else project_dir
            if os.path.exists(os.path.join(test_dir, "platformio.ini")):
                firmware_dir = test_dir
                break

        # Find source files
        source_files = []
        for root, dirs, files in os.walk(firmware_dir):
            # Skip PlatformIO build artifacts
            if ".pio" in root or "node_modules" in root:
                continue
            for fname in files:
                if fname.endswith((".cpp", ".c", ".h", ".ino")):
                    source_files.append(os.path.join(root, fname))

        if not source_files:
            return {"error": "No source files found"}

        # Scan includes
        includes = scan_includes(source_files)
        lib_deps = resolve_lib_deps(includes)

        # Detect board from platformio.ini
        board = self._detect_board(firmware_dir)

        # Reverse-engineer blocks from source
        blocks = self._extract_blocks(source_files, includes)

        # Read platformio.ini if exists
        ini_path = os.path.join(firmware_dir, "platformio.ini")
        ini_content = ""
        if os.path.exists(ini_path):
            with open(ini_path, "r") as f:
                ini_content = f.read()

        return {
            "board": board,
            "blocks": [self._block_to_dict(b) for b in blocks],
            "libraries": lib_deps,
            "includes": sorted(includes),
            "source_files": [os.path.relpath(f, project_dir) for f in source_files],
            "platformio_ini": ini_content,
        }

    def _detect_board(self, firmware_dir: str) -> str:
        """Detect board from platformio.ini."""
        ini_path = os.path.join(firmware_dir, "platformio.ini")
        if os.path.exists(ini_path):
            with open(ini_path, "r") as f:
                content = f.read()
            match = re.search(r'board\s*=\s*(\S+)', content)
            if match:
                return match.group(1)
        return "esp32dev"

    def _extract_blocks(
        self, source_files: list[str], includes: set[str]
    ) -> list[ImportedBlock]:
        """Reverse-engineer blocks from source code."""
        blocks = []

        for inc in includes:
            if inc in self.INCLUDE_TO_CATEGORY:
                category, name = self.INCLUDE_TO_CATEGORY[inc]
                block_id = name.lower().replace(" ", "_")

                block = ImportedBlock(
                    id=block_id,
                    name=name,
                    category=category,
                    library=inc,
                )

                # Find which source files use this library
                for fpath in source_files:
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                            content = f.read()
                        if inc in content:
                            if fpath.endswith(".h"):
                                block.header_file = fpath
                            else:
                                block.source_file = fpath

                            # Extract pin assignments
                            pin_matches = re.findall(
                                r'(?:#define\s+\w*PIN\w*\s+(\d+)|'
                                r'(?:pin|PIN|gpio)\s*[=:]\s*(\d+))',
                                content
                            )
                            for match in pin_matches:
                                pin = match[0] or match[1]
                                if pin:
                                    block.pins[f"pin_{len(block.pins)}"] = int(pin)

                            # Extract I2C address
                            addr_match = re.search(r'0x[0-9A-Fa-f]{2}', content)
                            if addr_match:
                                block.i2c_address = addr_match.group(0)

                    except Exception:
                        pass

                blocks.append(block)

        return blocks

    def _block_to_dict(self, block: ImportedBlock) -> dict:
        return {
            "id": block.id,
            "name": block.name,
            "category": block.category,
            "library": block.library,
            "source_file": block.source_file,
            "header_file": block.header_file,
            "pins": block.pins,
            "i2c_address": block.i2c_address,
        }


class DiffEditor:
    """
    Modify a single block without regenerating the entire project.

    Preserves user-written code sections marked with:
    // USER CODE BEGIN
    ... user code ...
    // USER CODE END
    """

    def apply_block_update(
        self,
        project_dir: str,
        block_id: str,
        new_header: str,
        new_source: str,
    ) -> dict:
        """
        Replace a single block's code while preserving user sections.

        Returns: {"updated_files": [...], "preserved_sections": int}
        """
        safe_name = block_id.lower().replace(" ", "_").replace("-", "_")
        firmware_dir = os.path.join(project_dir, "firmware")

        updated = []
        preserved = 0

        # Update header
        hdr_path = os.path.join(firmware_dir, "include", f"{safe_name}.h")
        if os.path.exists(hdr_path) and new_header:
            old = self._read_file(hdr_path)
            merged, sections = self._merge_preserving_user(old, new_header)
            preserved += sections
            self._write_file(hdr_path, merged)
            updated.append(hdr_path)

        # Update source
        src_path = os.path.join(firmware_dir, "src", f"{safe_name}.cpp")
        if os.path.exists(src_path) and new_source:
            old = self._read_file(src_path)
            merged, sections = self._merge_preserving_user(old, new_source)
            preserved += sections
            self._write_file(src_path, merged)
            updated.append(src_path)

        return {
            "updated_files": updated,
            "preserved_sections": preserved,
        }

    def _merge_preserving_user(self, old: str, new: str) -> tuple[str, int]:
        """
        Merge new code while preserving USER CODE sections from old.
        Returns (merged_code, num_preserved_sections).
        """
        # Normalize line endings
        old_norm = old.replace('\r\n', '\n')
        new_norm = new.replace('\r\n', '\n')

        # Extract user sections from old code
        user_sections = {}
        user_pattern = re.compile(
            r'// USER CODE BEGIN (\w+)\s*\n(.*?)// USER CODE END \1',
            re.DOTALL
        )
        for match in user_pattern.finditer(old_norm):
            section_name = match.group(1)
            user_code = match.group(2)
            user_sections[section_name] = user_code

        if not user_sections:
            return new, 0

        # Insert user sections into new code
        merged = new_norm
        preserved = 0
        for name, code in user_sections.items():
            # Match placeholder with flexible whitespace
            placeholder_pattern = re.compile(
                rf'// USER CODE BEGIN {name}\s*\n\s*// USER CODE END {name}'
            )
            replacement = f"// USER CODE BEGIN {name}\n{code}// USER CODE END {name}"
            if placeholder_pattern.search(merged):
                merged = placeholder_pattern.sub(replacement, merged, count=1)
                preserved += 1

        return merged, preserved

    def _read_file(self, path: str) -> str:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return ""

    def _write_file(self, path: str, content: str):
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
