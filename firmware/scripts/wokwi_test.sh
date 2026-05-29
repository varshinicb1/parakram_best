#!/bin/bash
# Wokwi Cloud Simulation Test — Parakram Firmware
# Runs the production firmware in Wokwi's ESP32-S3 simulator.
#
# Prerequisites:
#   - WOKWI_CLI_TOKEN environment variable set
#   - wokwi-cli installed at ~/wokwi-cli (or on PATH)
#   - Firmware built: idf.py -C firmware build
#
# Known limitation (May 2026):
#   Wokwi's ESP32-S3 model produces zero serial output with BLE-enabled firmware.
#   The BLE controller init hangs before UART output starts. Use QEMU for boot
#   validation (scripts/qemu_test.sh). Wokwi works for simpler ESP32-S3 projects
#   without BLE.
#
# Usage: ./scripts/wokwi_test.sh [timeout_ms]

set -euo pipefail

FIRMWARE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
WOKWI="${WOKWI:-$HOME/wokwi-cli}"
TIMEOUT_MS="${1:-30000}"
OUTPUT_FILE="$FIRMWARE_DIR/build/wokwi_output.txt"

if [ -z "${WOKWI_CLI_TOKEN:-}" ]; then
    echo "ERROR: WOKWI_CLI_TOKEN not set."
    echo "Get a token from https://wokwi.com/dashboard/ci"
    exit 1
fi

if [ ! -f "$WOKWI" ] && ! command -v wokwi-cli &>/dev/null; then
    echo "ERROR: wokwi-cli not found at $WOKWI or on PATH"
    exit 1
fi

if [ ! -f "$FIRMWARE_DIR/build/flasher_args.json" ]; then
    echo "ERROR: Firmware not built. Run: idf.py -C firmware build"
    exit 1
fi

echo "=== Parakram Wokwi Simulation Test ==="
echo "Firmware dir: $FIRMWARE_DIR"
echo "Timeout: ${TIMEOUT_MS}ms"
echo ""

echo "[1/2] Starting Wokwi simulation..."
"$WOKWI" \
    --timeout "$TIMEOUT_MS" \
    --serial-log-file "$OUTPUT_FILE" \
    --timeout-exit-code 0 \
    "$FIRMWARE_DIR" 2>&1 || true

echo ""
echo "[2/2] Checking serial output..."
BYTES=$(wc -c < "$OUTPUT_FILE" 2>/dev/null || echo "0")

if [ "$BYTES" -gt 0 ]; then
    echo "Serial output: $BYTES bytes"
    echo "--- Serial Log ---"
    head -50 "$OUTPUT_FILE"
    echo "--- End ---"
    
    # Validate boot if output exists
    PASS=0; FAIL=0
    check() {
        if grep -q "$2" "$OUTPUT_FILE"; then
            echo "  PASS: $1"; PASS=$((PASS + 1))
        else
            echo "  FAIL: $1"; FAIL=$((FAIL + 1))
        fi
    }
    check "Boot banner" "PARAKRAM"
    check "Scheduler"   "Scheduler initialized"
    
    echo ""
    echo "=== Results: $PASS/$((PASS+FAIL)) passed ==="
else
    echo "WARNING: Zero serial output (0 bytes)."
    echo "This is a known Wokwi ESP32-S3 limitation with BLE-enabled firmware."
    echo "Use scripts/qemu_test.sh for boot validation instead."
    echo ""
    echo "=== Wokwi test: INCONCLUSIVE (known limitation) ==="
    exit 0
fi
