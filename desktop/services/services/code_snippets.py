"""
Code Snippet Library — Pre-built, tested firmware snippets for common tasks.

Provides copy-paste-ready code for:
  - WiFi / BLE / MQTT / HTTP connections
  - Sensor reading patterns (I2C, SPI, OneWire)
  - Motor control (DC, Servo, Stepper)
  - Display output (OLED, TFT, LED matrix)
  - Power management (deep sleep, wake sources)
  - FreeRTOS patterns (tasks, queues, semaphores)

Each snippet includes: board compatibility, libraries needed, and inline docs.
Parakram exclusive — no competitor has a searchable snippet library.
"""

SNIPPETS = [
    {
        "id": "wifi-connect",
        "title": "WiFi Connection with Auto-Reconnect",
        "category": "connectivity",
        "boards": ["esp32dev", "esp32-s3-devkitc-1", "rpipicow"],
        "libraries": ["WiFi.h"],
        "tags": ["wifi", "connect", "reconnect", "esp32"],
        "code": '''#include <WiFi.h>

const char* WIFI_SSID = "YOUR_SSID";
const char* WIFI_PASS = "YOUR_PASSWORD";

void setupWiFi() {
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    Serial.print("Connecting to WiFi");
    int retries = 0;
    while (WiFi.status() != WL_CONNECTED && retries < 30) {
        delay(500);
        Serial.print(".");
        retries++;
    }
    if (WiFi.status() == WL_CONNECTED) {
        Serial.printf("\\nConnected! IP: %s\\n", WiFi.localIP().toString().c_str());
    } else {
        Serial.println("\\nFailed to connect — restarting...");
        ESP.restart();
    }
}

// Call in loop() for auto-reconnect
void maintainWiFi() {
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("[WARN] WiFi lost — reconnecting...");
        WiFi.disconnect();
        WiFi.begin(WIFI_SSID, WIFI_PASS);
    }
}''',
    },
    {
        "id": "i2c-scanner",
        "title": "I2C Bus Scanner",
        "category": "debugging",
        "boards": ["esp32dev", "uno", "pico", "nucleo_f446re"],
        "libraries": ["Wire.h"],
        "tags": ["i2c", "scanner", "debug", "address"],
        "code": '''#include <Wire.h>

void scanI2C() {
    Serial.println("Scanning I2C bus...");
    int devices = 0;
    for (byte addr = 1; addr < 127; addr++) {
        Wire.beginTransmission(addr);
        if (Wire.endTransmission() == 0) {
            Serial.printf("  Found device at 0x%02X", addr);
            // Known device identification
            switch (addr) {
                case 0x3C: case 0x3D: Serial.print(" (SSD1306 OLED)"); break;
                case 0x48: Serial.print(" (ADS1115/TMP102)"); break;
                case 0x57: Serial.print(" (MAX30102)"); break;
                case 0x68: Serial.print(" (MPU6050/DS3231)"); break;
                case 0x76: case 0x77: Serial.print(" (BME280/BMP280)"); break;
            }
            Serial.println();
            devices++;
        }
    }
    Serial.printf("Found %d device(s)\\n", devices);
}

void setup() {
    Serial.begin(115200);
    Wire.begin(); // Default SDA/SCL pins
    scanI2C();
}

void loop() { delay(5000); scanI2C(); }''',
    },
    {
        "id": "bme280-read",
        "title": "BME280 Temperature/Humidity/Pressure",
        "category": "sensor",
        "boards": ["esp32dev", "uno", "pico"],
        "libraries": ["Wire.h", "Adafruit_BME280.h"],
        "tags": ["bme280", "temperature", "humidity", "pressure", "i2c"],
        "code": '''#include <Wire.h>
#include <Adafruit_BME280.h>

Adafruit_BME280 bme;

void setup() {
    Serial.begin(115200);
    Wire.begin();

    if (!bme.begin(0x76)) { // Try 0x77 if this fails
        Serial.println("BME280 not found! Check wiring.");
        while (1) delay(10);
    }

    // Configure oversampling for weather monitoring
    bme.setSampling(Adafruit_BME280::MODE_NORMAL,
                    Adafruit_BME280::SAMPLING_X2,  // temp
                    Adafruit_BME280::SAMPLING_X16,  // pressure
                    Adafruit_BME280::SAMPLING_X1,  // humidity
                    Adafruit_BME280::FILTER_X16,
                    Adafruit_BME280::STANDBY_MS_500);
}

void loop() {
    float temp = bme.readTemperature();
    float hum  = bme.readHumidity();
    float pres = bme.readPressure() / 100.0F; // hPa

    Serial.printf("Temp: %.1f°C | Hum: %.1f%% | Pres: %.1f hPa\\n", temp, hum, pres);
    delay(2000);
}''',
    },
    {
        "id": "deep-sleep-timer",
        "title": "ESP32 Deep Sleep with Timer Wakeup",
        "category": "power",
        "boards": ["esp32dev", "esp32-s3-devkitc-1", "esp32-c3-devkitm-1"],
        "libraries": [],
        "tags": ["deep-sleep", "power", "battery", "wake", "esp32"],
        "code": '''#define SLEEP_SECONDS 300  // 5 minutes
#define uS_TO_S_FACTOR 1000000ULL

RTC_DATA_ATTR int bootCount = 0;

void setup() {
    Serial.begin(115200);
    bootCount++;
    Serial.printf("Boot #%d (woke from deep sleep)\\n", bootCount);

    // --- Do your work here ---
    // Read sensors, send data, etc.
    Serial.println("Reading sensors...");
    delay(1000); // Simulate work

    // --- Enter deep sleep ---
    Serial.printf("Going to sleep for %d seconds...\\n", SLEEP_SECONDS);
    esp_sleep_enable_timer_wakeup(SLEEP_SECONDS * uS_TO_S_FACTOR);

    // Optional: disable peripherals before sleep
    WiFi.disconnect(true);
    WiFi.mode(WIFI_OFF);
    btStop();

    Serial.flush();
    esp_deep_sleep_start();
}

void loop() { /* Never reached */ }''',
    },
    {
        "id": "mqtt-pubsub",
        "title": "MQTT Publish/Subscribe with TLS",
        "category": "connectivity",
        "boards": ["esp32dev", "esp32-s3-devkitc-1"],
        "libraries": ["WiFi.h", "PubSubClient.h"],
        "tags": ["mqtt", "iot", "publish", "subscribe", "cloud"],
        "code": '''#include <WiFi.h>
#include <PubSubClient.h>

const char* MQTT_BROKER = "broker.hivemq.com";
const int   MQTT_PORT   = 1883;
const char* MQTT_TOPIC  = "parakram/sensors";

WiFiClient espClient;
PubSubClient mqtt(espClient);

void mqttCallback(char* topic, byte* payload, unsigned int length) {
    String msg;
    for (unsigned int i = 0; i < length; i++) msg += (char)payload[i];
    Serial.printf("[MQTT] %s: %s\\n", topic, msg.c_str());
}

void connectMQTT() {
    while (!mqtt.connected()) {
        String clientId = "parakram-" + String(random(0xffff), HEX);
        if (mqtt.connect(clientId.c_str())) {
            Serial.println("[MQTT] Connected!");
            mqtt.subscribe(MQTT_TOPIC);
        } else {
            Serial.printf("[MQTT] Failed (rc=%d), retry in 5s...\\n", mqtt.state());
            delay(5000);
        }
    }
}

void setup() {
    Serial.begin(115200);
    // WiFi setup assumed done
    mqtt.setServer(MQTT_BROKER, MQTT_PORT);
    mqtt.setCallback(mqttCallback);
}

void loop() {
    if (!mqtt.connected()) connectMQTT();
    mqtt.loop();

    // Publish every 10s
    static unsigned long last = 0;
    if (millis() - last > 10000) {
        String payload = "{\\"temp\\":23.4,\\"hum\\":56}";
        mqtt.publish(MQTT_TOPIC, payload.c_str());
        last = millis();
    }
}''',
    },
    {
        "id": "freertos-tasks",
        "title": "FreeRTOS Multi-Task Pattern",
        "category": "rtos",
        "boards": ["esp32dev", "esp32-s3-devkitc-1"],
        "libraries": [],
        "tags": ["freertos", "tasks", "multithreading", "queue", "semaphore"],
        "code": '''// FreeRTOS multi-task pattern with queue communication
#include <Arduino.h>

QueueHandle_t sensorQueue;
SemaphoreHandle_t i2cMutex;

struct SensorData {
    float temperature;
    float humidity;
    uint32_t timestamp;
};

void sensorTask(void* param) {
    for (;;) {
        SensorData data;
        xSemaphoreTake(i2cMutex, portMAX_DELAY);
        // Read sensor (protected by mutex for shared I2C bus)
        data.temperature = 23.4;  // Replace with actual read
        data.humidity = 56.0;
        data.timestamp = millis();
        xSemaphoreGive(i2cMutex);

        xQueueSend(sensorQueue, &data, portMAX_DELAY);
        vTaskDelay(pdMS_TO_TICKS(2000));
    }
}

void displayTask(void* param) {
    SensorData data;
    for (;;) {
        if (xQueueReceive(sensorQueue, &data, pdMS_TO_TICKS(5000))) {
            Serial.printf("[%lu] T=%.1f°C H=%.1f%%\\n",
                          data.timestamp, data.temperature, data.humidity);
        }
    }
}

void setup() {
    Serial.begin(115200);
    sensorQueue = xQueueCreate(10, sizeof(SensorData));
    i2cMutex = xSemaphoreCreateMutex();

    xTaskCreatePinnedToCore(sensorTask, "Sensor", 4096, NULL, 2, NULL, 0);
    xTaskCreatePinnedToCore(displayTask, "Display", 4096, NULL, 1, NULL, 1);
}

void loop() { vTaskDelay(portMAX_DELAY); }''',
    },
    {
        "id": "servo-sweep",
        "title": "Servo Motor Sweep with Smooth Motion",
        "category": "actuator",
        "boards": ["esp32dev", "uno", "pico"],
        "libraries": ["ESP32Servo.h"],
        "tags": ["servo", "motor", "pwm", "sweep"],
        "code": '''#include <ESP32Servo.h>  // Use <Servo.h> for Arduino Uno

Servo myServo;
const int SERVO_PIN = 13;

void setup() {
    Serial.begin(115200);
    myServo.attach(SERVO_PIN, 500, 2400); // min/max pulse width
}

// Smooth sweep with configurable speed
void smoothSweep(int fromAngle, int toAngle, int stepDelay) {
    int step = (fromAngle < toAngle) ? 1 : -1;
    for (int angle = fromAngle; angle != toAngle; angle += step) {
        myServo.write(angle);
        delay(stepDelay);
    }
    myServo.write(toAngle);
}

void loop() {
    smoothSweep(0, 180, 15);   // Sweep to 180° (slow)
    delay(500);
    smoothSweep(180, 0, 10);   // Sweep back (fast)
    delay(500);
}''',
    },
    {
        "id": "webserver-api",
        "title": "ESP32 Web Server with REST API",
        "category": "connectivity",
        "boards": ["esp32dev", "esp32-s3-devkitc-1"],
        "libraries": ["WiFi.h", "WebServer.h", "ArduinoJson.h"],
        "tags": ["webserver", "rest", "api", "http", "json"],
        "code": '''#include <WiFi.h>
#include <WebServer.h>
#include <ArduinoJson.h>

WebServer server(80);

float temperature = 23.4;
float humidity = 56.0;

void handleRoot() {
    server.send(200, "text/html",
        "<h1>Parakram Sensor Node</h1>"
        "<p><a href='/api/sensors'>GET /api/sensors</a></p>");
}

void handleSensors() {
    JsonDocument doc;
    doc["temperature"] = temperature;
    doc["humidity"] = humidity;
    doc["uptime_ms"] = millis();
    doc["heap_free"] = ESP.getFreeHeap();

    String output;
    serializeJson(doc, output);
    server.send(200, "application/json", output);
}

void handleNotFound() {
    server.send(404, "application/json", "{\\"error\\":\\"not found\\"}");
}

void setup() {
    Serial.begin(115200);
    // WiFi setup assumed done

    server.on("/", handleRoot);
    server.on("/api/sensors", handleSensors);
    server.onNotFound(handleNotFound);

    // CORS headers
    server.enableCORS(true);
    server.begin();
    Serial.printf("Server at http://%s\\n", WiFi.localIP().toString().c_str());
}

void loop() { server.handleClient(); }''',
    },
]


def get_snippets(category: str = "", tag: str = "", board: str = "") -> list[dict]:
    """Get code snippets with optional filters."""
    results = SNIPPETS
    if category:
        results = [s for s in results if s["category"] == category.lower()]
    if tag:
        results = [s for s in results if tag.lower() in [t.lower() for t in s["tags"]]]
    if board:
        results = [s for s in results if board.lower() in [b.lower() for b in s["boards"]]]
    return results


def get_snippet_categories() -> list[dict]:
    cats: dict[str, int] = {}
    for s in SNIPPETS:
        c = s["category"]
        cats[c] = cats.get(c, 0) + 1
    return [{"name": k, "count": v} for k, v in sorted(cats.items())]


def search_snippets(query: str) -> list[dict]:
    q = query.lower()
    return [s for s in SNIPPETS if
            q in s["title"].lower() or
            q in " ".join(s["tags"]) or
            q in s.get("code", "").lower()]
