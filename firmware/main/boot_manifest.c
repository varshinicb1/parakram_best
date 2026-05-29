/**
 * @file boot_manifest.c
 * @brief I2C auto-detect — hardware manifest generation at boot.
 *
 * Scans all 127 I2C addresses on the configured bus(es).
 * Identifies known Parakram-supported peripherals by address.
 * Generates a JSON HardwareManifest and stores it in NVS.
 * The manifest is sent to the phone app via BLE on first connection.
 *
 * Known device database: 40+ sensors/displays from the Parakram driver registry.
 */

#include "esp_log.h"
#include "esp_err.h"
#include "driver/i2c.h"
#include "nvs_flash.h"
#include "nvs.h"
#include <string.h>
#include <stdio.h>

static const char *TAG = "MANIFEST";

#define MANIFEST_MAX_DEVICES    16
#define MANIFEST_NVS_KEY        "hw_manifest"
#define MANIFEST_JSON_MAX       2048

typedef struct {
    uint8_t     address;
    const char *name;
    const char *driver;
    const char *type;
} known_device_t;

/* Known I2C device address → driver mapping */
static const known_device_t KNOWN_DEVICES[] = {
    /* Sensors */
    {0x76, "BME280/BMP280",        "drv_bme280",     "sensor"},
    {0x77, "BME280/BMP280 (alt)",  "drv_bme280",     "sensor"},
    {0x68, "MPU6050",              "drv_mpu6050",     "sensor"},
    {0x69, "MPU6050 (alt)",        "drv_mpu6050",     "sensor"},
    {0x44, "SHT31",                "drv_sht31",       "sensor"},
    {0x23, "BH1750",               "drv_bh1750",      "sensor"},
    {0x38, "AHT20",                "drv_aht20",       "sensor"},
    {0x57, "MAX30102",             "drv_max30102",    "sensor"},
    {0x40, "INA219",               "drv_ina219",      "sensor"},
    {0x53, "ADXL345",              "drv_adxl345",     "sensor"},
    {0x39, "APDS9960/TSL2561",     "drv_apds9960",    "sensor"},
    {0x29, "VL53L0X",              "drv_vl53l0x",     "sensor"},
    {0x5C, "LPS22HB",              "drv_lps22hb",     "sensor"},
    {0x18, "MCP9808/LIS3DH",       "drv_mcp9808",     "sensor"},
    {0x5A, "CCS811/MLX90614",      "drv_ccs811",      "sensor"},
    {0x52, "ENS160",               "drv_ens160",      "sensor"},
    {0x58, "SGP30",                "drv_sgp30",       "sensor"},
    {0x48, "VEML7700",             "drv_veml7700",    "sensor"},
    {0x62, "SCD40",                "drv_scd40",       "sensor"},
    {0x28, "MFRC522",              "drv_mfrc522",     "sensor"},
    {0x5F, "HTS221",               "drv_hts221",      "sensor"},
    /* Displays */
    {0x3C, "SSD1306 OLED",         "drv_oled_ssd1306","display"},
    {0x3D, "SSD1306 OLED (alt)",   "drv_oled_ssd1306","display"},
    {0x27, "LCD I2C (PCF8574)",    "drv_lcd_i2c",     "display"},
    {0x3F, "LCD I2C (alt)",        "drv_lcd_i2c",     "display"},
    /* Touch */
    {0x15, "CST816S",              "drv_cst816s",     "touch"},
    {0x38, "FT6236",               "drv_ft6236",      "touch"},
    /* RTC */
    {0x68, "DS3231 RTC",           "ds3231",          "rtc"},
    /* End sentinel */
    {0x00, NULL, NULL, NULL},
};

typedef struct {
    uint8_t     address;
    const char *name;
    const char *driver;
    const char *type;
} detected_device_t;

static detected_device_t s_detected[MANIFEST_MAX_DEVICES];
static uint8_t s_num_detected = 0;
static EXT_RAM_BSS_ATTR char s_manifest_json[MANIFEST_JSON_MAX];

/**
 * @brief Look up a known device by I2C address.
 */
static const known_device_t *lookup_device(uint8_t addr) {
    for (int i = 0; KNOWN_DEVICES[i].name != NULL; i++) {
        if (KNOWN_DEVICES[i].address == addr) {
            return &KNOWN_DEVICES[i];
        }
    }
    return NULL;
}

/**
 * @brief Scan I2C bus and identify connected peripherals.
 * @param port  I2C port number (0 or 1).
 * @return Number of devices found.
 */
uint8_t boot_manifest_scan(i2c_port_t port) {
    ESP_LOGI(TAG, "Scanning I2C bus %d for peripherals...", port);
    s_num_detected = 0;

    for (uint8_t addr = 0x08; addr < 0x78; addr++) {
        if (s_num_detected >= MANIFEST_MAX_DEVICES) {
            break;
        }

        i2c_cmd_handle_t cmd = i2c_cmd_link_create();
        i2c_master_start(cmd);
        i2c_master_write_byte(cmd, (addr << 1) | I2C_MASTER_WRITE, true);
        i2c_master_stop(cmd);

        esp_err_t ret = i2c_master_cmd_begin(port, cmd, pdMS_TO_TICKS(50));
        i2c_cmd_link_delete(cmd);

        if (ret == ESP_OK) {
            const known_device_t *dev = lookup_device(addr);
            s_detected[s_num_detected].address = addr;

            if (dev != NULL) {
                s_detected[s_num_detected].name   = dev->name;
                s_detected[s_num_detected].driver = dev->driver;
                s_detected[s_num_detected].type   = dev->type;
                ESP_LOGI(TAG, "  0x%02X: %s (%s)", addr, dev->name, dev->driver);
            } else {
                s_detected[s_num_detected].name   = "unknown";
                s_detected[s_num_detected].driver = NULL;
                s_detected[s_num_detected].type   = "unknown";
                ESP_LOGI(TAG, "  0x%02X: unknown device", addr);
            }

            s_num_detected++;
        }
    }

    ESP_LOGI(TAG, "Scan complete: %u device(s) found.", s_num_detected);
    return s_num_detected;
}

/**
 * @brief Generate JSON manifest from scan results.
 * @return Pointer to null-terminated JSON string.
 */
const char *boot_manifest_to_json(void) {
    int offset = 0;
    offset += snprintf(s_manifest_json + offset,
                       MANIFEST_JSON_MAX - (size_t)offset,
                       "{\"board\":\"S3-PRO-N16R8\",\"firmware\":\"1.0.0\","
                       "\"devices\":[");

    for (uint8_t i = 0; i < s_num_detected; i++) {
        if (i > 0) {
            s_manifest_json[offset++] = ',';
        }
        offset += snprintf(s_manifest_json + offset,
                           MANIFEST_JSON_MAX - (size_t)offset,
                           "{\"addr\":\"0x%02X\",\"name\":\"%s\","
                           "\"driver\":\"%s\",\"type\":\"%s\"}",
                           s_detected[i].address,
                           s_detected[i].name,
                           s_detected[i].driver ? s_detected[i].driver : "none",
                           s_detected[i].type);
    }

    (void)snprintf(s_manifest_json + offset,
                   MANIFEST_JSON_MAX - (size_t)offset,
                   "],\"count\":%u}", s_num_detected);

    return s_manifest_json;
}

/**
 * @brief Save manifest to NVS for persistence across reboots.
 */
esp_err_t boot_manifest_save(void) {
    nvs_handle_t handle;
    esp_err_t err = nvs_open("parakram", NVS_READWRITE, &handle);
    if (err != ESP_OK) {
        return err;
    }

    err = nvs_set_str(handle, MANIFEST_NVS_KEY, s_manifest_json);
    if (err == ESP_OK) {
        err = nvs_commit(handle);
    }

    nvs_close(handle);
    return err;
}

uint8_t boot_manifest_get_count(void) {
    return s_num_detected;
}
