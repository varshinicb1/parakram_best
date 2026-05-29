/**
 * @file dumbdisplay_srv.h
 * @brief DumbDisplay TCP server — phone renders display for the board.
 */

#ifndef DUMBDISPLAY_SRV_H
#define DUMBDISPLAY_SRV_H

#include "esp_err.h"
#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

esp_err_t dd_server_init(void);
void      dd_server_deinit(void);
bool      dd_is_connected(void);

esp_err_t dd_send_cmd(const char *cmd);
esp_err_t dd_draw_text(uint8_t layer, int16_t x, int16_t y, const char *text);
esp_err_t dd_draw_rect(uint8_t layer, int16_t x, int16_t y,
                       uint16_t w, uint16_t h, uint32_t color);
esp_err_t dd_fill_rect(uint8_t layer, int16_t x, int16_t y,
                       uint16_t w, uint16_t h, uint32_t color);
esp_err_t dd_clear_layer(uint8_t layer);
esp_err_t dd_draw_circle(uint8_t layer, int16_t cx, int16_t cy,
                         uint16_t r, uint32_t color);
esp_err_t dd_draw_line(uint8_t layer, int16_t x1, int16_t y1,
                       int16_t x2, int16_t y2, uint32_t color);
esp_err_t dd_set_font(uint8_t layer, uint8_t size);
esp_err_t dd_update_gauge(uint8_t layer, const char *label,
                          float value, const char *unit);

#ifdef __cplusplus
}
#endif

#endif /* DUMBDISPLAY_SRV_H */
