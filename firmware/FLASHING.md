# Parakram Universal Factory Firmware — Flashing Guide

## Hardware Requirements

- **Board**: ESP32-S3-WROOM-1 N16R8 (16 MB flash, 8 MB OPI PSRAM)
- **USB Cable**: USB-C or Micro-USB (for UART/JTAG)
- **Computer**: Windows / macOS / Linux with Python 3.8+

## Prerequisites

Install ESP-IDF v5.3 (or later):
```bash
git clone --depth 1 -b v5.3 https://github.com/espressif/esp-idf.git ~/esp-idf
cd ~/esp-idf && git submodule update --init --depth 1 --recursive
./install.sh esp32s3
source export.sh
```

## Build

```bash
cd firmware
idf.py set-target esp32s3
idf.py build
```

Output: `build/parakram_firmware.bin` (~1.2 MB)

## Flash

### Option 1: idf.py (recommended)
```bash
idf.py -p /dev/ttyUSB0 flash    # Linux
idf.py -p /dev/cu.usbserial flash   # macOS
idf.py -p COM3 flash            # Windows
```

### Option 2: esptool.py (manual)
```bash
python -m esptool --chip esp32s3 -b 460800 \
  --before default_reset --after hard_reset \
  write_flash --flash_mode dio --flash_size 16MB --flash_freq 80m \
  0x0 build/bootloader/bootloader.bin \
  0x8000 build/partition_table/partition-table.bin \
  0xf000 build/ota_data_initial.bin \
  0x20000 build/parakram_firmware.bin
```

## Monitor

```bash
idf.py -p /dev/ttyUSB0 monitor
```

Expected boot output:
```
════════════════════════════════════════════════════
  PARAKRAM UNIVERSAL FACTORY FIRMWARE v1.0.0
  Vidyuthlabs — Zero-Code Hardware Platform
  Board: S3-PRO N16R8 (16MB flash / 8MB PSRAM)
════════════════════════════════════════════════════

[1/18] NVS initialized
[2/18] Board authenticated (Vidyuthlabs S3-PRO)
[3/18] Event bus initialized
...
[18/18] Watchdog initialized (10s timeout)

════════════════════════════════════════════════════
  SYSTEM READY
  WiFi:  SoftAP (parakram)
  BLE:   advertising
  DD:    port 10201 listening
  I2C:   N peripheral(s) detected
  Auth:  verified
════════════════════════════════════════════════════
```

## Partition Layout (16 MB)

| Partition | Type | Offset | Size | Purpose |
|-----------|------|--------|------|---------|
| nvs | data | 0x9000 | 24 KB | WiFi creds, device config |
| otadata | data | 0xF000 | 8 KB | OTA slot tracking |
| phy_init | data | 0x11000 | 4 KB | PHY calibration |
| ota_0 | app | 0x20000 | 3,840 KB | Factory firmware |
| ota_1 | app | 0x3E0000 | 3,840 KB | OTA update slot |
| program | data | 0x7A0000 | 128 KB | Bytecode VM program |
| coredump | data | 0x7C0000 | 128 KB | Crash dump |
| storage | data | 0x7E0000 | 8,320 KB | FAT filesystem |

## Board Locking (Production)

For production boards with eFuse identity:

1. Set `PARAKRAM_DEV_MODE=0` in `firmware/CMakeLists.txt`
2. Uncomment Secure Boot v2 + Flash Encryption in `sdkconfig.defaults`
3. Generate signing key: `espsecure.py generate_signing_key secure_boot_signing_key.pem --version 2`
4. Build and flash
5. On first boot, eFuses are burned — this is **IRREVERSIBLE**

## Certification Notes

- **Secure Boot v2**: RSA-PSS signed bootloader + app (sdkconfig ready, uncomment to enable)
- **Flash Encryption**: AES-256-XTS (sdkconfig ready, uncomment to enable)
- **Anti-rollback**: Enabled by default (`CONFIG_BOOTLOADER_APP_ANTI_ROLLBACK`)
- **Watchdog**: 10s hardware WDT with panic handler
- **Brown-out detection**: Level 7 (lowest voltage threshold)
- **Stack overflow**: Canary-based detection
- **Core dump**: Saved to flash for post-mortem analysis
- **Board authentication**: Chip model + flash size + PSRAM + eFuse identity verified at boot
