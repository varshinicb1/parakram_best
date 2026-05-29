"""AST-based block extraction from C source files."""

import re
from dataclasses import dataclass, field
from pathlib import Path

from config import RAW_DIR, MIN_BLOCK_LINES, MAX_BLOCK_LINES, SUPPORTED_EXTENSIONS


@dataclass
class CodeBlock:
    """A single extracted code block."""
    source_file: str
    function_name: str
    signature: str
    body: str
    line_start: int
    line_end: int
    includes: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    @property
    def line_count(self) -> int:
        return self.line_end - self.line_start + 1


# Regex to match C function definitions (simplified but effective)
FUNC_PATTERN = re.compile(
    r'^(\w[\w\s\*]+?)\s+(\w+)\s*\(([^)]*)\)\s*\{',
    re.MULTILINE
)

INCLUDE_PATTERN = re.compile(r'#include\s+[<"]([^>"]+)[>"]')


def extract_functions_from_file(filepath: Path) -> list[CodeBlock]:
    """Extract all function definitions from a single C file."""
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []

    lines = content.split("\n")
    includes = INCLUDE_PATTERN.findall(content)
    blocks: list[CodeBlock] = []

    for match in FUNC_PATTERN.finditer(content):
        return_type = match.group(1).strip()
        func_name = match.group(2)
        params = match.group(3).strip()
        start_pos = match.start()

        # Skip if it's a forward declaration or macro
        if func_name.startswith("__") or func_name.isupper():
            continue

        # Find matching closing brace
        line_start = content[:start_pos].count("\n") + 1
        brace_depth = 0
        in_body = False
        line_end = line_start

        for i, line in enumerate(lines[line_start - 1:], start=line_start):
            for ch in line:
                if ch == "{":
                    brace_depth += 1
                    in_body = True
                elif ch == "}":
                    brace_depth -= 1
            if in_body and brace_depth == 0:
                line_end = i
                break

        body = "\n".join(lines[line_start - 1:line_end])
        block_lines = line_end - line_start + 1

        if block_lines < MIN_BLOCK_LINES or block_lines > MAX_BLOCK_LINES:
            continue

        signature = f"{return_type} {func_name}({params})"

        # Auto-tag based on content
        tags = _infer_tags(func_name, body)

        blocks.append(CodeBlock(
            source_file=str(filepath.relative_to(RAW_DIR)),
            function_name=func_name,
            signature=signature,
            body=body,
            line_start=line_start,
            line_end=line_end,
            includes=includes,
            tags=tags,
        ))

    return blocks


def _infer_tags(func_name: str, body: str) -> list[str]:
    """Infer semantic tags from function name and body."""
    tags: list[str] = []
    combined = (func_name + " " + body).lower()

    tag_patterns = {
        "gpio": ["gpio", "pin_set", "pin_get", "digital_write"],
        "i2c": ["i2c", "twi"],
        "spi": ["spi", "mosi", "miso", "sclk"],
        "uart": ["uart", "usart", "serial"],
        "adc": ["adc", "analog_read"],
        "dma": ["dma", "dma_channel"],
        "timer": ["timer", "tick", "systick"],
        "interrupt": ["irq", "isr", "nvic", "interrupt"],
        "rtos": ["freertos", "task", "queue", "semaphore", "mutex"],
        "usb": ["usb", "uvc", "hid", "cdc"],
        "wifi": ["wifi", "wlan", "tcpip"],
        "ble": ["ble", "bluetooth", "gatt"],
        "display": ["lcd", "oled", "tft", "display", "ssd1306"],
        "sensor": ["sensor", "bme", "bmp", "mpu", "temp"],
        "flash": ["flash", "nvm", "eeprom"],
        "crypto": ["aes", "sha", "rsa", "encrypt", "hash"],
    }

    for tag, patterns in tag_patterns.items():
        if any(p in combined for p in patterns):
            tags.append(tag)

    return tags


def extract_all_blocks() -> dict[str, int]:
    """Extract blocks from all source files in RAW_DIR."""
    total_files = 0
    total_blocks = 0

    for ext in SUPPORTED_EXTENSIONS:
        for filepath in RAW_DIR.rglob(f"*{ext}"):
            blocks = extract_functions_from_file(filepath)
            total_files += 1
            total_blocks += len(blocks)

    return {"total_files": total_files, "total_blocks": total_blocks}
