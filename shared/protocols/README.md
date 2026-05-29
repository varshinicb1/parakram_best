# Shared Protocols

Cross-platform protocol definitions used by Android, iOS, firmware, and backend.

## BLE GATT Services

| Service UUID | Characteristic | Direction | Purpose |
|---|---|---|---|
| `0xFF01` | `0xFF02` | Board → App | HardwareManifest JSON |
| `0xFF01` | `0xFF03` | App → Board | Command packets |
| `0xFF01` | `0xFF04` | Board → App | Telemetry stream |
| `0xFF01` | `0xFF05` | App → Board | Firmware OTA chunks |

## HardwareManifest Schema

Sent by firmware on boot after peripheral auto-detection:

```json
{
  "board": "ESP32-S3-N16R8",
  "firmware_version": "1.0.0",
  "peripherals": [
    {"type": "mic", "model": "INMP441", "bus": "I2S", "pins": {"ws": 15, "sd": 32, "sck": 14}},
    {"type": "speaker", "model": "MAX98357A", "bus": "I2S", "pins": {"bclk": 26, "lrc": 25, "din": 22}},
    {"type": "display", "model": "ST7789", "bus": "SPI", "resolution": [240, 320]},
    {"type": "sensor", "model": "BME280", "bus": "I2C", "address": "0x76"}
  ],
  "capabilities": ["audio_in", "audio_out", "display", "i2c_scan", "lua", "ota"]
}
```

## UDP Audio Streaming

- Port 5000: Mic PCM (16-bit, 16kHz, mono) from board → app
- Port 5001: TTS PCM from app → board speaker

## Bytecode Payload Format

See `docs/artifacts/04_bytecode_isa.md` for the full ISA specification.

Ed25519 signed, 8-byte instructions, delivered via BLE GATT or WiFi TCP.
