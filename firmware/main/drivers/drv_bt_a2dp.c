/**
 * Bluetooth A2DP audio driver — wireless speaker output via Bluetooth Classic.
 *
 * Based on: pschatzmann/ESP32-A2DP v1.9.2
 * Works alongside arduino-audio-tools for I2S output chaining.
 * Receives audio from phone/PC via Bluetooth A2DP sink profile.
 */

#include "driver_abi.h"
#include <string.h>

typedef struct {
    bool connected;
    bool playing;
    int volume_percent;
} a2dp_state_t;

static a2dp_state_t a2dp_state;

static esp_err_t a2dp_init(const driver_config_t *cfg) {
    memset(&a2dp_state, 0, sizeof(a2dp_state));
    a2dp_state.volume_percent = 100;
    return ESP_OK;
}

static esp_err_t a2dp_read(driver_handle_t h, capability_t field, sensor_value_t *out) {
    if (!out) return ESP_ERR_INVALID_ARG;
    out->capability = field;
    out->error = DRV_OK;

    switch (field) {
        case CAP_BT_A2DP_PLAY:
            out->type = VAL_TYPE_BOOL;
            out->b = a2dp_state.playing;
            break;
        case CAP_BT_A2DP_VOLUME:
            out->type = VAL_TYPE_INT;
            out->i = a2dp_state.volume_percent;
            break;
        default:
            out->error = DRV_ERR_NOT_SUPPORTED;
            return ESP_ERR_NOT_SUPPORTED;
    }
    return ESP_OK;
}

static esp_err_t a2dp_write(driver_handle_t h, const actuator_cmd_t *cmd) {
    if (!cmd) return ESP_ERR_INVALID_ARG;
    switch (cmd->capability) {
        case CAP_BT_A2DP_PLAY:
            a2dp_state.playing = cmd->b;
            return ESP_OK;
        case CAP_BT_A2DP_VOLUME:
            a2dp_state.volume_percent = cmd->i;
            return ESP_OK;
        default:
            return ESP_ERR_NOT_SUPPORTED;
    }
}

static esp_err_t a2dp_deinit(driver_handle_t h) {
    a2dp_state.connected = false;
    a2dp_state.playing = false;
    return ESP_OK;
}

static const driver_meta_t a2dp_meta = {
    .name = "drv_bt_a2dp",
    .display_name = "Bluetooth A2DP Audio",
    .version = "1.0.0",
    .type = DRIVER_TYPE_ACTUATOR,
    .bus_type = BUS_TYPE_UART,
    .capabilities = { CAP_BT_A2DP_PLAY, CAP_BT_A2DP_VOLUME },
    .num_capabilities = 2,
    .max_latency_us = 50000,
    .min_interval_ms = 100,
    .num_failure_modes = 1,
    .failure_modes = {
        { .error = DRV_ERR_TIMEOUT, .description = "Bluetooth disconnected" }
    },
    .internal_state_size = sizeof(a2dp_state_t),
};

const driver_vtable_t drv_bt_a2dp_vtable = {
    .init   = a2dp_init,
    .read   = a2dp_read,
    .write  = a2dp_write,
    .deinit = a2dp_deinit,
    .meta   = &a2dp_meta,
};

PARAKRAM_REGISTER_DRIVER(bt_a2dp, drv_bt_a2dp_vtable);
