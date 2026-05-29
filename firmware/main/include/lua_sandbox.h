/**
 * @file lua_sandbox.h
 * @brief Lua 5.4 scripting sandbox for user-defined device logic.
 */
#pragma once

#include "esp_err.h"
#include <stddef.h>

/** Initialize the Lua sandbox (allocator in PSRAM, hw library registered). */
esp_err_t lua_sandbox_init(void);

/**
 * Execute a Lua script in the sandbox.
 * @param script  Source code (NUL-terminated not required if len is correct)
 * @param len     Length of script in bytes
 * @param err_buf Optional buffer for error message on failure (can be NULL)
 * @param err_buf_len Size of err_buf
 * @return ESP_OK on success, ESP_FAIL on runtime error, ESP_ERR_INVALID_ARG on parse error
 */
esp_err_t lua_sandbox_exec(const char *script, size_t len, char *err_buf, size_t err_buf_len);

/** Returns current Lua heap usage in bytes. */
size_t lua_sandbox_mem_used(void);

/** Destroy the Lua state and free all memory. */
void lua_sandbox_deinit(void);
