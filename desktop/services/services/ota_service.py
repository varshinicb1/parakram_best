"""
OTA Update Service — Over-the-Air firmware updates.

Provides:
  - OTA firmware push via HTTP to ESP32/ESP8266 devices
  - Firmware version management
  - Update progress tracking
"""
import os
import asyncio
import hashlib


class OTAService:
    """Manages OTA firmware updates for connected devices."""

    def __init__(self):
        self.updates_dir = os.path.join(os.path.dirname(__file__), "..", "ota_updates")
        os.makedirs(self.updates_dir, exist_ok=True)

    def get_firmware_info(self, firmware_path: str) -> dict:
        """Get firmware binary info (size, hash, version)."""
        if not os.path.exists(firmware_path):
            return {"error": f"Firmware not found: {firmware_path}"}

        size = os.path.getsize(firmware_path)
        with open(firmware_path, "rb") as f:
            md5 = hashlib.md5(f.read()).hexdigest()

        return {
            "path": firmware_path,
            "size": size,
            "size_human": f"{size / 1024:.1f} KB",
            "md5": md5,
        }

    async def push_ota(self, device_ip: str, firmware_path: str, port: int = 3232) -> dict:
        """Push firmware to device via HTTP OTA (ESP32 ArduinoOTA compatible)."""
        info = self.get_firmware_info(firmware_path)
        if "error" in info:
            return info

        try:
            import aiohttp
            url = f"http://{device_ip}:{port}/update"
            with open(firmware_path, "rb") as f:
                data = f.read()

            async with aiohttp.ClientSession() as session:
                headers = {
                    "Content-Type": "application/octet-stream",
                    "Content-Length": str(len(data)),
                    "x-MD5": info["md5"],
                }
                async with session.post(url, data=data, headers=headers, timeout=aiohttp.ClientTimeout(total=120)) as resp:
                    return {
                        "success": resp.status == 200,
                        "status_code": resp.status,
                        "device_ip": device_ip,
                        "firmware_size": info["size_human"],
                        "md5": info["md5"],
                    }
        except ImportError:
            return await self._espota_fallback(device_ip, firmware_path, port)
        except Exception as e:
            return {"success": False, "error": str(e), "device_ip": device_ip}

    async def _espota_fallback(self, device_ip: str, firmware_path: str, port: int) -> dict:
        """Fallback: use espota.py (comes with Arduino ESP32 core)."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "python", "-m", "espota", "-i", device_ip,
                "-p", str(port), "-f", firmware_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            return {
                "success": proc.returncode == 0,
                "output": stdout.decode() if stdout else "",
                "error": stderr.decode() if stderr else "",
                "device_ip": device_ip,
                "method": "espota",
            }
        except Exception as e:
            return {"success": False, "error": str(e), "method": "espota"}

    def generate_ota_firmware_code(self) -> str:
        """Generate Arduino OTA setup code for inclusion in firmware."""
        return '''// ─── OTA Update Support ─────────────────────────────────
#include <ArduinoOTA.h>

void setupOTA(const char* hostname) {
    ArduinoOTA.setHostname(hostname);
    ArduinoOTA.setPassword("parakram_ota");

    ArduinoOTA.onStart([]() {
        String type = (ArduinoOTA.getCommand() == U_FLASH)
            ? "firmware" : "filesystem";
        Serial.println("[OTA] Start updating " + type);
    });

    ArduinoOTA.onEnd([]() {
        Serial.println("\\n[OTA] Update complete — rebooting");
    });

    ArduinoOTA.onProgress([](unsigned int progress, unsigned int total) {
        Serial.printf("[OTA] Progress: %u%%\\r", (progress / (total / 100)));
    });

    ArduinoOTA.onError([](ota_error_t error) {
        Serial.printf("[OTA] Error[%u]: ", error);
        switch (error) {
            case OTA_AUTH_ERROR:    Serial.println("Auth Failed"); break;
            case OTA_BEGIN_ERROR:   Serial.println("Begin Failed"); break;
            case OTA_CONNECT_ERROR:Serial.println("Connect Failed"); break;
            case OTA_RECEIVE_ERROR:Serial.println("Receive Failed"); break;
            case OTA_END_ERROR:    Serial.println("End Failed"); break;
        }
    });

    ArduinoOTA.begin();
    Serial.println("[OTA] Ready — IP: " + WiFi.localIP().toString());
}
// Call ArduinoOTA.handle() in your loop()
'''
