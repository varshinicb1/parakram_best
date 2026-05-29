"""
Datasheet Parser — Extract hardware intelligence from PDF datasheets.

Parses uploaded PDF datasheets to extract:
  - Register maps (address, name, reset value, bit fields)
  - Pin tables (pin number → name → alternate functions)
  - Timing specifications (setup/hold times, clock frequencies)
  - Peripheral descriptions

Uses PyMuPDF (fitz) for text extraction + table detection.
Falls back to regex-based parsing when structured extraction fails.
"""

import re
import json
import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

# Try importing PyMuPDF — graceful fallback if not installed
try:
    import fitz  # PyMuPDF
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False


@dataclass
class RegisterField:
    name: str
    bits: str  # e.g., "7:0", "31:16"
    access: str = "RW"  # RW, RO, WO
    reset_value: str = "0"
    description: str = ""


@dataclass
class Register:
    name: str
    address: str  # hex, e.g., "0x40004000"
    offset: str = ""
    size: int = 32  # bits
    reset_value: str = "0x00000000"
    description: str = ""
    fields: list[RegisterField] = field(default_factory=list)


@dataclass
class PinInfo:
    number: str
    name: str
    type: str = "I/O"  # I/O, Power, GND
    alternate_functions: list[str] = field(default_factory=list)
    description: str = ""


@dataclass
class DatasheetKnowledge:
    chip_name: str = ""
    manufacturer: str = ""
    registers: list[Register] = field(default_factory=list)
    pins: list[PinInfo] = field(default_factory=list)
    peripherals: list[str] = field(default_factory=list)
    timing_specs: dict = field(default_factory=dict)
    raw_sections: dict[str, str] = field(default_factory=dict)
    source_file: str = ""
    page_count: int = 0


class DatasheetParser:
    """Parse PDF datasheets and extract hardware knowledge."""

    STORAGE_DIR = Path("./storage/datasheets")

    def __init__(self):
        self.STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    def parse_pdf(self, pdf_path: str) -> DatasheetKnowledge:
        """Parse a PDF datasheet and extract structured knowledge."""
        knowledge = DatasheetKnowledge(source_file=os.path.basename(pdf_path))

        if not HAS_FITZ:
            # Fallback: just store the path, will use file name for context
            knowledge.chip_name = self._guess_chip_from_filename(pdf_path)
            return knowledge

        try:
            doc = fitz.open(pdf_path)
            knowledge.page_count = len(doc)

            full_text = ""
            for page in doc:
                full_text += page.get_text() + "\n"

            # Extract chip name from first page
            knowledge.chip_name = self._extract_chip_name(full_text[:2000])
            knowledge.manufacturer = self._extract_manufacturer(full_text[:2000])

            # Extract sections
            knowledge.raw_sections = self._split_sections(full_text)

            # Extract registers
            knowledge.registers = self._extract_registers(full_text)

            # Extract pin table
            knowledge.pins = self._extract_pins(full_text)

            # Extract peripherals list
            knowledge.peripherals = self._extract_peripherals(full_text)

            # Extract timing specs
            knowledge.timing_specs = self._extract_timing(full_text)

            doc.close()
        except Exception as e:
            knowledge.raw_sections["error"] = str(e)

        return knowledge

    def _guess_chip_from_filename(self, path: str) -> str:
        name = os.path.basename(path).lower()
        for chip in ["esp32", "stm32", "nrf52", "rp2040", "atmega", "pic32"]:
            if chip in name:
                return chip.upper()
        return "Unknown"

    def _extract_chip_name(self, text: str) -> str:
        patterns = [
            r'(ESP32[-\w]*)',
            r'(STM32\w+)',
            r'(nRF\d+\w*)',
            r'(RP\d+)',
            r'(ATmega\d+\w*)',
            r'(PIC32\w+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return "Unknown"

    def _extract_manufacturer(self, text: str) -> str:
        manufacturers = {
            "espressif": "Espressif",
            "stmicroelectronics": "STMicroelectronics",
            "nordic": "Nordic Semiconductor",
            "raspberry pi": "Raspberry Pi",
            "microchip": "Microchip",
            "nxp": "NXP Semiconductors",
        }
        text_lower = text.lower()
        for key, name in manufacturers.items():
            if key in text_lower:
                return name
        return "Unknown"

    def _split_sections(self, text: str) -> dict[str, str]:
        """Split document into major sections."""
        sections = {}
        # Look for common section headers
        section_patterns = [
            r'(?:^|\n)(\d+\.?\s+(?:GPIO|General.Purpose|Pin|Register|Memory|Clock|Power|Peripheral|Timer|UART|SPI|I2C|ADC|DMA|Interrupt)[\w\s]*)',
        ]
        current_section = "overview"
        current_text = []

        for line in text.split("\n"):
            is_header = False
            for pattern in section_patterns:
                if re.match(pattern, line.strip(), re.IGNORECASE):
                    if current_text:
                        sections[current_section] = "\n".join(current_text[-500:])  # Cap per section
                    current_section = line.strip()[:80]
                    current_text = []
                    is_header = True
                    break
            if not is_header:
                current_text.append(line)

        if current_text:
            sections[current_section] = "\n".join(current_text[-500:])

        return sections

    def _extract_registers(self, text: str) -> list[Register]:
        """Extract register definitions from datasheet text."""
        registers = []
        # Common register table patterns
        patterns = [
            r'(0x[0-9A-Fa-f]+)\s+([\w_]+)\s+(?:R/?W?|RO|WO|RW)\s+(0x[0-9A-Fa-f]+)?\s*(.*?)(?:\n|$)',
            r'Offset:\s*(0x[0-9A-Fa-f]+)\s*.*?Name:\s*([\w_]+)',
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, text):
                groups = match.groups()
                reg = Register(
                    name=groups[1] if len(groups) > 1 else "UNKNOWN",
                    address=groups[0],
                    reset_value=groups[2] if len(groups) > 2 and groups[2] else "0x0",
                    description=groups[3].strip() if len(groups) > 3 and groups[3] else "",
                )
                if reg.name != "UNKNOWN" and len(registers) < 200:
                    registers.append(reg)

        return registers

    def _extract_pins(self, text: str) -> list[PinInfo]:
        """Extract pin definitions."""
        pins = []
        # Pattern for pin tables: Pin# | Name | Type | AF
        pin_pattern = r'(?:GPIO|Pin)\s*(\d+)\s+(\w+)\s+(?:I/?O|Input|Output|Power|GND)\s*(.*?)(?:\n|$)'
        for match in re.finditer(pin_pattern, text):
            pin = PinInfo(
                number=match.group(1),
                name=match.group(2),
                alternate_functions=match.group(3).strip().split(",") if match.group(3) else [],
            )
            if len(pins) < 100:
                pins.append(pin)
        return pins

    def _extract_peripherals(self, text: str) -> list[str]:
        """Extract list of available peripherals."""
        peripheral_keywords = [
            "GPIO", "UART", "USART", "SPI", "I2C", "I2S", "ADC", "DAC",
            "DMA", "Timer", "PWM", "CAN", "Ethernet", "USB", "SDIO",
            "RTC", "Watchdog", "LCD", "Camera", "Bluetooth", "WiFi",
        ]
        found = []
        text_upper = text.upper()
        for kw in peripheral_keywords:
            if kw.upper() in text_upper:
                found.append(kw)
        return found

    def _extract_timing(self, text: str) -> dict:
        """Extract timing specifications."""
        timing = {}
        # Clock frequencies
        freq_pattern = r'(\d+)\s*(?:MHz|GHz|kHz)\s+(?:clock|frequency|speed|crystal)'
        for match in re.finditer(freq_pattern, text, re.IGNORECASE):
            timing[f"clock_{match.group(1)}"] = match.group(0).strip()

        # Setup/hold times
        time_pattern = r'(t(?:SU|HD|CK|LOW|HIGH)[\w]*)\s*[=:]\s*(\d+\.?\d*)\s*(ns|µs|ms|us)'
        for match in re.finditer(time_pattern, text):
            timing[match.group(1)] = f"{match.group(2)} {match.group(3)}"

        return timing

    def knowledge_to_context(self, knowledge: DatasheetKnowledge) -> str:
        """Convert parsed knowledge to LLM-injectable context string."""
        lines = [f"## Datasheet: {knowledge.chip_name} ({knowledge.manufacturer})"]

        if knowledge.peripherals:
            lines.append(f"### Available Peripherals: {', '.join(knowledge.peripherals)}")

        if knowledge.registers:
            lines.append(f"\n### Key Registers ({len(knowledge.registers)} found)")
            for reg in knowledge.registers[:30]:  # Cap for context window
                lines.append(f"  {reg.address}: {reg.name} (reset: {reg.reset_value}) — {reg.description}")

        if knowledge.pins:
            lines.append(f"\n### Pin Map ({len(knowledge.pins)} pins)")
            for pin in knowledge.pins[:40]:
                af_str = f" (AF: {', '.join(pin.alternate_functions)})" if pin.alternate_functions else ""
                lines.append(f"  GPIO{pin.number}: {pin.name}{af_str}")

        if knowledge.timing_specs:
            lines.append("\n### Timing")
            for name, value in list(knowledge.timing_specs.items())[:10]:
                lines.append(f"  {name}: {value}")

        return "\n".join(lines)

    def save_knowledge(self, knowledge: DatasheetKnowledge) -> str:
        """Save parsed knowledge as JSON for future sessions."""
        out_path = self.STORAGE_DIR / f"{knowledge.chip_name.lower()}_knowledge.json"

        data = {
            "chip_name": knowledge.chip_name,
            "manufacturer": knowledge.manufacturer,
            "source_file": knowledge.source_file,
            "page_count": knowledge.page_count,
            "peripherals": knowledge.peripherals,
            "timing_specs": knowledge.timing_specs,
            "register_count": len(knowledge.registers),
            "pin_count": len(knowledge.pins),
            "registers": [
                {"name": r.name, "address": r.address, "reset": r.reset_value, "desc": r.description}
                for r in knowledge.registers[:100]
            ],
            "pins": [
                {"num": p.number, "name": p.name, "af": p.alternate_functions}
                for p in knowledge.pins[:60]
            ],
        }

        out_path.write_text(json.dumps(data, indent=2))
        return str(out_path)


# Singleton
_parser: Optional[DatasheetParser] = None

def get_datasheet_parser() -> DatasheetParser:
    global _parser
    if _parser is None:
        _parser = DatasheetParser()
    return _parser
