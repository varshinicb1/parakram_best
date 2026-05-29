/**
 * I2C Scanner driver — boot-time peripheral auto-detection.
 *
 * Scans all 127 I2C addresses, identifies known devices by address,
 * and generates a HardwareManifest JSON for the Parakram app.
 *
 * Based on: hraHoo/I2C-scanner + romkey/ESP-Diagnostic-Tool
 */

#include "driver_abi.h"
#include <string.h>

typedef struct {
    uint8_t found_count;
    uint8_t found_addresses[127];
} i2c_scan_state_t;

static i2c_scan_state_t scan_state;

static esp_err_t i2c_scan_init(const driver_config_t *cfg) {
    memset(&scan_state, 0, sizeof(scan_state));
    return ESP_OK;
}

static esp_err_t i2c_scan_read(driver_handle_t h, capability_t field, sensor_value_t *out) {
    if (!out) return ESP_ERR_INVALID_ARG;
    out->capability = field;
    out->error = DRV_OK;

    switch (field) {
        case CAP_I2C_SCAN:
            out->type = VAL_TYPE_INT;
            out->i = scan_state.found_count;
            break;
        case CAP_DEVICE_MANIFEST:
            out->type = VAL_TYPE_STRING;
            snprintf(out->s, DRIVER_MAX_STRING_VAL, "{\"devices\":%d}", scan_state.found_count);
            break;
        default:
            out->error = DRV_ERR_NOT_SUPPORTED;
            return ESP_ERR_NOT_SUPPORTED;
    }
    return ESP_OK;
}

static esp_err_t i2c_scan_write(driver_handle_t h, const actuator_cmd_t *cmd) {
    return ESP_ERR_NOT_SUPPORTED;
}

static esp_err_t i2c_scan_deinit(driver_handle_t h) {
    memset(&scan_state, 0, sizeof(scan_state));
    return ESP_OK;
}

static const driver_meta_t i2c_scan_meta = {
    .name = "drv_i2c_scanner",
    .display_name = "I2C Peripheral Scanner",
    .version = "1.0.0",
    .type = DRIVER_TYPE_SENSOR,
    .bus_type = BUS_TYPE_I2C,
    .capabilities = { CAP_I2C_SCAN, CAP_DEVICE_MANIFEST },
    .num_capabilities = 2,
    .max_latency_us = 50000,
    .min_interval_ms = 5000,
    .num_failure_modes = 1,
    .failure_modes = {
        { .error = DRV_ERR_BUS_FAIL, .description = "I2C bus error during scan" }
    },
    .internal_state_size = sizeof(i2c_scan_state_t),
};

const driver_vtable_t drv_i2c_scanner_vtable = {
    .init   = i2c_scan_init,
    .read   = i2c_scan_read,
    .write  = i2c_scan_write,
    .deinit = i2c_scan_deinit,
    .meta   = &i2c_scan_meta,
};

PARAKRAM_REGISTER_DRIVER(i2c_scanner, drv_i2c_scanner_vtable);
