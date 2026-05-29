#!/bin/bash
# =============================================================================
# Parakram — OSS Dependencies Clone & Update Script
# =============================================================================
# Usage:
#   ./clone_oss_deps.sh              # Clone missing repos only
#   ./clone_oss_deps.sh --update     # Clone missing + pull latest on existing
# =============================================================================

set -euo pipefail

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SUCCESS=0
FAILED=0
UPDATED=0
SKIPPED=0

UPDATE_MODE=false

# Parse arguments
if [[ "${1:-}" == "--update" || "${1:-}" == "-u" ]]; then
    UPDATE_MODE=true
    echo -e "${BLUE}🔄 Running in UPDATE mode (will pull latest changes)${NC}"
else
    echo -e "${BLUE}📥 Running in CLONE mode (will skip existing repos)${NC}"
fi

echo ""

# Check git
if ! command -v git &> /dev/null; then
    echo -e "${RED}❌ Error: git is not installed.${NC}"
    exit 1
fi

TARGET_DIR="parakram-firmware-deps"
mkdir -p "$TARGET_DIR"
cd "$TARGET_DIR"

echo -e "📁 Working in: $(pwd)"
echo ""

# =============================================================================
# Smart Clone / Update Function
# =============================================================================
clone_or_update() {
    local repo_url=$1
    local dir_name=$(basename "$repo_url" .git)

    if [ -d "$dir_name" ]; then
        if $UPDATE_MODE; then
            echo -e "${YELLOW}🔄 Updating: $dir_name${NC}"
            cd "$dir_name"
            if git pull --ff-only > /dev/null 2>&1; then
                echo -e "${GREEN}✅ Updated: $dir_name${NC}"
                ((UPDATED++))
            else
                echo -e "${RED}❌ Failed to update: $dir_name${NC}"
                ((FAILED++))
            fi
            cd ..
        else
            echo -e "${YELLOW}⏭️  Skipping (already exists): $dir_name${NC}"
            ((SKIPPED++))
        fi
        return 0
    fi

    # Clone new repo
    echo -e "${BLUE}📥 Cloning: $dir_name${NC}"
    if git clone --depth 1 "$repo_url" "$dir_name" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Cloned: $dir_name${NC}"
        ((SUCCESS++))
    else
        echo -e "${RED}❌ Failed to clone: $dir_name${NC}"
        ((FAILED++))
    fi
    echo ""
}

# =============================================================================
# LAYERS (same as before)
# =============================================================================

echo -e "${BLUE}=== Layer 1: Grand Reference ===${NC}"
clone_or_update "https://github.com/espressif/esp-box.git"

echo -e "${BLUE}=== Layer 2: Audio Input ===${NC}"
clone_or_update "https://github.com/pschatzmann/arduino-audio-tools.git"
clone_or_update "https://github.com/aleiei/ESP32-BUG-I2S-MIC.git"
clone_or_update "https://github.com/circuitsmiles/ai-chat-bot-v0.2.git"
clone_or_update "https://github.com/kaloprojects/KALO-ESP32-Voice-ChatGPT.git"
clone_or_update "https://github.com/FabrikappAgency/esp32-realtime-voice-assistant.git"

echo -e "${BLUE}=== Layer 3: Audio Output ===${NC}"
clone_or_update "https://github.com/pschatzmann/ESP32-A2DP.git"

echo -e "${BLUE}=== Layer 4: Display ===${NC}"
clone_or_update "https://github.com/trevorwslee/Arduino-DumbDisplay.git"
clone_or_update "https://github.com/trevorwslee/TFTImageShow.git"

echo -e "${BLUE}=== Layer 5: Phone Sensors ===${NC}"
clone_or_update "https://github.com/phyphox/phyphox-arduino.git"

echo -e "${BLUE}=== Layer 6: Wake Word & AI ===${NC}"
clone_or_update "https://github.com/kahrendt/esphome-on-device-wake-word.git"
clone_or_update "https://github.com/espressif/esp-tflite-micro.git"

echo -e "${BLUE}=== Layer 7: BLE OTA ===${NC}"
clone_or_update "https://github.com/gb88/BLEOTA.git"
clone_or_update "https://github.com/fbiego/ESP32_BLE_OTA_Arduino.git"

echo -e "${BLUE}=== Layer 8: WiFi Provisioning ===${NC}"
clone_or_update "https://github.com/tzapu/WiFiManager.git"
clone_or_update "https://github.com/espressif/esp-idf-provisioning-android.git"

echo -e "${BLUE}=== Layer 9: HTTP OTA ===${NC}"
clone_or_update "https://github.com/ayushsharma82/ElegantOTA.git"

echo -e "${BLUE}=== Layer 10: I2C Detection ===${NC}"
clone_or_update "https://github.com/Sensirion/arduino-upt-i2c-auto-detection.git"
clone_or_update "https://github.com/MagicBulletPro/I2C-Device-Scanner.git"

echo -e "${BLUE}=== Layer 11: Lua Scripting ===${NC}"
clone_or_update "https://github.com/whitecatboard/Lua-RTOS-ESP32.git"
clone_or_update "https://github.com/loboris/Lua-RTOS-ESP32.git"

echo -e "${BLUE}=== Layer 12: Offline STT ===${NC}"
clone_or_update "https://github.com/alphacep/vosk-api.git"
clone_or_update "https://github.com/alphacep/vosk-android-demo.git"

echo -e "${BLUE}=== Layer 13: USB Camera ===${NC}"
clone_or_update "https://github.com/esp-arduino-libs/ESP32_USB_Stream.git"

# =============================================================================
# Summary
# =============================================================================
echo ""
echo "=============================================="
echo -e "${BLUE}📊 Final Summary${NC}"
echo "=============================================="
echo -e "${GREEN}✅ Newly cloned:  $SUCCESS${NC}"
echo -e "${GREEN}🔄 Updated:       $UPDATED${NC}"
echo -e "${RED}❌ Failed:        $FAILED${NC}"
echo -e "${YELLOW}⏭️  Skipped:      $SKIPPED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 All done successfully!${NC}"
else
    echo -e "${YELLOW}⚠️  Some operations failed. Please check above.${NC}"
fi