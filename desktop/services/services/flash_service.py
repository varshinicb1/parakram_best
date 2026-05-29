"""
Flash Service
Device detection, firmware upload, and serial monitor management.
"""

import os
import asyncio
import subprocess
import serial.tools.list_ports


class FlashService:
    """Manages device flashing and serial monitoring."""

    def __init__(self):
        self.projects_dir = os.environ.get("PROJECTS_DIR", "../projects")
        self._monitor_process = None

    def detect_devices(self) -> list[dict]:
        """
        Detect connected ESP32 devices via USB serial ports.
        Looks for common ESP32 USB-UART chips (CP210x, CH340, FTDI).
        """
        devices = []
        ports = serial.tools.list_ports.comports()

        esp32_identifiers = [
            "CP210", "CH340", "CH9102", "FTDI", "USB Serial",
            "Silicon Labs", "wch.cn", "1a86",  # CH340 vendor
            "10c4",  # CP210x vendor
        ]

        for port in ports:
            is_esp32 = any(
                ident.lower() in (port.description + " " + (port.manufacturer or "")).lower()
                for ident in esp32_identifiers
            )
            devices.append({
                "port": port.device,
                "description": port.description,
                "manufacturer": port.manufacturer or "Unknown",
                "is_esp32_likely": is_esp32,
                "hwid": port.hwid,
            })

        return devices

    async def flash(self, project_id: str, port: str | None = None) -> dict:
        """
        Flash firmware to ESP32 device using PlatformIO.
        Auto-detects port if not specified.
        """
        firmware_dir = os.path.join(self.projects_dir, project_id, "firmware")

        if not os.path.exists(os.path.join(firmware_dir, "platformio.ini")):
            raise FileNotFoundError("No firmware found. Build first.")

        cmd = ["pio", "run", "--target", "upload"]
        if port:
            cmd.extend(["--upload-port", port])

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=firmware_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            output = stdout.decode("utf-8", errors="replace")
            error_output = stderr.decode("utf-8", errors="replace")

            if process.returncode == 0:
                return {
                    "status": "success",
                    "message": "Firmware flashed successfully",
                    "output": output,
                }
            else:
                return {
                    "status": "failed",
                    "message": "Flash failed",
                    "output": output + error_output,
                }
        except FileNotFoundError:
            raise RuntimeError("PlatformIO CLI not found. Install with: pip install platformio")

    def start_monitor(self, port: str | None = None, baud: int = 115200) -> dict:
        """Start serial monitor (non-blocking)."""
        if self._monitor_process and self._monitor_process.poll() is None:
            return {"status": "already_running"}

        cmd = ["pio", "device", "monitor", "--baud", str(baud)]
        if port:
            cmd.extend(["--port", port])

        try:
            self._monitor_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            return {
                "status": "started",
                "pid": self._monitor_process.pid,
            }
        except FileNotFoundError:
            raise RuntimeError("PlatformIO CLI not found")

    def stop_monitor(self):
        """Stop the running serial monitor."""
        if self._monitor_process and self._monitor_process.poll() is None:
            self._monitor_process.terminate()
            self._monitor_process = None
