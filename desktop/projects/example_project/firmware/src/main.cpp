// Parakram AI — Auto-generated firmware
// Project nodes: 3
// Project edges: 1

#include <Arduino.h>
#include "temperature_sensor.h"
#include "threshold_logic.h"
#include "wifi.h"

void setup() {
    Serial.begin(115200);
    delay(1000);
    Serial.println("=== Parakram AI Firmware ===");
    Serial.println("Initializing modules...");

    temperature_sensor_setup();
    threshold_logic_setup();
    wifi_setup();

    Serial.println("All modules initialized.");
}

void loop() {
    temperature_sensor_loop();
    threshold_logic_loop();
    wifi_loop();
    delay(10);
}
