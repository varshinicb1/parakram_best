"""
Extension Manager — VS Code-style extension system for Parakram OS.

Extensions are folders in ~/.parakram/extensions/ with:
  manifest.json  — metadata + activation hooks
  main.py        — entry point (Python module)
  panel.tsx      — optional frontend panel (served statically)

Hook system:
  on_project_create   — when user creates a new project
  on_code_generate    — before/after firmware code generation
  on_compile          — before/after PlatformIO compile
  on_flash            — before/after flash to device
  on_serial_data      — on incoming serial data
  on_board_detect     — when a board is detected
  on_file_change      — when workspace files change
  contribute_blocks   — provide custom hardware blocks
  contribute_boards   — register new board definitions
"""

import os
import json
import importlib.util
import asyncio
import traceback
from pathlib import Path
from typing import Any, Callable, Optional
from dataclasses import dataclass, field


# ── Extension manifest schema ──────────────────────────────────

@dataclass
class ExtensionManifest:
    id: str
    name: str
    version: str
    description: str = ""
    author: str = ""
    icon: str = "puzzle"
    entry_point: str = "main.py"
    activates_on: list[str] = field(default_factory=lambda: ["*"])
    provides: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    settings_schema: dict = field(default_factory=dict)
    category: str = "general"  # board-support, sensor, protocol, tool, general


@dataclass
class Extension:
    manifest: ExtensionManifest
    path: Path
    enabled: bool = True
    loaded: bool = False
    module: Any = None
    error: Optional[str] = None


# ── Built-in extensions (ship with Parakram) ───────────────────

BUILTIN_EXTENSIONS = {
    "esp32-support": {
        "id": "esp32-support",
        "name": "ESP32 Board Support",
        "version": "2.0.0",
        "description": "Full ESP32/S3/C3 board support with WiFi, BLE, and peripheral drivers",
        "author": "Parakram",
        "icon": "cpu",
        "category": "board-support",
        "activates_on": ["on_board_detect", "contribute_boards", "contribute_blocks"],
        "provides": ["board:esp32dev", "board:esp32-s3", "board:esp32-c3"],
    },
    "stm32-support": {
        "id": "stm32-support",
        "name": "STM32 Board Support",
        "version": "2.0.0",
        "description": "STM32F4/H7/L4 support with HAL drivers and register-level access",
        "author": "Parakram",
        "icon": "cpu",
        "category": "board-support",
        "activates_on": ["on_board_detect", "contribute_boards"],
        "provides": ["board:stm32f4", "board:stm32h7", "board:stm32l4"],
    },
    "rp2040-support": {
        "id": "rp2040-support",
        "name": "RP2040/RP2350 Support",
        "version": "1.0.0",
        "description": "Raspberry Pi Pico / Pico 2 board support",
        "author": "Parakram",
        "icon": "cpu",
        "category": "board-support",
        "activates_on": ["on_board_detect", "contribute_boards"],
        "provides": ["board:rp2040", "board:rp2350"],
    },
    "sensor-drivers": {
        "id": "sensor-drivers",
        "name": "Sensor Driver Pack",
        "version": "2.0.0",
        "description": "Pre-built drivers: BME280, MPU6050, BMP390, SHT40, ADS1115, TCS34725, VL53L0X",
        "author": "Parakram",
        "icon": "thermometer",
        "category": "sensor",
        "activates_on": ["contribute_blocks"],
        "provides": ["block:bme280", "block:mpu6050", "block:bmp390", "block:sht40"],
    },
    "protocol-analyzers": {
        "id": "protocol-analyzers",
        "name": "Protocol Analyzers",
        "version": "1.0.0",
        "description": "I2C/SPI/UART/CAN bus protocol decoding and analysis tools",
        "author": "Parakram",
        "icon": "activity",
        "category": "protocol",
        "activates_on": ["on_serial_data"],
        "provides": ["tool:i2c-decode", "tool:spi-decode", "tool:uart-decode"],
    },
    "mqtt-integration": {
        "id": "mqtt-integration",
        "name": "MQTT Integration",
        "version": "1.0.0",
        "description": "MQTT broker connection, topic management, and message visualization",
        "author": "Parakram",
        "icon": "radio",
        "category": "protocol",
        "activates_on": ["on_code_generate", "contribute_blocks"],
        "provides": ["block:mqtt_client", "tool:mqtt-monitor"],
    },
    "ota-updater": {
        "id": "ota-updater",
        "name": "OTA Update Manager",
        "version": "1.0.0",
        "description": "Over-The-Air firmware update support with rollback",
        "author": "Parakram",
        "icon": "upload",
        "category": "tool",
        "activates_on": ["on_flash", "contribute_blocks"],
        "provides": ["block:ota_update", "tool:ota-server"],
    },
    "power-profiler": {
        "id": "power-profiler",
        "name": "Power Profiler",
        "version": "1.0.0",
        "description": "Deep sleep analysis, current draw estimation, battery life calculator",
        "author": "Parakram",
        "icon": "battery",
        "category": "tool",
        "activates_on": ["on_compile"],
        "provides": ["tool:power-analysis", "tool:sleep-optimizer"],
    },
}


# ── Extension Manager ──────────────────────────────────────────

class ExtensionManager:
    """Manages the lifecycle of Parakram extensions."""

    _instance: Optional["ExtensionManager"] = None

    def __init__(self):
        self.extensions_dir = Path.home() / ".parakram" / "extensions"
        self.extensions_dir.mkdir(parents=True, exist_ok=True)
        self.extensions: dict[str, Extension] = {}
        self.hooks: dict[str, list[Callable]] = {}
        self._settings_path = self.extensions_dir / "settings.json"
        self._settings: dict = {}
        self._load_settings()
        self._register_builtins()

    @classmethod
    def get_instance(cls) -> "ExtensionManager":
        if cls._instance is None:
            cls._instance = ExtensionManager()
        return cls._instance

    def _load_settings(self):
        if self._settings_path.exists():
            try:
                self._settings = json.loads(self._settings_path.read_text())
            except Exception:
                self._settings = {}

    def _save_settings(self):
        self._settings_path.write_text(json.dumps(self._settings, indent=2))

    def _register_builtins(self):
        """Register all built-in extensions."""
        for ext_id, manifest_data in BUILTIN_EXTENSIONS.items():
            manifest = ExtensionManifest(**manifest_data)
            enabled = self._settings.get(f"{ext_id}.enabled", True)
            self.extensions[ext_id] = Extension(
                manifest=manifest,
                path=self.extensions_dir / ext_id,
                enabled=enabled,
                loaded=True,  # built-ins are always "loaded"
            )

    def discover(self) -> list[dict]:
        """Discover user-installed extensions from disk."""
        for entry in self.extensions_dir.iterdir():
            if entry.is_dir() and (entry / "manifest.json").exists():
                ext_id = entry.name
                if ext_id not in self.extensions:
                    try:
                        manifest_data = json.loads((entry / "manifest.json").read_text())
                        manifest = ExtensionManifest(**manifest_data)
                        enabled = self._settings.get(f"{ext_id}.enabled", True)
                        self.extensions[ext_id] = Extension(
                            manifest=manifest, path=entry, enabled=enabled
                        )
                    except Exception as e:
                        self.extensions[ext_id] = Extension(
                            manifest=ExtensionManifest(id=ext_id, name=ext_id, version="?"),
                            path=entry, enabled=False, error=str(e),
                        )
        return self.list_all()

    def list_all(self) -> list[dict]:
        """List all extensions with status."""
        return [
            {
                "id": ext.manifest.id,
                "name": ext.manifest.name,
                "version": ext.manifest.version,
                "description": ext.manifest.description,
                "author": ext.manifest.author,
                "icon": ext.manifest.icon,
                "category": ext.manifest.category,
                "enabled": ext.enabled,
                "loaded": ext.loaded,
                "builtin": ext.manifest.id in BUILTIN_EXTENSIONS,
                "provides": ext.manifest.provides,
                "error": ext.error,
            }
            for ext in self.extensions.values()
        ]

    def enable(self, ext_id: str) -> bool:
        if ext_id in self.extensions:
            self.extensions[ext_id].enabled = True
            self._settings[f"{ext_id}.enabled"] = True
            self._save_settings()
            return True
        return False

    def disable(self, ext_id: str) -> bool:
        if ext_id in self.extensions:
            self.extensions[ext_id].enabled = False
            self._settings[f"{ext_id}.enabled"] = False
            self._save_settings()
            return True
        return False

    def load_extension(self, ext_id: str) -> bool:
        """Load a user extension's Python module."""
        ext = self.extensions.get(ext_id)
        if not ext or ext.loaded or ext.manifest.id in BUILTIN_EXTENSIONS:
            return False

        entry = ext.path / ext.manifest.entry_point
        if not entry.exists():
            ext.error = f"Entry point not found: {ext.manifest.entry_point}"
            return False

        try:
            spec = importlib.util.spec_from_file_location(f"parakram_ext.{ext_id}", str(entry))
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                ext.module = module
                ext.loaded = True
                ext.error = None

                # Register hooks
                for hook_name in ext.manifest.activates_on:
                    if hasattr(module, hook_name):
                        if hook_name not in self.hooks:
                            self.hooks[hook_name] = []
                        self.hooks[hook_name].append(getattr(module, hook_name))
                return True
        except Exception as e:
            ext.error = f"Load failed: {traceback.format_exc()}"
            return False

    async def fire_hook(self, hook_name: str, **kwargs) -> list[Any]:
        """Fire a hook and collect results from all registered handlers."""
        results = []
        for handler in self.hooks.get(hook_name, []):
            try:
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(**kwargs)
                else:
                    result = handler(**kwargs)
                if result is not None:
                    results.append(result)
            except Exception as e:
                results.append({"error": str(e), "handler": str(handler)})
        return results

    def install_from_dict(self, manifest_data: dict) -> str:
        """Install extension from manifest dict (creates folder + manifest.json)."""
        ext_id = manifest_data.get("id", "")
        if not ext_id:
            return "Missing extension ID"

        ext_dir = self.extensions_dir / ext_id
        ext_dir.mkdir(parents=True, exist_ok=True)
        (ext_dir / "manifest.json").write_text(json.dumps(manifest_data, indent=2))

        # Create stub entry point
        if not (ext_dir / manifest_data.get("entry_point", "main.py")).exists():
            (ext_dir / manifest_data.get("entry_point", "main.py")).write_text(
                f'"""\n{manifest_data.get("name", ext_id)} — Parakram Extension\n"""\n\n'
                f'def on_activate():\n    print(f"[{ext_id}] Extension activated")\n'
            )

        self.discover()
        return f"Installed: {ext_id}"

    def uninstall(self, ext_id: str) -> str:
        """Uninstall a user extension (can't uninstall builtins)."""
        if ext_id in BUILTIN_EXTENSIONS:
            return "Cannot uninstall built-in extension"

        ext = self.extensions.get(ext_id)
        if not ext:
            return "Extension not found"

        import shutil
        if ext.path.exists():
            shutil.rmtree(ext.path)

        del self.extensions[ext_id]
        return f"Uninstalled: {ext_id}"

    def get_marketplace(self) -> list[dict]:
        """Return available extensions from the marketplace (local registry for now)."""
        installed_ids = set(self.extensions.keys())
        marketplace = [
            {
                "id": "nrf52-support",
                "name": "nRF52 Board Support",
                "version": "1.0.0",
                "description": "Nordic nRF52840/nRF5340 BLE support with SoftDevice",
                "author": "Community",
                "category": "board-support",
                "downloads": 1250,
            },
            {
                "id": "lora-driver",
                "name": "LoRa/LoRaWAN Driver",
                "version": "1.0.0",
                "description": "SX1276/SX1262 LoRa driver with LoRaWAN OTAA/ABP",
                "author": "Community",
                "category": "protocol",
                "downloads": 890,
            },
            {
                "id": "display-pack",
                "name": "Display Driver Pack",
                "version": "1.0.0",
                "description": "SSD1306, ST7789, ILI9341, E-Paper display drivers with LVGL",
                "author": "Community",
                "category": "sensor",
                "downloads": 2100,
            },
            {
                "id": "motor-control",
                "name": "Motor Control Suite",
                "version": "1.0.0",
                "description": "DC motors, servos, steppers, H-bridge, PID control",
                "author": "Community",
                "category": "sensor",
                "downloads": 750,
            },
            {
                "id": "misra-checker",
                "name": "MISRA C:2012 Checker",
                "version": "0.5.0",
                "description": "Static analysis for MISRA C compliance in generated firmware",
                "author": "Parakram Labs",
                "category": "tool",
                "downloads": 420,
            },
        ]
        return [m for m in marketplace if m["id"] not in installed_ids]


def get_extension_manager() -> ExtensionManager:
    return ExtensionManager.get_instance()
