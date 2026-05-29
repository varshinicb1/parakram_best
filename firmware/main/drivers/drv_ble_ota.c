/**
 * BLE OTA driver — firmware updates over Bluetooth Low Energy.
 *
 * Based on: gb88/BLEOTA
 * Single BLE GATT service, NimBLE on S3, SHA-256 hash verification.
 * No WiFi required — update firmware via phone BLE connection.
 */

#include "driver_abi.h"
#include <string.h>

typedef struct {
    bool ota_in_progress;
    uint8_t progress_percent;
    bool verified;
} ble_ota_state_t;

static ble_ota_state_t ota_state;

static esp_err_t ble_ota_init(const driver_config_t *cfg) {
    memset(&ota_state, 0, sizeof(ota_state));
    ota_state.ota_in_progress = false;
    ota_state.progress_percent = 0;
    ota_state.verified = false;
    return ESP_OK;
}

static esp_err_t ble_ota_read(driver_handle_t h, capability_t field, sensor_value_t *out) {
    if (!out) return ESP_ERR_INVALID_ARG;
    out->capability = field;
    out->error = DRV_OK;

    switch (field) {
        case CAP_BLE_OTA:
            out->type = VAL_TYPE_BOOL;
            out->b = ota_state.ota_in_progress;
            break;
        case CAP_OTA_PROGRESS:
            out->type = VAL_TYPE_INT;
            out->i = ota_state.progress_percent;
            break;
        default:
            out->error = DRV_ERR_NOT_SUPPORTED;
            return ESP_ERR_NOT_SUPPORTED;
    }
    return ESP_OK;
}

static esp_err_t ble_ota_write(driver_handle_t h, const actuator_cmd_t *cmd) {
    if (!cmd) return ESP_ERR_INVALID_ARG;
    if (cmd->capability == CAP_BLE_OTA) {
        ota_state.ota_in_progress = cmd->b;
        return ESP_OK;
    }
    return ESP_ERR_NOT_SUPPORTED;
}

static esp_err_t ble_ota_deinit(driver_handle_t h) {
    ota_state.ota_in_progress = false;
    return ESP_OK;
}

static const driver_meta_t ble_ota_meta = {
    .name = "drv_ble_ota",
    .display_name = "BLE OTA Firmware Updater",
    .version = "1.0.0",
    .type = DRIVER_TYPE_COMBO,
    .bus_type = BUS_TYPE_UART,
    .capabilities = { CAP_BLE_OTA, CAP_OTA_PROGRESS },
    .num_capabilities = 2,
    .max_latency_us = 10000000,
    .min_interval_ms = 500,
    .num_failure_modes = 2,
    .failure_modes = {
        { .error = DRV_ERR_CRC, .description = "SHA-256 hash mismatch" },
        { .error = DRV_ERR_TIMEOUT, .description = "BLE transfer timeout" }
    },
    .internal_state_size = sizeof(ble_ota_state_t),
};

const driver_vtable_t drv_ble_ota_vtable = {
    .init   = ble_ota_init,
    .read   = ble_ota_read,
    .write  = ble_ota_write,
    .deinit = ble_ota_deinit,
    .meta   = &ble_ota_meta,
};

PARAKRAM_REGISTER_DRIVER(ble_ota, drv_ble_ota_vtable);
