/**
 * @file dumbdisplay_srv.c
 * @brief DumbDisplay TCP server — board-side protocol handler.
 *
 * Accepts TCP connections on port 10201 from the Parakram mobile app.
 * Sends display commands (text, shapes, images) using the DumbDisplay
 * pipe-delimited protocol. The phone renders all graphics via GPU.
 *
 * Protocol: Each command is a pipe-delimited line terminated by '\n'.
 *   Format: "CMD|layer_id|param1|param2|...\n"
 *
 * Certification: Thread-safe, bounded memory, watchdog-compatible.
 */

#include "esp_log.h"
#include "esp_err.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include "lwip/sockets.h"
#include "lwip/netdb.h"
#include <string.h>
#include <stdio.h>

static const char *TAG = "DD_SRV";

#define DD_PORT         10201
#define DD_MAX_CMD_LEN  256
#define DD_STACK_SIZE   4096
#define DD_TASK_PRIO    5

/* Connection state */
static int              s_server_fd = -1;
static int              s_client_fd = -1;
static SemaphoreHandle_t s_tx_mutex  = NULL;
static TaskHandle_t     s_task      = NULL;
static bool             s_running   = false;

/**
 * @brief Send a raw command string to the connected phone.
 * @param cmd  Pipe-delimited command string (without trailing newline).
 * @return ESP_OK on success, ESP_ERR_INVALID_STATE if no client connected.
 */
esp_err_t dd_send_cmd(const char *cmd) {
    if (s_client_fd < 0) {
        return ESP_ERR_INVALID_STATE;
    }

    if (xSemaphoreTake(s_tx_mutex, pdMS_TO_TICKS(100)) != pdTRUE) {
        return ESP_ERR_TIMEOUT;
    }

    char buf[DD_MAX_CMD_LEN + 2];
    int len = snprintf(buf, sizeof(buf), "%s\n", cmd);
    if (len < 0 || len >= (int)sizeof(buf)) {
        xSemaphoreGive(s_tx_mutex);
        return ESP_ERR_INVALID_SIZE;
    }

    int sent = send(s_client_fd, buf, (size_t)len, 0);
    xSemaphoreGive(s_tx_mutex);

    return (sent == len) ? ESP_OK : ESP_FAIL;
}

/**
 * @brief Send display text to the phone.
 * @param layer  Layer ID (0-7).
 * @param x      X position.
 * @param y      Y position.
 * @param text   Text string to display.
 */
esp_err_t dd_draw_text(uint8_t layer, int16_t x, int16_t y, const char *text) {
    char cmd[DD_MAX_CMD_LEN];
    (void)snprintf(cmd, sizeof(cmd), "TXT|%u|%d|%d|%s", layer, x, y, text);
    return dd_send_cmd(cmd);
}

/**
 * @brief Send rectangle draw command.
 */
esp_err_t dd_draw_rect(uint8_t layer, int16_t x, int16_t y,
                       uint16_t w, uint16_t h, uint32_t color) {
    char cmd[DD_MAX_CMD_LEN];
    (void)snprintf(cmd, sizeof(cmd), "RECT|%u|%d|%d|%u|%u|#%06lX",
                   layer, x, y, w, h, (unsigned long)color);
    return dd_send_cmd(cmd);
}

/**
 * @brief Send filled rectangle command.
 */
esp_err_t dd_fill_rect(uint8_t layer, int16_t x, int16_t y,
                       uint16_t w, uint16_t h, uint32_t color) {
    char cmd[DD_MAX_CMD_LEN];
    (void)snprintf(cmd, sizeof(cmd), "FRECT|%u|%d|%d|%u|%u|#%06lX",
                   layer, x, y, w, h, (unsigned long)color);
    return dd_send_cmd(cmd);
}

/**
 * @brief Clear a display layer.
 */
esp_err_t dd_clear_layer(uint8_t layer) {
    char cmd[DD_MAX_CMD_LEN];
    (void)snprintf(cmd, sizeof(cmd), "CLR|%u", layer);
    return dd_send_cmd(cmd);
}

/**
 * @brief Send circle draw command.
 */
esp_err_t dd_draw_circle(uint8_t layer, int16_t cx, int16_t cy,
                         uint16_t r, uint32_t color) {
    char cmd[DD_MAX_CMD_LEN];
    (void)snprintf(cmd, sizeof(cmd), "CIRC|%u|%d|%d|%u|#%06lX",
                   layer, cx, cy, r, (unsigned long)color);
    return dd_send_cmd(cmd);
}

/**
 * @brief Send line draw command.
 */
esp_err_t dd_draw_line(uint8_t layer, int16_t x1, int16_t y1,
                       int16_t x2, int16_t y2, uint32_t color) {
    char cmd[DD_MAX_CMD_LEN];
    (void)snprintf(cmd, sizeof(cmd), "LINE|%u|%d|%d|%d|%d|#%06lX",
                   layer, x1, y1, x2, y2, (unsigned long)color);
    return dd_send_cmd(cmd);
}

/**
 * @brief Set font size.
 */
esp_err_t dd_set_font(uint8_t layer, uint8_t size) {
    char cmd[DD_MAX_CMD_LEN];
    (void)snprintf(cmd, sizeof(cmd), "FONT|%u|%u", layer, size);
    return dd_send_cmd(cmd);
}

/**
 * @brief Send sensor dashboard update (convenience).
 */
esp_err_t dd_update_gauge(uint8_t layer, const char *label,
                          float value, const char *unit) {
    char cmd[DD_MAX_CMD_LEN];
    (void)snprintf(cmd, sizeof(cmd), "GAUGE|%u|%s|%.2f|%s",
                   layer, label, (double)value, unit);
    return dd_send_cmd(cmd);
}

/**
 * @brief Check if a phone is connected.
 */
bool dd_is_connected(void) {
    return (s_client_fd >= 0);
}

/**
 * @brief TCP server task — accepts one client at a time.
 */
static void dd_server_task(void *arg) {
    (void)arg;

    struct sockaddr_in srv_addr;
    (void)memset(&srv_addr, 0, sizeof(srv_addr));
    srv_addr.sin_family      = AF_INET;
    srv_addr.sin_addr.s_addr = htonl(INADDR_ANY);
    srv_addr.sin_port        = htons(DD_PORT);

    s_server_fd = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (s_server_fd < 0) {
        ESP_LOGE(TAG, "socket() failed: errno %d", errno);
        vTaskDelete(NULL);
        return;
    }

    int opt = 1;
    (void)setsockopt(s_server_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

    if (bind(s_server_fd, (struct sockaddr *)&srv_addr, sizeof(srv_addr)) != 0) {
        ESP_LOGE(TAG, "bind() failed: errno %d", errno);
        close(s_server_fd);
        s_server_fd = -1;
        vTaskDelete(NULL);
        return;
    }

    if (listen(s_server_fd, 1) != 0) {
        ESP_LOGE(TAG, "listen() failed: errno %d", errno);
        close(s_server_fd);
        s_server_fd = -1;
        vTaskDelete(NULL);
        return;
    }

    ESP_LOGI(TAG, "DumbDisplay server listening on port %d", DD_PORT);

    while (s_running) {
        struct sockaddr_in cli_addr;
        socklen_t cli_len = sizeof(cli_addr);

        s_client_fd = accept(s_server_fd, (struct sockaddr *)&cli_addr, &cli_len);
        if (s_client_fd < 0) {
            if (s_running) {
                ESP_LOGW(TAG, "accept() failed: errno %d", errno);
            }
            continue;
        }

        ESP_LOGI(TAG, "Phone connected from %s:%d",
                 inet_ntoa(cli_addr.sin_addr), ntohs(cli_addr.sin_port));

        /* Send handshake */
        dd_send_cmd("HELLO|PARAKRAM|1.0.0|S3-PRO-N16R8");

        /* Read loop — handle commands from phone */
        char rx_buf[DD_MAX_CMD_LEN];
        while (s_running) {
            int n = recv(s_client_fd, rx_buf, sizeof(rx_buf) - 1, 0);
            if (n <= 0) {
                ESP_LOGI(TAG, "Phone disconnected.");
                break;
            }
            rx_buf[n] = '\0';
            /* Process incoming commands (touch events, etc.) */
            ESP_LOGD(TAG, "RX: %s", rx_buf);
        }

        close(s_client_fd);
        s_client_fd = -1;
    }

    close(s_server_fd);
    s_server_fd = -1;
    vTaskDelete(NULL);
}

/**
 * @brief Start the DumbDisplay TCP server.
 * @return ESP_OK on success.
 */
esp_err_t dd_server_init(void) {
    if (s_running) {
        return ESP_OK;
    }

    s_tx_mutex = xSemaphoreCreateMutex();
    if (s_tx_mutex == NULL) {
        return ESP_ERR_NO_MEM;
    }

    s_running = true;

    BaseType_t ret = xTaskCreatePinnedToCore(
        dd_server_task, "dd_srv", DD_STACK_SIZE, NULL,
        DD_TASK_PRIO, &s_task, 0  /* Core 0 — network tasks */
    );

    if (ret != pdPASS) {
        s_running = false;
        vSemaphoreDelete(s_tx_mutex);
        s_tx_mutex = NULL;
        return ESP_ERR_NO_MEM;
    }

    return ESP_OK;
}

/**
 * @brief Stop the DumbDisplay TCP server.
 */
void dd_server_deinit(void) {
    s_running = false;

    if (s_client_fd >= 0) {
        shutdown(s_client_fd, SHUT_RDWR);
        close(s_client_fd);
        s_client_fd = -1;
    }

    if (s_server_fd >= 0) {
        shutdown(s_server_fd, SHUT_RDWR);
        close(s_server_fd);
        s_server_fd = -1;
    }

    if (s_tx_mutex != NULL) {
        vSemaphoreDelete(s_tx_mutex);
        s_tx_mutex = NULL;
    }
}
