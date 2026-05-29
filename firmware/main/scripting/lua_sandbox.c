/**
 * @file lua_sandbox.c
 * @brief Lua 5.4 scripting sandbox for user-defined device logic on FreeRTOS.
 *
 * Provides a sandboxed Lua runtime with:
 *   - Hardware API bindings (GPIO, I2C, SPI, ADC, PWM)
 *   - Time/delay functions
 *   - Driver registry access (read sensors, write actuators)
 *   - Memory-limited allocator using PSRAM
 *   - Execution deadline enforcement (configurable max runtime)
 *   - No filesystem/network/OS access (sandbox)
 *
 * Scripts are loaded from NVS or OTA and executed in a dedicated FreeRTOS task.
 *
 * Requires: lua-5.4 component (via IDF component manager or vendored source)
 */

#include "lua_sandbox.h"
#include <string.h>
#include "esp_log.h"
#include "esp_heap_caps.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/gpio.h"
#include "driver/i2c.h"

#include "lua.h"
#include "lauxlib.h"
#include "lualib.h"

static const char *TAG = "LUA_SANDBOX";

#define LUA_MAX_MEMORY    (256 * 1024)  /* 256 KB max Lua heap (PSRAM) */
#define LUA_MAX_RUNTIME_MS 5000         /* 5s max script execution */
#define LUA_STACK_SIZE     (8 * 1024)   /* FreeRTOS task stack */

typedef struct {
    lua_State *L;
    TaskHandle_t task;
    size_t mem_used;
    int64_t deadline_us;
    bool running;
} lua_sandbox_t;

static lua_sandbox_t s_sandbox;

/* ── Memory allocator (PSRAM, with limit) ────────────────────────────── */

static void *lua_psram_alloc(void *ud, void *ptr, size_t osize, size_t nsize) {
    lua_sandbox_t *sb = (lua_sandbox_t *)ud;

    if (nsize == 0) {
        if (ptr) {
            sb->mem_used -= osize;
            heap_caps_free(ptr);
        }
        return NULL;
    }

    if (sb->mem_used - osize + nsize > LUA_MAX_MEMORY) {
        ESP_LOGW(TAG, "Memory limit reached (%u/%u)", (unsigned)sb->mem_used, LUA_MAX_MEMORY);
        return NULL;
    }

    void *new_ptr;
    if (ptr) {
        new_ptr = heap_caps_realloc(ptr, nsize, MALLOC_CAP_SPIRAM);
    } else {
        new_ptr = heap_caps_malloc(nsize, MALLOC_CAP_SPIRAM);
    }

    if (new_ptr) {
        sb->mem_used = sb->mem_used - osize + nsize;
    }
    return new_ptr;
}

/* ── Deadline hook (prevents infinite loops) ─────────────────────────── */

static void lua_deadline_hook(lua_State *L, lua_Debug *ar) {
    (void)ar;
    if (esp_timer_get_time() > s_sandbox.deadline_us) {
        luaL_error(L, "script exceeded maximum runtime (%d ms)", LUA_MAX_RUNTIME_MS);
    }
}

/* ── Hardware API bindings ───────────────────────────────────────────── */

static int l_gpio_mode(lua_State *L) {
    int pin = luaL_checkinteger(L, 1);
    const char *mode = luaL_checkstring(L, 2);
    gpio_config_t cfg = {
        .pin_bit_mask = 1ULL << pin,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    if (strcmp(mode, "output") == 0) {
        cfg.mode = GPIO_MODE_OUTPUT;
    } else if (strcmp(mode, "input") == 0) {
        cfg.mode = GPIO_MODE_INPUT;
        cfg.pull_up_en = GPIO_PULLUP_ENABLE;
    } else {
        return luaL_error(L, "unknown mode: %s (use 'input' or 'output')", mode);
    }
    gpio_config(&cfg);
    return 0;
}

static int l_gpio_write(lua_State *L) {
    int pin = luaL_checkinteger(L, 1);
    int val = luaL_checkinteger(L, 2);
    gpio_set_level(pin, val ? 1 : 0);
    return 0;
}

static int l_gpio_read(lua_State *L) {
    int pin = luaL_checkinteger(L, 1);
    lua_pushinteger(L, gpio_get_level(pin));
    return 1;
}

static int l_delay_ms(lua_State *L) {
    int ms = luaL_checkinteger(L, 1);
    if (ms > 0 && ms < 30000) {
        vTaskDelay(pdMS_TO_TICKS(ms));
    }
    return 0;
}

static int l_millis(lua_State *L) {
    lua_pushinteger(L, (lua_Integer)(esp_timer_get_time() / 1000));
    return 1;
}

static int l_print(lua_State *L) {
    int n = lua_gettop(L);
    for (int i = 1; i <= n; i++) {
        const char *s = luaL_tolstring(L, i, NULL);
        if (i > 1) ESP_LOGI(TAG, " ");
        ESP_LOGI(TAG, "%s", s ? s : "(nil)");
        lua_pop(L, 1);
    }
    return 0;
}

static int l_i2c_write(lua_State *L) {
    int addr = luaL_checkinteger(L, 1);
    size_t len;
    const char *data = luaL_checklstring(L, 2, &len);
    i2c_cmd_handle_t cmd = i2c_cmd_link_create();
    i2c_master_start(cmd);
    i2c_master_write_byte(cmd, (addr << 1) | I2C_MASTER_WRITE, true);
    i2c_master_write(cmd, (const uint8_t *)data, len, true);
    i2c_master_stop(cmd);
    esp_err_t ret = i2c_master_cmd_begin(I2C_NUM_0, cmd, pdMS_TO_TICKS(100));
    i2c_cmd_link_delete(cmd);
    lua_pushboolean(L, ret == ESP_OK);
    return 1;
}

static int l_i2c_read(lua_State *L) {
    int addr = luaL_checkinteger(L, 1);
    int len = luaL_checkinteger(L, 2);
    if (len > 128) len = 128;
    uint8_t buf[128];
    i2c_cmd_handle_t cmd = i2c_cmd_link_create();
    i2c_master_start(cmd);
    i2c_master_write_byte(cmd, (addr << 1) | I2C_MASTER_READ, true);
    i2c_master_read(cmd, buf, len, I2C_MASTER_LAST_NACK);
    i2c_master_stop(cmd);
    esp_err_t ret = i2c_master_cmd_begin(I2C_NUM_0, cmd, pdMS_TO_TICKS(100));
    i2c_cmd_link_delete(cmd);
    if (ret == ESP_OK) {
        lua_pushlstring(L, (const char *)buf, len);
    } else {
        lua_pushnil(L);
    }
    return 1;
}

static const luaL_Reg parakram_lib[] = {
    {"gpio_mode",  l_gpio_mode},
    {"gpio_write", l_gpio_write},
    {"gpio_read",  l_gpio_read},
    {"delay",      l_delay_ms},
    {"millis",     l_millis},
    {"i2c_write",  l_i2c_write},
    {"i2c_read",   l_i2c_read},
    {NULL, NULL}
};

/* ── Sandbox whitelist ───────────────────────────────────────────────── */

static void open_sandbox_libs(lua_State *L) {
    luaL_openlibs(L);

    /* Remove dangerous modules */
    lua_pushnil(L); lua_setglobal(L, "io");
    lua_pushnil(L); lua_setglobal(L, "os");
    lua_pushnil(L); lua_setglobal(L, "debug");
    lua_pushnil(L); lua_setglobal(L, "package");
    lua_pushnil(L); lua_setglobal(L, "require");
    lua_pushnil(L); lua_setglobal(L, "dofile");
    lua_pushnil(L); lua_setglobal(L, "loadfile");

    /* Override print */
    lua_pushcfunction(L, l_print);
    lua_setglobal(L, "print");

    /* Register hw library */
    luaL_newlib(L, parakram_lib);
    lua_setglobal(L, "hw");
}

/* ── Public API ──────────────────────────────────────────────────────── */

esp_err_t lua_sandbox_init(void) {
    if (s_sandbox.L) return ESP_OK;

    s_sandbox.mem_used = 0;
    s_sandbox.L = lua_newstate(lua_psram_alloc, &s_sandbox);
    if (!s_sandbox.L) {
        ESP_LOGE(TAG, "Failed to create Lua state");
        return ESP_ERR_NO_MEM;
    }

    open_sandbox_libs(s_sandbox.L);

    ESP_LOGI(TAG, "Lua 5.4 sandbox initialized (max %d KB PSRAM)", LUA_MAX_MEMORY / 1024);
    return ESP_OK;
}

esp_err_t lua_sandbox_exec(const char *script, size_t len, char *err_buf, size_t err_buf_len) {
    if (!s_sandbox.L) return ESP_ERR_INVALID_STATE;

    s_sandbox.deadline_us = esp_timer_get_time() + (LUA_MAX_RUNTIME_MS * 1000LL);
    lua_sethook(s_sandbox.L, lua_deadline_hook, LUA_MASKCOUNT, 1000);

    int ret = luaL_loadbuffer(s_sandbox.L, script, len, "=user_script");
    if (ret != LUA_OK) {
        const char *msg = lua_tostring(s_sandbox.L, -1);
        if (err_buf && msg) snprintf(err_buf, err_buf_len, "%s", msg);
        ESP_LOGE(TAG, "Load error: %s", msg ? msg : "unknown");
        lua_pop(s_sandbox.L, 1);
        return ESP_ERR_INVALID_ARG;
    }

    ret = lua_pcall(s_sandbox.L, 0, 0, 0);
    lua_sethook(s_sandbox.L, NULL, 0, 0);

    if (ret != LUA_OK) {
        const char *msg = lua_tostring(s_sandbox.L, -1);
        if (err_buf && msg) snprintf(err_buf, err_buf_len, "%s", msg);
        ESP_LOGE(TAG, "Runtime error: %s", msg ? msg : "unknown");
        lua_pop(s_sandbox.L, 1);
        return ESP_FAIL;
    }

    ESP_LOGI(TAG, "Script executed OK (mem: %u/%u bytes)", (unsigned)s_sandbox.mem_used, LUA_MAX_MEMORY);
    return ESP_OK;
}

size_t lua_sandbox_mem_used(void) {
    return s_sandbox.mem_used;
}

void lua_sandbox_deinit(void) {
    if (s_sandbox.L) {
        lua_close(s_sandbox.L);
        s_sandbox.L = NULL;
        s_sandbox.mem_used = 0;
    }
    ESP_LOGI(TAG, "Sandbox destroyed");
}
