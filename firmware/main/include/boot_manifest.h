/**
 * @file boot_manifest.h
 * @brief I2C auto-detect hardware manifest generator.
 */

#ifndef BOOT_MANIFEST_H
#define BOOT_MANIFEST_H

#include "esp_err.h"
#include "driver/i2c.h"
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

uint8_t     boot_manifest_scan(i2c_port_t port);
const char *boot_manifest_to_json(void);
esp_err_t   boot_manifest_save(void);
uint8_t     boot_manifest_get_count(void);

#ifdef __cplusplus
}
#endif

#endif /* BOOT_MANIFEST_H */
