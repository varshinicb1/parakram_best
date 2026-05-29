"""
Serial Port Detection & Communication Service.

Uses pyserial to:
  - Detect connected USB/serial devices
  - Identify ESP32/STM32/RP2040 by VID:PID
  - Open serial monitors
  - Flash firmware via esptool
"""
import json
import asyncio

# Known USB VID:PID mappings for common dev boards
KNOWN_DEVICES = {
    ("10C4", "EA60"): {"name": "ESP32 DevKit V1", "board": "esp32dev", "chip": "esp32"},
    ("1A86", "7523"): {"name": "ESP32 (CH340)", "board": "esp32dev", "chip": "esp32"},
    ("303A", "1001"): {"name": "ESP32-S3 DevKit", "board": "esp32-s3-devkitc-1", "chip": "esp32s3"},
    ("303A", "0002"): {"name": "ESP32-S2", "board": "esp32-s2-saola-1", "chip": "esp32s2"},
    ("303A", "1002"): {"name": "ESP32-C3", "board": "esp32-c3-devkitm-1", "chip": "esp32c3"},
    ("0483", "5740"): {"name": "STM32 (ST-Link)", "board": "genericSTM32F411CE", "chip": "stm32"},
    ("0483", "374B"): {"name": "STM32 Nucleo", "board": "nucleo_f446re", "chip": "stm32"},
    ("2E8A", "0005"): {"name": "Raspberry Pi Pico", "board": "pico", "chip": "rp2040"},
    ("2E8A", "F00A"): {"name": "Raspberry Pi Pico W", "board": "rpipicow", "chip": "rp2040"},
    ("2341", "0043"): {"name": "Arduino Uno", "board": "uno", "chip": "atmega328p"},
    ("2341", "8036"): {"name": "Arduino Leonardo", "board": "leonardo", "chip": "atmega32u4"},
    ("1A86", "55D4"): {"name": "ESP32-C3 (CH343)", "board": "esp32-c3-devkitm-1", "chip": "esp32c3"},
}


def scan_serial_ports() -> list[dict]:
    """Scan for connected serial devices and identify known boards."""
    try:
        from serial.tools import list_ports
        ports = list_ports.comports()
    except ImportError:
        return _mock_scan()

    devices = []
    for port in ports:
        vid = f"{port.vid:04X}" if port.vid else None
        pid = f"{port.pid:04X}" if port.pid else None

        device_info = {
            "port": port.device,
            "description": port.description,
            "hwid": port.hwid,
            "vid": vid,
            "pid": pid,
            "serial_number": port.serial_number,
            "manufacturer": port.manufacturer,
        }

        # Try to identify the board
        if vid and pid:
            known = KNOWN_DEVICES.get((vid, pid))
            if known:
                device_info.update(known)
            else:
                device_info["name"] = port.description or "Unknown Device"
                device_info["board"] = "unknown"
                device_info["chip"] = "unknown"
        else:
            device_info["name"] = port.description or port.device
            device_info["board"] = "unknown"
            device_info["chip"] = "unknown"

        devices.append(device_info)

    return devices


def _mock_scan() -> list[dict]:
    """Fallback mock data when pyserial is not installed."""
    return [
        {"port": "COM4", "name": "ESP32 DevKit V1", "board": "esp32dev",
         "chip": "esp32", "vid": "10C4", "pid": "EA60", "description": "Silicon Labs CP210x"},
        {"port": "COM7", "name": "ESP32-S3 DevKit", "board": "esp32-s3-devkitc-1",
         "chip": "esp32s3", "vid": "303A", "pid": "1001", "description": "Espressif USB JTAG"},
    ]


async def flash_firmware(port: str, firmware_path: str, chip: str = "esp32") -> dict:
    """Flash firmware binary to device using esptool."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "esptool.py", "--chip", chip, "--port", port,
            "--baud", "460800", "write_flash", "-z", "0x10000", firmware_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return {
            "success": proc.returncode == 0,
            "output": stdout.decode() if stdout else "",
            "error": stderr.decode() if stderr else "",
            "port": port,
            "chip": chip,
        }
    except FileNotFoundError:
        return {
            "success": False,
            "error": "esptool.py not found. Install with: pip install esptool",
            "port": port,
        }


async def read_serial(port: str, baud: int = 115200, timeout: float = 5.0) -> list[str]:
    """Read serial output from a device for a short duration."""
    try:
        import serial
        ser = serial.Serial(port, baud, timeout=1)
        lines = []
        import time
        end = time.time() + timeout
        while time.time() < end:
            if ser.in_waiting:
                line = ser.readline().decode("utf-8", errors="replace").strip()
                if line:
                    lines.append(line)
            await asyncio.sleep(0.05)
        ser.close()
        return lines
    except ImportError:
        return ["[MOCK] pyserial not installed — install with: pip install pyserial"]
    except Exception as e:
        return [f"[ERROR] {str(e)}"]
