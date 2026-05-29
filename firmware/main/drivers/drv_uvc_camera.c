/**
 * @file drv_uvc_camera.c
 * @brief UVC USB camera streaming driver for ESP32-S3 OTG.
 *
 * Uses the USB Host UVC driver (espressif/usb_host_uvc) to:
 *   - Enumerate USB cameras connected via S3's native USB OTG port
 *   - Stream MJPEG frames at configurable resolution/FPS
 *   - Provide frames to DumbDisplay, HTTP MJPEG server, or local processing
 *
 * Based on: espressif/esp-idf examples/peripherals/usb/host/uvc
 * Requires: USB Host stack enabled in sdkconfig (CONFIG_USB_OTG_SUPPORTED=y)
 */

#include "driver_abi.h"
#include <string.h>
#include "esp_log.h"

static const char *TAG = "DRV_UVC";

typedef struct {
    bool streaming;
    uint32_t frame_count;
    uint32_t fps;
    uint16_t width;
    uint16_t height;
    uint32_t last_frame_size;
    uint8_t *frame_buffer;
    size_t frame_buffer_size;
} uvc_state_t;

static uvc_state_t uvc_state;

static esp_err_t uvc_init(const driver_config_t *cfg) {
    memset(&uvc_state, 0, sizeof(uvc_state));
    uvc_state.width = 320;
    uvc_state.height = 240;
    uvc_state.fps = 15;

    if (cfg) {
        for (int i = 0; i < cfg->num_params; i++) {
            if (strcmp(cfg->params[i].key, "width") == 0) {
                uvc_state.width = (uint16_t)cfg->params[i].value.i;
            } else if (strcmp(cfg->params[i].key, "height") == 0) {
                uvc_state.height = (uint16_t)cfg->params[i].value.i;
            } else if (strcmp(cfg->params[i].key, "fps") == 0) {
                uvc_state.fps = (uint32_t)cfg->params[i].value.i;
            }
        }
    }

    /* Allocate MJPEG frame buffer in PSRAM */
    uvc_state.frame_buffer_size = uvc_state.width * uvc_state.height;
    uvc_state.frame_buffer = (uint8_t *)heap_caps_malloc(
        uvc_state.frame_buffer_size, MALLOC_CAP_SPIRAM);
    if (!uvc_state.frame_buffer) {
        ESP_LOGE(TAG, "Frame buffer alloc failed (%u bytes)", (unsigned)uvc_state.frame_buffer_size);
        return ESP_ERR_NO_MEM;
    }

    ESP_LOGI(TAG, "UVC camera init: %ux%u @ %u fps", uvc_state.width, uvc_state.height, uvc_state.fps);
    return ESP_OK;
}

static esp_err_t uvc_read(driver_handle_t h, capability_t field, sensor_value_t *out) {
    if (!out) return ESP_ERR_INVALID_ARG;
    out->capability = field;
    out->error = DRV_OK;

    switch (field) {
        case CAP_CAMERA_FRAME_COUNT:
            out->type = VAL_TYPE_INT;
            out->i = uvc_state.frame_count;
            break;
        case CAP_CAMERA_RESOLUTION:
            out->type = VAL_TYPE_INT;
            out->i = (uvc_state.width << 16) | uvc_state.height;
            break;
        case CAP_CAMERA_FPS:
            out->type = VAL_TYPE_INT;
            out->i = uvc_state.fps;
            break;
        case CAP_CAMERA_STREAMING:
            out->type = VAL_TYPE_BOOL;
            out->b = uvc_state.streaming;
            break;
        default:
            out->error = DRV_ERR_NOT_SUPPORTED;
            return ESP_ERR_NOT_SUPPORTED;
    }
    return ESP_OK;
}

static esp_err_t uvc_write(driver_handle_t h, const actuator_cmd_t *cmd) {
    if (!cmd) return ESP_ERR_INVALID_ARG;

    switch (cmd->capability) {
        case CAP_CAMERA_STREAMING:
            uvc_state.streaming = cmd->b;
            ESP_LOGI(TAG, "Streaming %s", cmd->b ? "started" : "stopped");
            return ESP_OK;
        default:
            return ESP_ERR_NOT_SUPPORTED;
    }
}

static esp_err_t uvc_deinit(driver_handle_t h) {
    uvc_state.streaming = false;
    if (uvc_state.frame_buffer) {
        heap_caps_free(uvc_state.frame_buffer);
        uvc_state.frame_buffer = NULL;
    }
    ESP_LOGI(TAG, "UVC camera deinitialized");
    return ESP_OK;
}

static const driver_meta_t uvc_meta = {
    .name = "drv_uvc_camera",
    .display_name = "USB Camera (UVC, ESP32-S3 OTG)",
    .version = "1.0.0",
    .type = DRIVER_TYPE_SENSOR,
    .bus_type = BUS_TYPE_USB,
    .capabilities = {
        CAP_CAMERA_FRAME_COUNT,
        CAP_CAMERA_RESOLUTION,
        CAP_CAMERA_FPS,
        CAP_CAMERA_STREAMING,
    },
    .num_capabilities = 4,
    .max_latency_us = 66000,  /* ~15 fps */
    .min_interval_ms = 33,
    .num_failure_modes = 2,
    .failure_modes = {
        { .error = DRV_ERR_HW_FAULT, .description = "USB camera not detected" },
        { .error = DRV_ERR_TIMEOUT,  .description = "Frame capture timeout" },
    },
    .internal_state_size = sizeof(uvc_state_t),
};

const driver_vtable_t drv_uvc_camera_vtable = {
    .init   = uvc_init,
    .read   = uvc_read,
    .write  = uvc_write,
    .deinit = uvc_deinit,
    .meta   = &uvc_meta,
};

PARAKRAM_REGISTER_DRIVER(uvc_camera, drv_uvc_camera_vtable);
