// Parakram AI — Sensor Module Template
// Template for sensor blocks (DHT22, BMP280, etc.)

#include "{{MODULE_NAME}}.h"
#include <{{LIBRARY}}>

// Configuration
static const int DATA_PIN = {{PIN}};
static unsigned long lastRead = 0;
static const unsigned long READ_INTERVAL = {{READ_INTERVAL}};

// Sensor instance
{
  {
    SENSOR_INSTANCE
  }
}

void {
  {
    MODULE_NAME
  }
}
_setup() {
  Serial.print("[{{MODULE_NAME}}] Initializing on pin ");
  Serial.println(DATA_PIN);

  {
    {
      SENSOR_INIT
    }
  }

  Serial.println("[{{MODULE_NAME}}] Ready");
}

void {
  {
    MODULE_NAME
  }
}
_loop() {
  unsigned long now = millis();
  if (now - lastRead < READ_INTERVAL)
    return;
  lastRead = now;

  {
    {
      SENSOR_READ
    }
  }

  // Output values via Serial
  {
    {
      SERIAL_OUTPUT
    }
  }
}
