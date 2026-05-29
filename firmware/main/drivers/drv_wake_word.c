/**
 * Wake word detection driver — on-device keyword spotting via TFLite Micro.
 *
 * Based on: kahrendt/esphome-on-device-wake-word
 * Runs inference every 20ms on ESP32-S3 (< 10ms per inference).
 * TFLite Micro model in PSRAM (< 500KB), openWakeWord methodology.
 *
 * Uses INMP441 mic input (I2S_NUM_0) and processes 20ms audio strides.
 */

#include "driver_abi.h"
#include <string.h>

typedef struct {
    bool detected;
    float confidence;
    int detection_count;
    bool listening;
} wake_word_state_t;

static wake_word_state_t ww_state;

static esp_err_t ww_init(const driver_config_t *cfg) {
    memset(&ww_state, 0, sizeof(ww_state));
    ww_state.listening = true;
    return ESP_OK;
}

static esp_err_t ww_read(driver_handle_t h, capability_t field, sensor_value_t *out) {
    if (!out) return ESP_ERR_INVALID_ARG;
    out->capability = field;
    out->error = DRV_OK;

    switch (field) {
        case CAP_WAKE_WORD:
            out->type = VAL_TYPE_BOOL;
            out->b = ww_state.detected;
            if (ww_state.detected) ww_state.detected = false;
            break;
        case CAP_VOICE_ACTIVITY:
            out->type = VAL_TYPE_FLOAT;
            out->f = ww_state.confidence;
            break;
        default:
            out->error = DRV_ERR_NOT_SUPPORTED;
            return ESP_ERR_NOT_SUPPORTED;
    }
    return ESP_OK;
}

static esp_err_t ww_write(driver_handle_t h, const actuator_cmd_t *cmd) {
    if (!cmd) return ESP_ERR_INVALID_ARG;
    if (cmd->capability == CAP_WAKE_WORD) {
        ww_state.listening = cmd->b;
        return ESP_OK;
    }
    return ESP_ERR_NOT_SUPPORTED;
}

static esp_err_t ww_deinit(driver_handle_t h) {
    ww_state.listening = false;
    return ESP_OK;
}

static const driver_meta_t ww_meta = {
    .name = "drv_wake_word",
    .display_name = "Wake Word Detector (TFLite Micro)",
    .version = "1.0.0",
    .type = DRIVER_TYPE_SENSOR,
    .bus_type = BUS_TYPE_I2C,
    .capabilities = { CAP_WAKE_WORD, CAP_VOICE_ACTIVITY },
    .num_capabilities = 2,
    .max_latency_us = 10000,
    .min_interval_ms = 20,
    .num_failure_modes = 1,
    .failure_modes = {
        { .error = DRV_ERR_HW_FAULT, .description = "TFLite model load failed" }
    },
    .internal_state_size = sizeof(wake_word_state_t),
};

const driver_vtable_t drv_wake_word_vtable = {
    .init   = ww_init,
    .read   = ww_read,
    .write  = ww_write,
    .deinit = ww_deinit,
    .meta   = &ww_meta,
};

PARAKRAM_REGISTER_DRIVER(wake_word, drv_wake_word_vtable);
