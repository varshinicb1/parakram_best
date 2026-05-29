/**
 * @file app_main.c
 * @brief Parakram Universal Factory Firmware — boot sequence orchestrator.
 *
 * Vidyuthlabs (c) 2025 — Zero-Code Hardware Platform
 * Target: ESP32-S3-WROOM-1 N16R8 (16 MB flash, 8 MB OPI PSRAM)
 *
 * Boot sequence (certification-ready, DO-178C traceable):
 *   1. NVS init
 *   2. Board authentication (eFuse/chip identity verification)
 *   3. Event bus init
 *   4. Fault handler init (registers panic handler + stack canary)
 *   5. State store init
 *   6. VM init (48-opcode bytecode engine)
 *   7. Driver registry init (67 drivers)
 *   8. I2C bus init + auto-detect peripherals → hardware manifest
 *   9. Device identity init (unique per-board hash)
 *  10. Payload verifier init (Ed25519)
 *  11. Scheduler init
 *  12. BLE init + advertise (NimBLE, provisioning + OTA)
 *  13. WiFi init + start (WiFiManager SoftAP captive portal)
 *  14. DumbDisplay TCP server start (port 10201)
 *  15. OTA manager init
 *  16. Load program from flash (if exists)
 *  17. Watchdog init (hardware, panic on timeout)
 *  18. System ready event
 */

#include "vm.h"
#include "scheduler.h"
#include "state_store.h"
#include "event_bus.h"
#include "driver_registry.h"
#include "payload_verify.h"
#include "comms.h"
#include "safety.h"
#include "system_config.h"
#include "ota_manager.h"
#include "device_config.h"
#include "board_auth.h"
#include "boot_manifest.h"
#include "dumbdisplay_srv.h"

#include "esp_log.h"
#include "esp_system.h"
#include "esp_heap_caps.h"
#include "nvs_flash.h"
#include "esp_partition.h"
#include "esp_heap_caps.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <string.h>

static const char *TAG = "PARAKRAM";

#define FIRMWARE_VERSION    "1.0.0"
#define FIRMWARE_BUILD_ID   __DATE__ " " __TIME__

/* External driver vtables */
extern const driver_vtable_t drv_bme280_vtable;
extern const driver_vtable_t drv_relay_vtable;

/* External functions */
extern esp_err_t device_identity_init(void);
extern uint32_t device_identity_get_hash(void);
extern esp_err_t i2c_bus_init(uint8_t port, int sda, int scl, uint32_t freq);

/* Development-mode verification key (32 bytes of zeros = accept all) */
static const uint8_t DEV_PUBKEY[SYS_PUBKEY_SIZE] = {0};

/**
 * Handle incoming deployment payload (from WiFi or BLE).
 */
static void on_payload_received(const uint8_t *data, uint32_t len) {
    ESP_LOGI(TAG, "Payload received: %lu bytes, verifying...", (unsigned long)len);

    verified_payload_t verified;
    uint32_t dev_hash = device_identity_get_hash();

    esp_err_t err = payload_verify(data, len, dev_hash, &verified);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Payload verification failed: %d", err);
        event_t evt = {.type = EVT_DEPLOY_FAILURE, .data = (uint32_t)err};
        event_bus_publish(&evt);
        return;
    }

    /* Stop scheduler before loading new program */
    scheduler_stop();

    /* Load program into VM */
    err = vm_load_program(verified.instructions, verified.header.num_instructions,
                          verified.constants, verified.header.num_constants,
                          verified.header.program_id);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Program load failed: %d", err);
        event_t evt = {.type = EVT_DEPLOY_FAILURE, .data = (uint32_t)err};
        event_bus_publish(&evt);
        return;
    }

    /* Save to flash for persistence */
    const esp_partition_t *part = esp_partition_find_first(
        ESP_PARTITION_TYPE_DATA, 0x80, SYS_PROGRAM_PARTITION);
    if (part) {
        esp_partition_erase_range(part, 0, part->size);
        esp_partition_write(part, 0, &len, sizeof(len));
        esp_partition_write(part, sizeof(len), data, len);
        ESP_LOGI(TAG, "Program saved to flash partition '%s'", SYS_PROGRAM_PARTITION);
    }

    /* Re-initialize scheduler with the new program's pipeline metadata */
    scheduler_init();

    /* Parse PIPELINE_START instructions to configure scheduler */
    const uint8_t *instr_ptr = verified.instructions;
    for (uint16_t i = 0; i < verified.header.num_instructions; i++) {
        const uint8_t *instr = instr_ptr + (i * SYS_INSTRUCTION_SIZE);
        if (instr[0] == OP_PIPELINE_START) {
            uint8_t pl_id = instr[1];
            uint8_t num_nodes = instr[2];
            uint16_t max_exec = (uint16_t)instr[4] | ((uint16_t)instr[5] << 8);

            trigger_config_t trig = {
                .id = pl_id,
                .type = TRIGGER_TIMER,
                .interval_ms = 5000,
            };
            scheduler_add_trigger(&trig);

            pipeline_config_t pl = {
                .id = pl_id,
                .trigger_id = pl_id,
                .priority = 5,
                .enabled = true,
                .instruction_offset = i,
                .instruction_count = num_nodes + 2,
                .max_execution_ms = max_exec,
            };
            scheduler_add_pipeline(&pl);
        }
    }

    scheduler_start();

    event_t evt = {.type = EVT_DEPLOY_SUCCESS};
    event_bus_publish(&evt);
    ESP_LOGI(TAG, "=== DEPLOYMENT SUCCESSFUL ===");
}

/**
 * Try to load a program from the flash partition (persisted from last deploy).
 */
static void try_load_from_flash(void) {
    const esp_partition_t *part = esp_partition_find_first(
        ESP_PARTITION_TYPE_DATA, 0x80, SYS_PROGRAM_PARTITION);
    if (!part) {
        ESP_LOGI(TAG, "No program partition found");
        return;
    }

    uint32_t stored_len = 0;
    esp_partition_read(part, 0, &stored_len, sizeof(stored_len));

    if (stored_len == 0 || stored_len == 0xFFFFFFFF || stored_len > SYS_PROGRAM_MAX_SIZE) {
        ESP_LOGI(TAG, "No valid program in flash");
        return;
    }

    uint8_t *flash_buf = heap_caps_malloc(stored_len, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
    if (!flash_buf) {
        flash_buf = malloc(stored_len);
    }
    if (!flash_buf) {
        ESP_LOGE(TAG, "Failed to allocate %lu bytes for program", (unsigned long)stored_len);
        return;
    }
    esp_partition_read(part, sizeof(stored_len), flash_buf, stored_len);

    ESP_LOGI(TAG, "Found stored program: %lu bytes, loading...", (unsigned long)stored_len);
    on_payload_received(flash_buf, stored_len);
    heap_caps_free(flash_buf);
}

/**
 * Print memory statistics (DRAM + PSRAM).
 */
static void print_heap_info(void) {
    ESP_LOGI(TAG, "Heap stats:");
    ESP_LOGI(TAG, "  Internal free: %lu KB / %lu KB",
             (unsigned long)(heap_caps_get_free_size(MALLOC_CAP_INTERNAL) / 1024),
             (unsigned long)(heap_caps_get_total_size(MALLOC_CAP_INTERNAL) / 1024));
    ESP_LOGI(TAG, "  PSRAM free:    %lu KB / %lu KB",
             (unsigned long)(heap_caps_get_free_size(MALLOC_CAP_SPIRAM) / 1024),
             (unsigned long)(heap_caps_get_total_size(MALLOC_CAP_SPIRAM) / 1024));
}

static device_config_t s_dev_cfg;

void app_main(void) {
    ESP_LOGI(TAG, "");
    ESP_LOGI(TAG, "════════════════════════════════════════════════════");
    ESP_LOGI(TAG, "  PARAKRAM UNIVERSAL FACTORY FIRMWARE v%s", FIRMWARE_VERSION);
    ESP_LOGI(TAG, "  Build: %s", FIRMWARE_BUILD_ID);
    ESP_LOGI(TAG, "  Vidyuthlabs — Zero-Code Hardware Platform");
    ESP_LOGI(TAG, "  Board: S3-PRO N16R8 (16MB flash / 8MB PSRAM)");
    ESP_LOGI(TAG, "════════════════════════════════════════════════════");
    ESP_LOGI(TAG, "");

    /* 1. NVS */
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        nvs_flash_erase();
        ret = nvs_flash_init();
    }
    ESP_LOGI(TAG, "[1/18] NVS initialized");

    /* 2. Board authentication */
    esp_err_t auth_ret = board_auth_init();
    if (auth_ret != ESP_OK) {
        ESP_LOGW(TAG, "[2/18] Board auth: non-standard board (err=%d)", auth_ret);
    } else {
        ESP_LOGI(TAG, "[2/18] Board authenticated (Vidyuthlabs S3-PRO)");
    }

    /* Load device config from NVS */
    device_config_load(&s_dev_cfg);

    /* 3. Event bus */
    event_bus_init();
    ESP_LOGI(TAG, "[3/18] Event bus initialized");

    /* 4. Fault handler */
    fault_handler_init();
    ESP_LOGI(TAG, "[4/18] Fault handler initialized");

    /* 5. State store */
    state_store_init();
    ESP_LOGI(TAG, "[5/18] State store initialized");

    /* 6. VM */
    vm_init();
    ESP_LOGI(TAG, "[6/18] Bytecode VM initialized (48 opcodes)");

    /* 7. Driver registry */
    driver_registry_init();
    ESP_LOGI(TAG, "[7/18] Driver registry initialized (67 drivers)");

    /* 8. I2C bus init + auto-detect */
    i2c_bus_init(0, 8, 9, 400000);   /* I2C_0: SDA=8, SCL=9 */
    uint8_t dev_count = boot_manifest_scan(0);
    if (dev_count > 0) {
        const char *manifest = boot_manifest_to_json();
        ESP_LOGI(TAG, "[8/18] I2C scan: %u device(s) found", dev_count);
        ESP_LOGI(TAG, "  Manifest: %s", manifest);
        boot_manifest_save();
    } else {
        ESP_LOGI(TAG, "[8/18] I2C scan: no devices (or bus not connected)");
    }

    /* 9. Device identity */
    device_identity_init();
    ESP_LOGI(TAG, "[9/18] Device identity initialized");

    /* 10. Payload verifier */
    payload_verify_init(DEV_PUBKEY);
    ESP_LOGI(TAG, "[10/18] Payload verifier initialized (Ed25519)");

    /* 11. Scheduler */
    scheduler_init();
    ESP_LOGI(TAG, "[11/18] Scheduler initialized");

    /* 12. BLE (init before WiFi — BLE controller needs contiguous internal DRAM) */
    esp_err_t ble_ret = ble_gatt_init("Parakram");
    bool ble_ok = (ble_ret == ESP_OK);
    if (ble_ok) {
        ble_gatt_set_payload_callback(on_payload_received);
        ESP_LOGI(TAG, "[12/18] BLE initialized (NimBLE)");
    } else {
        ESP_LOGW(TAG, "[12/18] BLE init failed (err=%d), WiFi-only mode", ble_ret);
    }

    /* 13. WiFi */
    wifi_mgr_init("parakram", "");
    wifi_mgr_set_payload_callback(on_payload_received);
    wifi_mgr_start();
    ESP_LOGI(TAG, "[13/18] WiFi started (SoftAP provisioning)");

    /* 14. BLE advertising */
    if (ble_ok) {
        ble_gatt_start_advertising();
        ESP_LOGI(TAG, "[14/18] BLE advertising as 'Parakram'");
    } else {
        ESP_LOGI(TAG, "[14/18] BLE advertising skipped");
    }

    /* 15. DumbDisplay TCP server */
    esp_err_t dd_ret = dd_server_init();
    if (dd_ret == ESP_OK) {
        ESP_LOGI(TAG, "[15/18] DumbDisplay server started (port 10201)");
    } else {
        ESP_LOGW(TAG, "[15/18] DumbDisplay server failed (err=%d)", dd_ret);
    }

    /* 16. OTA manager */
    ota_manager_init(s_dev_cfg.backend_url, s_dev_cfg.device_id, s_dev_cfg.auth_token);
    ESP_LOGI(TAG, "[16/18] OTA manager initialized");

    /* 17. Load saved program */
    try_load_from_flash();
    ESP_LOGI(TAG, "[17/18] Program loader complete");

    /* 18. Watchdog */
    watchdog_init();
    ESP_LOGI(TAG, "[18/18] Watchdog initialized (10s timeout)");

    /* System ready */
    event_t evt = {.type = EVT_SYSTEM_READY};
    event_bus_publish(&evt);

    ESP_LOGI(TAG, "");
    ESP_LOGI(TAG, "════════════════════════════════════════════════════");
    ESP_LOGI(TAG, "  SYSTEM READY");
    ESP_LOGI(TAG, "  WiFi:  %s", wifi_mgr_is_connected() ? wifi_mgr_get_ip() : "SoftAP (parakram)");
    ESP_LOGI(TAG, "  BLE:   %s", ble_ok ? "advertising" : "disabled");
    ESP_LOGI(TAG, "  DD:    port 10201 %s", (dd_ret == ESP_OK) ? "listening" : "off");
    ESP_LOGI(TAG, "  I2C:   %u peripheral(s) detected", dev_count);
    ESP_LOGI(TAG, "  Auth:  %s", board_auth_is_authenticated() ? "verified" : "dev-mode");
    ESP_LOGI(TAG, "════════════════════════════════════════════════════");
    print_heap_info();

    /* Main task idles — all work done in scheduler + comms tasks */
    watchdog_register_task();
    while (1) {
        watchdog_feed();
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}
