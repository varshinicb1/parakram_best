# Auto-detected hardware manifest from I2C scan at boot
builtin_interfaces/Time stamp
string device_id
string mcu_type             # e.g. "ESP32-S3", "RP2040"
string firmware_version
uint32 flash_size_kb
uint32 psram_size_kb
string[] detected_drivers   # driver names matched from I2C scan
uint8[] i2c_addresses       # raw I2C addresses found (0x00-0x7F)
string manifest_json        # full manifest as JSON string
