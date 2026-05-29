// Parakram AI — WiFi Module Template
// Template for WiFi connectivity blocks

#include "{{MODULE_NAME}}.h"
#include <WiFi.h>

// Configuration
static const char *WIFI_SSID = "{{SSID}}";
static const char *WIFI_PASS = "{{PASSWORD}}";
static bool autoReconnect = {{AUTO_RECONNECT}};

static bool wifiConnected = false;
static unsigned long lastCheck = 0;
static const unsigned long CHECK_INTERVAL = 10000;

void {
  {
    MODULE_NAME
  }
}
_setup() {
  Serial.println("[{{MODULE_NAME}}] Connecting to WiFi...");
  Serial.print("[{{MODULE_NAME}}] SSID: ");
  Serial.println(WIFI_SSID);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    wifiConnected = true;
    Serial.println();
    Serial.print("[{{MODULE_NAME}}] Connected! IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println();
    Serial.println("[{{MODULE_NAME}}] Connection failed");
  }
}

void {
  {
    MODULE_NAME
  }
}
_loop() {
  unsigned long now = millis();
  if (now - lastCheck < CHECK_INTERVAL)
    return;
  lastCheck = now;

  if (WiFi.status() != WL_CONNECTED) {
    wifiConnected = false;
    if (autoReconnect) {
      Serial.println("[{{MODULE_NAME}}] Reconnecting...");
      WiFi.reconnect();
    }
  } else {
    wifiConnected = true;
  }
}

bool {
  {
    MODULE_NAME
  }
}
_is_connected() { return wifiConnected; }
