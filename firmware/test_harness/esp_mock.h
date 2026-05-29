/**
 * @file esp_mock.h
 * @brief Mock ESP-IDF types and functions for host-side VM testing.
 *
 * Replaces esp_err.h, esp_log.h, esp_timer.h, freertos/FreeRTOS.h, freertos/task.h
 * so the real vm.c compiles with gcc on x86.
 */
#ifndef ESP_MOCK_H
#define ESP_MOCK_H

#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <math.h>
#include <time.h>

#ifdef __cplusplus
extern "C" {
#endif

/* esp_err.h */
typedef int esp_err_t;
#define ESP_OK              0
#define ESP_FAIL            -1
#define ESP_ERR_INVALID_SIZE -2

/* esp_log.h */
#define ESP_LOGI(tag, fmt, ...) printf("[I][%s] " fmt "\n", tag, ##__VA_ARGS__)
#define ESP_LOGW(tag, fmt, ...) printf("[W][%s] " fmt "\n", tag, ##__VA_ARGS__)
#define ESP_LOGE(tag, fmt, ...) printf("[E][%s] " fmt "\n", tag, ##__VA_ARGS__)
#define ESP_LOGD(tag, fmt, ...) /* noop in test */

/* esp_timer.h */
static inline int64_t esp_timer_get_time(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (int64_t)ts.tv_sec * 1000000LL + ts.tv_nsec / 1000LL;
}

/* freertos stubs */
#define configMAX_PRIORITIES 25
#define pdMS_TO_TICKS(ms) (ms)
static inline void vTaskDelay(uint32_t ticks) {
    /* In test mode, just skip delays */
    (void)ticks;
}

#ifdef __cplusplus
}
#endif
#endif /* ESP_MOCK_H */
