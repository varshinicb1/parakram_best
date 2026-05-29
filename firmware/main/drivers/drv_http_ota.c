/**
 * HTTP OTA driver — firmware updates over WiFi HTTP.
 *
 * Based on: ayushsharma82/ElegantOTA
 * Web UI for OTA updates — 3-line integration.
 * Works on ESP32, ESP8266, RP2040.
 */

#include "driver_abi.h"
#include <string.h>

typedef struct {
    bool ota_in_progress;
    uint8_t progress_percent;
    bool server_running;
} http_ota_state_t;

static http_ota_state_t hota_state;

static esp_err_t http_ota_init(const driver_config_t *cfg) {
    memset(&hota_state, 0, sizeof(hota_state));
    return ESP_OK;
}

static esp_err_t http_ota_read(driver_handle_t h, capability_t field, sensor_value_t *out) {
    if (!out) return ESP_ERR_INVALID_ARG;
    out->capability = field;
    out->error = DRV_OK;

    switch (field) {
        case CAP_HTTP_OTA:
            out->type = VAL_TYPE_BOOL;
            out->b = hota_state.ota_in_progress;
            break;
        case CAP_OTA_PROGRESS:
            out->type = VAL_TYPE_INT;
            out->i = hota_state.progress_percent;
            break;
        default:
            out->error = DRV_ERR_NOT_SUPPORTED;
            return ESP_ERR_NOT_SUPPORTED;
    }
    return ESP_OK;
}

static esp_err_t http_ota_write(driver_handle_t h, const actuator_cmd_t *cmd) {
    if (!cmd) return ESP_ERR_INVALID_ARG;
    if (cmd->capability == CAP_HTTP_OTA) {
        hota_state.server_running = cmd->b;
        return ESP_OK;
    }
    return ESP_ERR_NOT_SUPPORTED;
}

static esp_err_t http_ota_deinit(driver_handle_t h) {
    hota_state.server_running = false;
    return ESP_OK;
}

static const driver_meta_t http_ota_meta = {
    .name = "drv_http_ota",
    .display_name = "HTTP OTA (ElegantOTA)",
    .version = "1.0.0",
    .type = DRIVER_TYPE_COMBO,
    .bus_type = BUS_TYPE_UART,
    .capabilities = { CAP_HTTP_OTA, CAP_OTA_PROGRESS },
    .num_capabilities = 2,
    .max_latency_us = 10000000,
    .min_interval_ms = 500,
    .num_failure_modes = 2,
    .failure_modes = {
        { .error = DRV_ERR_CRC, .description = "Firmware hash mismatch" },
        { .error = DRV_ERR_TIMEOUT, .description = "HTTP upload timeout" }
    },
    .internal_state_size = sizeof(http_ota_state_t),
};

const driver_vtable_t drv_http_ota_vtable = {
    .init   = http_ota_init,
    .read   = http_ota_read,
    .write  = http_ota_write,
    .deinit = http_ota_deinit,
    .meta   = &http_ota_meta,
};

PARAKRAM_REGISTER_DRIVER(http_ota, drv_http_ota_vtable);
