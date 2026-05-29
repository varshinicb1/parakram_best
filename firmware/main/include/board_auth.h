/**
 * @file board_auth.h
 * @brief Board authentication — eFuse-based identity binding.
 *
 * Ensures firmware runs ONLY on Vidyuthlabs ESP32-S3 N16R8 boards.
 */

#ifndef BOARD_AUTH_H
#define BOARD_AUTH_H

#include "esp_err.h"
#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Initialize board authentication.
 *
 * Verifies: ESP32-S3 chip, 16 MB flash, 8 MB PSRAM, Vidyuthlabs OUI.
 * In production mode, halts on failure. In dev mode, logs warning.
 *
 * @return ESP_OK on success.
 */
esp_err_t board_auth_init(void);

/**
 * @brief Check if board passed authentication.
 * @return true if authenticated.
 */
bool board_auth_is_authenticated(void);

/**
 * @brief Get the 32-byte board identity hash.
 * @return Pointer to SHA-256 hash (valid after board_auth_init).
 */
const uint8_t *board_auth_get_hash(void);

#ifdef __cplusplus
}
#endif

#endif /* BOARD_AUTH_H */
