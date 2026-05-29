#ifndef CONFIG_H
#define CONFIG_H

// === Block Configuration Constants ===================
// Total blocks: 4
// Board: esp32dev

// --- Temperature Sensor ---
#define CFG_TEMPERATURE_SENSOR_PIN 4
#define CFG_TEMPERATURE_SENSOR_READ_INTERVAL 2000

// --- Threshold Logic ---
#define CFG_THRESHOLD_LOGIC_THRESHOLD 30.0
#define CFG_THRESHOLD_LOGIC_COMPARISON greater_than

// --- WiFi ---
#define CFG_WIFI_SSID "MyNetwork"
#define CFG_WIFI_PASSWORD "MyPassword"

// --- Filter (Temperature Sensor.temperature) ---
#define CFG_FILTER_TEMPERATURE_SENSORTEMPERATURE_WINDOW_SIZE 5

// === Memory Budget =================================
// Flash: 462,000 bytes (11.0%)
// SRAM:  111,000 bytes (21.3%)

#endif // CONFIG_H
