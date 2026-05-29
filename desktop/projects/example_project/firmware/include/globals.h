#ifndef GLOBALS_H
#define GLOBALS_H

#include <Arduino.h>

// === Pin Definitions ===========================
#define PIN_TEMPERATURE_SENSOR 4

// === I2C Bus Configuration ========================

// === Shared State Variables =======================
extern float temperature_sensor_temperature;
extern float temperature_sensor_humidity;
extern bool threshold_logic_triggered;
extern bool wifi_connected;
extern float filter_temperature_sensortemperature_smoothed;

#endif // GLOBALS_H
