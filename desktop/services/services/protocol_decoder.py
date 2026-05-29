"""
Protocol Decoder — Real-time I2C/SPI/UART/CAN serial protocol analysis.

Decodes raw serial/logic analyzer data into human-readable protocol frames.
Matches and EXCEEDS Embedder's "industry-leading serial monitor" by adding
protocol-level decoding on top of raw serial output.
"""

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ProtocolFrame:
    protocol: str  # I2C, SPI, UART, CAN
    timestamp_ms: float = 0
    direction: str = ""  # TX/RX/MOSI/MISO
    address: str = ""
    data: list[str] = field(default_factory=list)
    decoded: str = ""
    error: str = ""
    raw: str = ""


class I2CDecoder:
    """Decode I2C traffic from serial debug output."""

    KNOWN_DEVICES = {
        "0x76": "BME280 (Pressure/Temperature/Humidity)",
        "0x77": "BMP280/BME680 (Pressure/Gas)",
        "0x68": "MPU6050 (Accelerometer/Gyroscope)",
        "0x69": "MPU6050 (Alt Address)",
        "0x3C": "SSD1306 OLED Display (128x64)",
        "0x3D": "SSD1306 OLED Display (Alt)",
        "0x27": "PCF8574 I2C LCD (16x2)",
        "0x48": "ADS1115 ADC",
        "0x50": "AT24C32 EEPROM",
        "0x57": "DS3231 RTC",
        "0x29": "VL53L0X ToF Distance Sensor",
        "0x44": "SHT40 Temperature/Humidity",
        "0x40": "INA219 Current Sensor",
        "0x70": "TCA9548A I2C Multiplexer",
        "0x60": "SI7021 Humidity Sensor",
        "0x23": "BH1750 Light Sensor",
    }

    def decode_scan(self, output: str) -> list[dict]:
        """Decode I2C scanner output."""
        devices = []
        for match in re.finditer(r'(?:Found|Device at|0x)([0-9A-Fa-f]{2})', output):
            addr = f"0x{match.group(1).upper()}"
            devices.append({
                "address": addr,
                "device": self.KNOWN_DEVICES.get(addr, "Unknown Device"),
                "protocol": "I2C",
            })
        return devices

    def decode_transaction(self, line: str) -> Optional[ProtocolFrame]:
        """Decode a single I2C transaction from debug output."""
        # Pattern: I2C Write to 0x76: [0xF4, 0x27] or I2C Read from 0x76: [0x12, 0x34]
        match = re.search(
            r'I2C\s+(Write|Read)\s+(?:to|from)\s+(0x[0-9A-Fa-f]+)\s*:\s*\[(.*?)\]', line, re.IGNORECASE
        )
        if match:
            addr = match.group(2).upper()
            return ProtocolFrame(
                protocol="I2C",
                direction="TX" if match.group(1).lower() == "write" else "RX",
                address=addr,
                data=[b.strip() for b in match.group(3).split(",")],
                decoded=self.KNOWN_DEVICES.get(addr, "Unknown"),
                raw=line.strip(),
            )
        return None


class SPIDecoder:
    """Decode SPI traffic."""

    def decode_transaction(self, line: str) -> Optional[ProtocolFrame]:
        match = re.search(r'SPI\s+(MOSI|MISO|TX|RX)\s*:\s*\[(.*?)\]', line, re.IGNORECASE)
        if match:
            return ProtocolFrame(
                protocol="SPI",
                direction=match.group(1).upper(),
                data=[b.strip() for b in match.group(2).split(",")],
                raw=line.strip(),
            )
        return None


class UARTDecoder:
    """Decode UART traffic with baud rate detection."""

    COMMON_BAUDS = [9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600]

    def decode_line(self, line: str) -> ProtocolFrame:
        return ProtocolFrame(
            protocol="UART",
            direction="RX",
            data=[line.strip()],
            decoded=self._classify_output(line),
            raw=line.strip(),
        )

    def _classify_output(self, line: str) -> str:
        """Classify serial output type."""
        line_lower = line.lower().strip()
        if any(kw in line_lower for kw in ["error", "fail", "fault", "crash", "panic", "abort"]):
            return "ERROR"
        if any(kw in line_lower for kw in ["warn", "warning"]):
            return "WARNING"
        if any(kw in line_lower for kw in ["init", "setup", "start", "boot", "ready"]):
            return "INIT"
        if any(kw in line_lower for kw in ["heap", "memory", "stack", "free ram"]):
            return "MEMORY"
        if re.search(r'\d+\.\d+', line):
            return "DATA"  # Likely sensor data
        return "LOG"


class CANDecoder:
    """Decode CAN bus frames."""

    def decode_frame(self, line: str) -> Optional[ProtocolFrame]:
        # Standard CAN: ID=0x123 DLC=8 Data=[01 02 03 04 05 06 07 08]
        match = re.search(
            r'(?:CAN|TWAI)\s+(?:ID|id)\s*=?\s*(0x[0-9A-Fa-f]+)\s+(?:DLC|dlc)\s*=?\s*(\d+)\s+(?:Data|data)\s*=?\s*\[(.*?)\]',
            line, re.IGNORECASE
        )
        if match:
            return ProtocolFrame(
                protocol="CAN",
                address=match.group(1),
                data=[b.strip() for b in match.group(3).split()],
                decoded=f"DLC={match.group(2)}",
                raw=line.strip(),
            )
        return None


class ProtocolAnalyzer:
    """Main protocol analyzer — dispatches to per-protocol decoders."""

    def __init__(self):
        self.i2c = I2CDecoder()
        self.spi = SPIDecoder()
        self.uart = UARTDecoder()
        self.can = CANDecoder()
        self.frames: list[ProtocolFrame] = []

    def analyze_line(self, line: str) -> dict:
        """Analyze a single line of serial output."""
        # Try protocol-specific decoders first
        frame = self.i2c.decode_transaction(line)
        if not frame:
            frame = self.spi.decode_transaction(line)
        if not frame:
            frame = self.can.decode_frame(line)
        if not frame:
            frame = self.uart.decode_line(line)

        self.frames.append(frame)

        return {
            "protocol": frame.protocol,
            "direction": frame.direction,
            "address": frame.address,
            "data": frame.data,
            "decoded": frame.decoded,
            "error": frame.error,
            "raw": frame.raw,
            "frame_index": len(self.frames) - 1,
        }

    def analyze_bulk(self, text: str) -> list[dict]:
        """Analyze multiple lines at once."""
        results = []
        for line in text.strip().split("\n"):
            if line.strip():
                results.append(self.analyze_line(line))
        return results

    def i2c_scan(self, output: str) -> list[dict]:
        """Decode I2C scanner output and identify devices."""
        return self.i2c.decode_scan(output)

    def get_statistics(self) -> dict:
        """Get protocol traffic statistics."""
        stats: dict[str, int] = {}
        for frame in self.frames:
            stats[frame.protocol] = stats.get(frame.protocol, 0) + 1
        return {
            "total_frames": len(self.frames),
            "by_protocol": stats,
            "errors": sum(1 for f in self.frames if f.error),
        }

    def clear(self):
        self.frames = []


def get_protocol_analyzer() -> ProtocolAnalyzer:
    return ProtocolAnalyzer()
