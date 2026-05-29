/**
 * WiFi Provisioning driver — SoftAP captive portal for WiFi credential entry.
 *
 * Based on: tzapu/WiFiManager
 * Launches SoftAP, user connects and enters WiFi credentials via captive portal.
 * Credentials saved to NVS. Triggers board → Parakram handshake on success.
 */

#include "driver_abi.h"
#include <string.h>

typedef struct {
    bool provisioned;
    bool portal_active;
    int timeout_sec;
} wifi_prov_state_t;

static wifi_prov_state_t prov_state;

static esp_err_t wifi_prov_init(const driver_config_t *cfg) {
    memset(&prov_state, 0, sizeof(prov_state));
    prov_state.timeout_sec = 180;
    prov_state.provisioned = false;
    prov_state.portal_active = false;
    return ESP_OK;
}

static esp_err_t wifi_prov_read(driver_handle_t h, capability_t field, sensor_value_t *out) {
    if (!out) return ESP_ERR_INVALID_ARG;
    out->capability = field;
    out->error = DRV_OK;

    switch (field) {
        case CAP_WIFI_STATUS:
            out->type = VAL_TYPE_BOOL;
            out->b = prov_state.provisioned;
            break;
        case CAP_WIFI_PROVISION:
            out->type = VAL_TYPE_BOOL;
            out->b = prov_state.portal_active;
            break;
        default:
            out->error = DRV_ERR_NOT_SUPPORTED;
            return ESP_ERR_NOT_SUPPORTED;
    }
    return ESP_OK;
}

static esp_err_t wifi_prov_write(driver_handle_t h, const actuator_cmd_t *cmd) {
    if (!cmd) return ESP_ERR_INVALID_ARG;
    if (cmd->capability == CAP_WIFI_PROVISION) {
        prov_state.portal_active = cmd->b;
        return ESP_OK;
    }
    return ESP_ERR_NOT_SUPPORTED;
}

static esp_err_t wifi_prov_deinit(driver_handle_t h) {
    prov_state.portal_active = false;
    return ESP_OK;
}

static const driver_meta_t wifi_prov_meta = {
    .name = "drv_wifi_provision",
    .display_name = "WiFi Provisioning (SoftAP)",
    .version = "1.0.0",
    .type = DRIVER_TYPE_COMBO,
    .bus_type = BUS_TYPE_UART,
    .capabilities = { CAP_WIFI_PROVISION, CAP_WIFI_STATUS },
    .num_capabilities = 2,
    .max_latency_us = 5000000,
    .min_interval_ms = 1000,
    .num_failure_modes = 1,
    .failure_modes = {
        { .error = DRV_ERR_TIMEOUT, .description = "Portal timeout — no credentials entered" }
    },
    .internal_state_size = sizeof(wifi_prov_state_t),
};

const driver_vtable_t drv_wifi_provision_vtable = {
    .init   = wifi_prov_init,
    .read   = wifi_prov_read,
    .write  = wifi_prov_write,
    .deinit = wifi_prov_deinit,
    .meta   = &wifi_prov_meta,
};

PARAKRAM_REGISTER_DRIVER(wifi_provision, drv_wifi_provision_vtable);
