"""
Block Factory — Generates full golden block templates from compact definitions.

Instead of hand-writing 200+ blocks, define components compactly and let
the factory generate the full header/source/JSON.

Usage:
    from agents.block_factory import BlockFactory
    factory = BlockFactory()
    blocks = factory.generate_all()
    factory.write_all()
"""

import os, json, re


def _safe(block_id: str) -> str:
    """Convert block ID to safe C identifier."""
    return block_id.replace("-", "_").replace(".", "_")


def _make_header(block_id: str, funcs: list[tuple]) -> str:
    """Generate a .h header from function signatures."""
    guard = _safe(block_id).upper() + "_H"
    lines = [f"#ifndef {guard}", f"#define {guard}", '#include <Arduino.h>']
    for ret, name, params in funcs:
        p = ", ".join(f"{t} {n}" for t, n in params) if params else ""
        lines.append(f"{ret} {name}({p});")
    lines.append("#endif")
    return "\n".join(lines)


def _make_i2c_source(block_id: str, cfg: dict) -> str:
    """Generate source for I2C sensor blocks (most common pattern)."""
    s = _safe(block_id)
    lib_class = cfg["class"]
    addr = cfg.get("addr", "0x00")
    reads = cfg.get("reads", [])   # [("temperature", "readTemperature()", "float", "%.1f")]
    interval = cfg.get("interval", 2000)

    lines = [f'#include "{s}.h"', '#include <Wire.h>']
    for inc in cfg.get("includes", []):
        lines.append(f"#include <{inc}>")

    lines.append(f"static {lib_class} _dev;")
    for varname, _, vtype, _ in reads:
        lines.append(f"static {vtype} _{varname} = 0;")
    lines.append("static unsigned long _last = 0;")
    lines.append(f"void {s}_setup() {{")
    lines.append("  Wire.begin();")

    init = cfg.get("init", f"_dev.begin({addr})")
    lines.append(f"  if (!{init}) {{ Serial.println(\"[{s}] Init failed!\"); return; }}")
    for setup_line in cfg.get("setup_extra", []):
        lines.append(f"  {setup_line};")
    lines.append(f'  Serial.println("[{s}] OK");')
    lines.append("}")

    lines.append(f"void {s}_loop() {{")
    lines.append(f"  if (millis()-_last < {interval}) return;")
    lines.append("  _last = millis();")

    if cfg.get("perform_reading"):
        lines.append(f"  {cfg['perform_reading']};")

    for varname, read_expr, vtype, fmt in reads:
        lines.append(f"  _{varname} = {read_expr};")
    lines.append("}")

    for varname, _, vtype, _ in reads:
        fname = f"{s}_get_{varname}"
        lines.append(f"{vtype} {fname}() {{ return _{varname}; }}")

    return "\n".join(lines)


def _make_gpio_source(block_id: str, cfg: dict) -> str:
    """Generate source for simple GPIO blocks (digital/analog)."""
    s = _safe(block_id)
    pin = cfg.get("pin", 0)
    pin_name = cfg.get("pin_name", "PIN")
    mode = cfg.get("mode", "INPUT")
    reads = cfg.get("reads", [])
    interval = cfg.get("interval", 1000)

    lines = [f'#include "{s}.h"', '#include <Arduino.h>']
    lines.append(f"#define {pin_name} {pin}")

    for varname, _, vtype, _ in reads:
        lines.append(f"static {vtype} _{varname} = 0;")
    lines.append("static unsigned long _last = 0;")

    lines.append(f"void {s}_setup() {{")
    lines.append(f"  pinMode({pin_name}, {mode});")
    for setup_line in cfg.get("setup_extra", []):
        lines.append(f"  {setup_line};")
    lines.append(f'  Serial.println("[{s}] OK");')
    lines.append("}")

    lines.append(f"void {s}_loop() {{")
    lines.append(f"  if (millis()-_last < {interval}) return;")
    lines.append("  _last = millis();")
    for varname, read_expr, vtype, fmt in reads:
        lines.append(f"  _{varname} = {read_expr};")
    lines.append("}")

    for varname, _, vtype, _ in reads:
        fname = f"{s}_get_{varname}"
        lines.append(f"{vtype} {fname}() {{ return _{varname}; }}")

    return "\n".join(lines)


def _make_spi_source(block_id: str, cfg: dict) -> str:
    """Generate source for SPI-based blocks."""
    s = _safe(block_id)
    lines = [f'#include "{s}.h"', '#include <SPI.h>']
    for inc in cfg.get("includes", []):
        lines.append(f"#include <{inc}>")

    cs = cfg.get("cs_pin", 5)
    lines.append(f"#define CS_PIN {cs}")

    if cfg.get("custom_source"):
        lines.append(cfg["custom_source"])
    else:
        lines.append(f"void {s}_setup() {{ SPI.begin(); Serial.println(\"[{s}] OK\"); }}")
        lines.append(f"void {s}_loop() {{}}")

    return "\n".join(lines)


class BlockFactory:
    """Generates golden blocks from compact definitions."""

    def __init__(self):
        self.blocks = {}

    def add_i2c(self, block_id: str, name: str, lib_class: str,
                addr: str, includes: list, lib_deps: list,
                reads: list, interval: int = 2000,
                init: str = None, setup_extra: list = None,
                perform_reading: str = None,
                extra_funcs: list = None):
        """Add an I2C sensor/device block."""
        cfg = {
            "class": lib_class, "addr": addr, "includes": includes,
            "reads": reads, "interval": interval,
            "setup_extra": setup_extra or [],
            "perform_reading": perform_reading,
        }
        if init:
            cfg["init"] = init

        # Build function list for header
        s = _safe(block_id)
        funcs = [(f"void", f"{s}_setup", []), (f"void", f"{s}_loop", [])]
        for varname, _, vtype, _ in reads:
            funcs.append((vtype, f"{s}_get_{varname}", []))
        if extra_funcs:
            funcs.extend(extra_funcs)

        self.blocks[block_id] = {
            "id": block_id, "name": name, "category": "sensor",
            "libs": [f"{i}" for i in includes],
            "lib_deps": lib_deps,
            "pins": {"sda": 21, "scl": 22}, "bus": "I2C", "addr": addr,
            "header": _make_header(block_id, funcs),
            "source": _make_i2c_source(block_id, cfg),
        }

    def add_gpio(self, block_id: str, name: str, category: str,
                 pin: int, mode: str, reads: list = None,
                 lib_deps: list = None, interval: int = 1000,
                 pin_name: str = "PIN", setup_extra: list = None,
                 extra_funcs: list = None):
        """Add a GPIO-based block."""
        s = _safe(block_id)
        cfg = {
            "pin": pin, "pin_name": pin_name, "mode": mode,
            "reads": reads or [], "interval": interval,
            "setup_extra": setup_extra or [],
        }
        funcs = [("void", f"{s}_setup", []), ("void", f"{s}_loop", [])]
        for varname, _, vtype, _ in (reads or []):
            funcs.append((vtype, f"{s}_get_{varname}", []))
        if extra_funcs:
            funcs.extend(extra_funcs)

        self.blocks[block_id] = {
            "id": block_id, "name": name, "category": category,
            "libs": [], "lib_deps": lib_deps or [],
            "pins": {pin_name.lower(): pin},
            "header": _make_header(block_id, funcs),
            "source": _make_gpio_source(block_id, cfg),
        }

    def add_raw(self, block_id: str, name: str, category: str,
                libs: list, lib_deps: list, pins: dict,
                header: str, source: str, bus: str = "", addr: str = ""):
        """Add a block with fully custom header/source."""
        self.blocks[block_id] = {
            "id": block_id, "name": name, "category": category,
            "libs": libs, "lib_deps": lib_deps, "pins": pins,
            "bus": bus, "addr": addr,
            "header": header, "source": source,
        }

    def get_all(self) -> dict:
        """Get all blocks grouped by category."""
        result = {}
        for bid, block in self.blocks.items():
            cat = block["category"]
            if cat not in result:
                result[cat] = []
            result[cat].append(block)
        return result

    def get_count(self) -> int:
        return len(self.blocks)
