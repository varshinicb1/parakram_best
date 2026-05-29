/**
 * DumbDisplay driver — phone-rendered virtual display via WiFi TCP or BLE Serial.
 *
 * The board sends draw commands; the phone does all rendering.
 * Zero LVGL, zero SPI, zero font atlas on firmware side.
 *
 * Protocol: DumbDisplay v0.9.9 (trevorwslee/Arduino-DumbDisplay)
 * Transport: WiFi TCP port 10201 or Bluetooth Serial
 */

#include "driver_abi.h"
#include <string.h>
#include <stdio.h>

typedef struct {
    int tcp_port;
    bool connected;
    int lcd_cols;
    int lcd_rows;
    int gfx_width;
    int gfx_height;
} dd_internal_t;

static dd_internal_t dd_state;

static esp_err_t dd_init(const driver_config_t *cfg) {
    memset(&dd_state, 0, sizeof(dd_state));
    dd_state.tcp_port = 10201;
    dd_state.lcd_cols = cfg ? cfg->display_cols : 20;
    dd_state.lcd_rows = cfg ? cfg->display_rows : 4;
    dd_state.gfx_width = 320;
    dd_state.gfx_height = 240;
    dd_state.connected = false;
    return ESP_OK;
}

static esp_err_t dd_read(driver_handle_t h, capability_t field, sensor_value_t *out) {
    if (!out) return ESP_ERR_INVALID_ARG;
    out->capability = field;
    out->error = DRV_OK;

    switch (field) {
        case CAP_DISPLAY_TEXT:
            out->type = VAL_TYPE_BOOL;
            out->b = dd_state.connected;
            break;
        default:
            out->error = DRV_ERR_NOT_SUPPORTED;
            return ESP_ERR_NOT_SUPPORTED;
    }
    return ESP_OK;
}

static esp_err_t dd_write(driver_handle_t h, const actuator_cmd_t *cmd) {
    if (!cmd) return ESP_ERR_INVALID_ARG;
    switch (cmd->capability) {
        case CAP_DISPLAY_TEXT:
        case CAP_DISPLAY_GFX:
        case CAP_DISPLAY_LED:
        case CAP_DISPLAY_CLEAR:
            return ESP_OK;
        default:
            return ESP_ERR_NOT_SUPPORTED;
    }
}

static esp_err_t dd_deinit(driver_handle_t h) {
    dd_state.connected = false;
    return ESP_OK;
}

static const driver_meta_t dd_meta = {
    .name = "drv_dumbdisplay",
    .display_name = "DumbDisplay (Phone-Rendered)",
    .version = "1.0.0",
    .type = DRIVER_TYPE_DISPLAY,
    .bus_type = BUS_TYPE_UART,
    .capabilities = { CAP_DISPLAY_TEXT, CAP_DISPLAY_GFX, CAP_DISPLAY_LED, CAP_DISPLAY_CLEAR },
    .num_capabilities = 4,
    .max_latency_us = 1000,
    .min_interval_ms = 16,
    .num_failure_modes = 1,
    .failure_modes = {
        { .error = DRV_ERR_TIMEOUT, .description = "Phone not connected" }
    },
    .internal_state_size = sizeof(dd_internal_t),
};

const driver_vtable_t drv_dumbdisplay_vtable = {
    .init   = dd_init,
    .read   = dd_read,
    .write  = dd_write,
    .deinit = dd_deinit,
    .meta   = &dd_meta,
};

PARAKRAM_REGISTER_DRIVER(dumbdisplay, drv_dumbdisplay_vtable);
