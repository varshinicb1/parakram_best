#!/bin/bash
# QEMU Simulation Test — Parakram Firmware
# Builds firmware without PSRAM/BT, runs in QEMU ESP32-S3, validates boot sequence.
#
# Prerequisites:
#   - ESP-IDF v5.3 toolchain (source ~/esp-idf/export.sh)
#   - QEMU-xtensa (Espressif fork) at ~/qemu/bin/qemu-system-xtensa
#
# Usage: ./scripts/qemu_test.sh [timeout_seconds]

set -euo pipefail

FIRMWARE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
QEMU="${QEMU:-$HOME/qemu/bin/qemu-system-xtensa}"
TIMEOUT="${1:-30}"
BUILD_DIR="$FIRMWARE_DIR/build_qemu"
OUTPUT_FILE="$BUILD_DIR/qemu_serial_output.txt"

echo "=== Parakram QEMU Simulation Test ==="
echo "Firmware dir: $FIRMWARE_DIR"
echo "QEMU: $QEMU"
echo "Timeout: ${TIMEOUT}s"
echo ""

# Step 1: Build with QEMU sdkconfig (BT=n, SPIRAM=n)
echo "[1/4] Building firmware (SPIRAM=n, BT=n)..."
if [ ! -d "$BUILD_DIR" ]; then
    # Create a QEMU-specific sdkconfig by patching the production one
    cp "$FIRMWARE_DIR/sdkconfig" "$FIRMWARE_DIR/sdkconfig.qemu"
    sed -i 's/^CONFIG_SPIRAM=y/CONFIG_SPIRAM=n/' "$FIRMWARE_DIR/sdkconfig.qemu"
    sed -i 's/^CONFIG_BT_ENABLED=y/CONFIG_BT_ENABLED=n/' "$FIRMWARE_DIR/sdkconfig.qemu"
    sed -i 's/^CONFIG_BT_NIMBLE_ENABLED=y/# CONFIG_BT_NIMBLE_ENABLED is not set/' "$FIRMWARE_DIR/sdkconfig.qemu"
    sed -i 's/^CONFIG_SPIRAM_MODE_OCT=y/# CONFIG_SPIRAM_MODE_OCT is not set/' "$FIRMWARE_DIR/sdkconfig.qemu"
fi
idf.py -C "$FIRMWARE_DIR" \
    -B "$BUILD_DIR" \
    -D "SDKCONFIG=$FIRMWARE_DIR/sdkconfig.qemu" \
    build 2>&1 | tail -3

# Step 2: Merge flash image
echo ""
echo "[2/4] Creating 16MB flash image..."
python3 -m esptool --chip esp32s3 merge_bin \
    --fill-flash-size 16MB \
    -o "$BUILD_DIR/merged_qemu.bin" \
    0x0 "$BUILD_DIR/bootloader/bootloader.bin" \
    0x8000 "$BUILD_DIR/partition_table/partition-table.bin" \
    0xf000 "$BUILD_DIR/ota_data_initial.bin" \
    0x20000 "$BUILD_DIR/parakram_firmware.bin" 2>&1 | tail -1

# Step 3: Run QEMU
# Use -display none + -serial file: instead of -nographic because QEMU's
# -nographic mode produces zero serial output when run from a non-interactive
# bash script (stdout buffering issue with the emulated UART).
echo ""
echo "[3/4] Running QEMU ESP32-S3 (${TIMEOUT}s timeout)..."
timeout "$TIMEOUT" "$QEMU" \
    -M esp32s3 \
    -drive "file=$BUILD_DIR/merged_qemu.bin,if=mtd,format=raw" \
    -display none \
    -serial "file:$OUTPUT_FILE" \
    -monitor none \
    -no-reboot \
    > /dev/null 2>&1 || true
echo "  Serial output: $(wc -c < "$OUTPUT_FILE") bytes captured"

# Step 4: Validate boot sequence
echo ""
echo "[4/4] Validating boot sequence..."
echo ""

PASS=0
FAIL=0

check() {
    local desc="$1"
    local pattern="$2"
    if grep -q "$pattern" "$OUTPUT_FILE"; then
        echo "  PASS: $desc"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: $desc"
        FAIL=$((FAIL + 1))
    fi
}

check "Boot banner"              "PARAKRAM UNIVERSAL FACTORY FIRMWARE v1.0.0"
check "Vidyuthlabs"              "Vidyuthlabs"
check "Zero-Code platform"       "Zero-Code Hardware Platform"
check "NVS initialized"          "NVS initialized"
check "Board auth"               "Board auth"
check "Event bus initialized"    "Event bus initialized"
check "Fault handler initialized" "Fault handler initialized"
check "State store initialized"  "State store initialized"
check "VM initialized"           "VM initialized"
check "Driver registry initialized" "Driver registry initialized"
check "I2C bus initialized"      "I2C0 initialized"
check "Device identity"          "Device ID: VDYT-"
check "Payload verifier"         "Payload verifier initialized"
check "Scheduler initialized"    "Scheduler initialized"

echo ""
TOTAL=$((PASS + FAIL))
echo "=== Results: $PASS/$TOTAL passed ==="

if [ "$FAIL" -gt 0 ]; then
    echo "SIMULATION TEST FAILED ($FAIL assertions failed)"
    exit 1
else
    echo "SIMULATION TEST PASSED — all $PASS assertions verified"
    exit 0
fi
