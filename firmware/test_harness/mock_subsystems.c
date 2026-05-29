/**
 * @file mock_subsystems.c
 * @brief Mock implementations of firmware subsystems for host-side VM testing.
 *
 * Provides: state_store, driver_registry, event_bus, fault_handler
 * All in a single file for simplicity.
 */
#include "esp_mock.h"
#include "system_config.h"
#include "vm.h"
#include "state_store.h"
#include "driver_registry.h"
#include "event_bus.h"
#include "safety.h"

/* ============================================================
 * State Store
 * ============================================================ */
static vm_value_t s_state_vars[SYS_MAX_STATE_VARIABLES];
static uint8_t    s_state_count = 0;

esp_err_t state_store_init(void) {
    memset(s_state_vars, 0, sizeof(s_state_vars));
    s_state_count = 0;
    return ESP_OK;
}

esp_err_t state_store_set(uint8_t index, vm_value_t value) {
    if (index >= SYS_MAX_STATE_VARIABLES) return ESP_FAIL;
    s_state_vars[index] = value;
    if (index >= s_state_count) s_state_count = index + 1;
    return ESP_OK;
}

esp_err_t state_store_get(uint8_t index, vm_value_t *out) {
    if (index >= SYS_MAX_STATE_VARIABLES) return ESP_FAIL;
    *out = s_state_vars[index];
    return ESP_OK;
}

esp_err_t state_store_increment(uint8_t index) {
    if (index >= SYS_MAX_STATE_VARIABLES) return ESP_FAIL;
    if (s_state_vars[index].type == VM_TYPE_INT) {
        s_state_vars[index].i++;
    } else if (s_state_vars[index].type == VM_TYPE_FLOAT) {
        s_state_vars[index].f += 1.0f;
    }
    return ESP_OK;
}

void state_store_reset(void) {
    memset(s_state_vars, 0, sizeof(s_state_vars));
    s_state_count = 0;
}

uint8_t state_store_count(void) { return s_state_count; }

/* ============================================================
 * Driver Registry (mock — returns simulated sensor data)
 * ============================================================ */
#define MAX_REGISTERED_DRIVERS 32
static registered_driver_t s_drivers[MAX_REGISTERED_DRIVERS];
static uint8_t s_driver_count = 0;

/* Mock sensor read: returns simulated value */
static esp_err_t mock_sensor_read(driver_handle_t h, capability_t field, sensor_value_t *out) {
    out->type = VAL_TYPE_FLOAT;
    out->timestamp_ms = (uint32_t)(esp_timer_get_time() / 1000);
    out->error = DRV_OK;
    out->capability = field;

    switch (field) {
        case CAP_TEMPERATURE:    out->f = 24.5f;   break;
        case CAP_HUMIDITY:       out->f = 65.0f;    break;
        case CAP_PRESSURE:       out->f = 1013.25f; break;
        case CAP_SOIL_MOISTURE:  out->f = 45.0f;    break;
        case CAP_LIGHT_LUX:     out->f = 320.0f;   break;
        case CAP_CO2_PPM:        out->f = 415.0f;   break;
        case CAP_DISTANCE:       out->f = 12.5f;    break;
        case CAP_PH_LEVEL:      out->f = 7.2f;     break;
        default:                 out->f = 42.0f;    break;
    }
    printf("[MOCK_DRV] Read driver[%d] cap=%d -> %.2f\n", h.driver_index, field, out->f);
    return ESP_OK;
}

/* Mock actuator write: logs the action */
static esp_err_t mock_actuator_write(driver_handle_t h, const actuator_cmd_t *cmd) {
    printf("[MOCK_DRV] Write driver[%d] cap=%d ", h.driver_index, cmd->capability);
    switch (cmd->type) {
        case VAL_TYPE_FLOAT:  printf("float=%.2f\n", cmd->f); break;
        case VAL_TYPE_INT:    printf("int=%d\n", cmd->i); break;
        case VAL_TYPE_BOOL:   printf("bool=%s\n", cmd->b ? "true" : "false"); break;
        case VAL_TYPE_STRING: printf("text=\"%s\"\n", cmd->s); break;
        default:              printf("unknown\n"); break;
    }
    return ESP_OK;
}

static esp_err_t mock_init(const driver_config_t *cfg) { return ESP_OK; }
static esp_err_t mock_deinit(driver_handle_t h) { return ESP_OK; }

static const driver_meta_t mock_sensor_meta = {
    .name = "mock_sensor", .display_name = "Mock Sensor", .version = "1.0.0",
    .type = DRIVER_TYPE_SENSOR, .bus_type = BUS_TYPE_I2C,
    .capabilities = {CAP_TEMPERATURE, CAP_HUMIDITY, CAP_PRESSURE, CAP_SOIL_MOISTURE},
    .num_capabilities = 4
};

static const driver_meta_t mock_actuator_meta = {
    .name = "mock_actuator", .display_name = "Mock Actuator", .version = "1.0.0",
    .type = DRIVER_TYPE_ACTUATOR, .bus_type = BUS_TYPE_GPIO,
    .capabilities = {CAP_ON_OFF, CAP_SPEED_PERCENT, CAP_ANGLE_DEGREES, CAP_TEXT_DISPLAY},
    .num_capabilities = 4
};

static const driver_vtable_t mock_sensor_vtable = {
    .init = mock_init, .read = mock_sensor_read, .write = NULL, .deinit = mock_deinit,
    .meta = &mock_sensor_meta
};

static const driver_vtable_t mock_actuator_vtable = {
    .init = mock_init, .read = NULL, .write = mock_actuator_write, .deinit = mock_deinit,
    .meta = &mock_actuator_meta
};

esp_err_t driver_registry_init(void) {
    memset(s_drivers, 0, sizeof(s_drivers));
    s_driver_count = 0;
    return ESP_OK;
}

esp_err_t driver_registry_register(uint8_t index, const driver_vtable_t *vtable, const driver_config_t *config) {
    if (index >= MAX_REGISTERED_DRIVERS) return ESP_FAIL;
    s_drivers[index].vtable = vtable;
    if (config) s_drivers[index].config = *config;
    s_drivers[index].handle.driver_index = index;
    s_drivers[index].initialized = true;
    if (index >= s_driver_count) s_driver_count = index + 1;
    return ESP_OK;
}

registered_driver_t *driver_registry_get(uint8_t index) {
    if (index >= MAX_REGISTERED_DRIVERS) return NULL;
    if (!s_drivers[index].initialized) return NULL;
    return &s_drivers[index];
}

uint8_t driver_registry_count(void) { return s_driver_count; }

esp_err_t driver_registry_init_all(void) { return ESP_OK; }
void driver_registry_deinit_all(void) {}

/* Register mock drivers at well-known indices */
void mock_register_default_drivers(void) {
    driver_registry_register(0, &mock_sensor_vtable, NULL);   /* BME280-like */
    driver_registry_register(1, &mock_actuator_vtable, NULL); /* Relay/GPIO */
    driver_registry_register(2, &mock_sensor_vtable, NULL);   /* Soil moisture */
    driver_registry_register(3, &mock_actuator_vtable, NULL); /* Display */
    printf("[MOCK_DRV] Registered 4 mock drivers (sensor@0, actuator@1, sensor@2, display@3)\n");
}

/* ============================================================
 * Event Bus (stub)
 * ============================================================ */
esp_err_t event_bus_init(void) { return ESP_OK; }
esp_err_t event_bus_subscribe(event_type_t type, event_handler_t handler, void *user_data) { return ESP_OK; }
esp_err_t event_bus_publish(const event_t *event) {
    printf("[EVENT] type=%d data=%u\n", event->type, event->data);
    return ESP_OK;
}

/* ============================================================
 * Fault Handler (stub — logs faults)
 * ============================================================ */
static fault_record_t s_faults[FAULT_MAX];
static uint32_t s_total_faults = 0;

esp_err_t fault_handler_init(void) {
    memset(s_faults, 0, sizeof(s_faults));
    s_total_faults = 0;
    return ESP_OK;
}

void fault_raise(fault_type_t type, uint32_t data) {
    if (type >= FAULT_MAX) return;
    s_faults[type].type = type;
    s_faults[type].count++;
    s_faults[type].data = data;
    s_faults[type].last_occurrence = (uint32_t)(esp_timer_get_time() / 1000);
    s_total_faults++;
    printf("[FAULT] type=%d data=%u count=%u\n", type, data, s_faults[type].count);
}

const fault_record_t *fault_get(fault_type_t type) {
    return (type < FAULT_MAX) ? &s_faults[type] : NULL;
}
uint32_t fault_total_count(void) { return s_total_faults; }
void fault_clear_all(void) { memset(s_faults, 0, sizeof(s_faults)); s_total_faults = 0; }

/* Comms mock */
void comms_send_telemetry(const char *json) {
    printf("[COMMS] Telemetry: %s\n", json);
}
