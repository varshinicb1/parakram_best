"""
Library Knowledge Base — Maps Arduino/ESP32 libraries to their actual
class names, method signatures, and #include paths.

This prevents the LLM from hallucinating non-existent API calls.
The knowledge base is injected into the firmware generation prompt
alongside RAG results.
"""

# Each entry contains:
#   "include": The actual #include statement
#   "class": The main class name
#   "methods": List of real method signatures
#   "platformio_lib": The lib_deps entry for platformio.ini
#   "notes": Platform-specific gotchas

LIBRARY_REGISTRY: dict[str, dict] = {
    # ─── Sensors ─────────────────────────────────────────
    "Adafruit_BME280": {
        "include": "#include <Adafruit_BME280.h>",
        "depends": ["#include <Wire.h>", "#include <Adafruit_Sensor.h>"],
        "class": "Adafruit_BME280",
        "constructor": "Adafruit_BME280()",
        "methods": [
            "bool begin(uint8_t addr = 0x76, TwoWire *wire = &Wire)",
            "float readTemperature()",
            "float readHumidity()",
            "float readPressure()",
            "float readAltitude(float seaLevelPa = 1013.25)",
            "uint32_t sensorID()",
            "void setSampling(sensor_mode mode, sensor_sampling tempSampling, sensor_sampling pressSampling, sensor_sampling humSampling, sensor_filter filter, standby_duration duration)",
        ],
        "platformio_lib": "adafruit/Adafruit BME280 Library@^2.2.4",
        "notes": "Requires Adafruit_Sensor and Wire. Default I2C addr 0x76, alt 0x77.",
    },
    "Adafruit_BMP280": {
        "include": "#include <Adafruit_BMP280.h>",
        "depends": ["#include <Wire.h>", "#include <Adafruit_Sensor.h>"],
        "class": "Adafruit_BMP280",
        "constructor": "Adafruit_BMP280()",
        "methods": [
            "bool begin(uint8_t addr = 0x76, uint8_t chipid = BMP280_CHIPID)",
            "float readTemperature()",
            "float readPressure()",
            "float readAltitude(float seaLevelPa = 1013.25)",
        ],
        "platformio_lib": "adafruit/Adafruit BMP280 Library@^2.6.8",
        "notes": "Pressure-only variant. No humidity reading.",
    },
    "DHT": {
        "include": "#include <DHT.h>",
        "depends": [],
        "class": "DHT",
        "constructor": "DHT(uint8_t pin, uint8_t type)",
        "methods": [
            "void begin()",
            "float readTemperature(bool isFahrenheit = false)",
            "float readHumidity()",
            "float computeHeatIndex(float temperature, float humidity, bool isFahrenheit = true)",
            "bool read(bool force = false)",
        ],
        "platformio_lib": "adafruit/DHT sensor library@^1.4.6",
        "notes": "Type constants: DHT11, DHT22, DHT21. 2s min interval between reads.",
    },
    "BH1750": {
        "include": "#include <BH1750.h>",
        "depends": ["#include <Wire.h>"],
        "class": "BH1750",
        "constructor": "BH1750(uint8_t addr = 0x23)",
        "methods": [
            "bool begin(BH1750::Mode mode = CONTINUOUS_HIGH_RES_MODE, byte addr = 0x23, TwoWire* wire = &Wire)",
            "bool configure(Mode mode)",
            "float readLightLevel()",
            "bool measurementReady(bool maxWait = false)",
        ],
        "platformio_lib": "claws/BH1750@^1.3.0",
        "notes": "Addr pin LOW=0x23, HIGH=0x5C.",
    },
    "Adafruit_MPU6050": {
        "include": "#include <Adafruit_MPU6050.h>",
        "depends": ["#include <Wire.h>", "#include <Adafruit_Sensor.h>"],
        "class": "Adafruit_MPU6050",
        "constructor": "Adafruit_MPU6050()",
        "methods": [
            "bool begin(uint8_t i2c_address = MPU6050_I2CADDR_DEFAULT, TwoWire *wire = &Wire, int32_t sensorID = 0)",
            "bool getEvent(sensors_event_t *accel, sensors_event_t *gyro, sensors_event_t *temp)",
            "void setAccelerometerRange(mpu6050_accel_range_t range)",
            "void setGyroRange(mpu6050_gyro_range_t range)",
            "void setFilterBandwidth(mpu6050_bandwidth_t bandwidth)",
        ],
        "platformio_lib": "adafruit/Adafruit MPU6050@^2.2.6",
        "notes": "Returns sensors_event_t structs. acceleration.x/y/z in m/s^2, gyro.x/y/z in rad/s.",
    },
    "Adafruit_ADS1X15": {
        "include": "#include <Adafruit_ADS1X15.h>",
        "depends": ["#include <Wire.h>"],
        "class": "Adafruit_ADS1115",
        "constructor": "Adafruit_ADS1115()",
        "methods": [
            "bool begin(uint8_t i2c_addr = ADS1X15_ADDRESS, TwoWire *wire = &Wire)",
            "int16_t readADC_SingleEnded(uint8_t channel)",
            "int16_t readADC_Differential_0_1()",
            "float computeVolts(int16_t counts)",
            "void setGain(adsGain_t gain)",
            "adsGain_t getGain()",
            "void setDataRate(uint16_t rate)",
        ],
        "platformio_lib": "adafruit/Adafruit ADS1X15@^2.5.0",
        "notes": "16-bit ADC. Gain: GAIN_TWOTHIRDS(6.144V), GAIN_ONE(4.096V), GAIN_TWO(2.048V).",
    },
    "Adafruit_INA219": {
        "include": "#include <Adafruit_INA219.h>",
        "depends": ["#include <Wire.h>"],
        "class": "Adafruit_INA219",
        "constructor": "Adafruit_INA219(uint8_t addr = 0x40)",
        "methods": [
            "bool begin(TwoWire *wire = &Wire)",
            "float getBusVoltage_V()",
            "float getShuntVoltage_mV()",
            "float getCurrent_mA()",
            "float getPower_mW()",
        ],
        "platformio_lib": "adafruit/Adafruit INA219@^1.2.2",
        "notes": "Max 26V bus, 3.2A bidirectional current.",
    },
    "VL53L0X": {
        "include": "#include <VL53L0X.h>",
        "depends": ["#include <Wire.h>"],
        "class": "VL53L0X",
        "constructor": "VL53L0X()",
        "methods": [
            "void setAddress(uint8_t new_addr)",
            "bool init(bool io_2v8 = true)",
            "void setTimeout(uint16_t timeout)",
            "uint16_t readRangeSingleMillimeters()",
            "void startContinuous(uint32_t period_ms = 0)",
            "uint16_t readRangeContinuousMillimeters()",
            "bool timeoutOccurred()",
        ],
        "platformio_lib": "pololu/VL53L0X@^1.3.1",
        "notes": "Returns 8190 on timeout/out-of-range. Range 30-1200mm.",
    },

    # ─── Communication ───────────────────────────────────
    "WiFi": {
        "include": "#include <WiFi.h>",
        "depends": [],
        "class": "WiFiClass (global WiFi)",
        "constructor": "// Built-in, use global WiFi object",
        "methods": [
            "wl_status_t begin(const char* ssid, const char* passphrase = NULL)",
            "void disconnect(bool wifioff = false, bool eraseap = false)",
            "bool isConnected()",
            "wl_status_t status()",
            "IPAddress localIP()",
            "String macAddress()",
            "int32_t RSSI()",
            "void mode(wifi_mode_t m)  // WIFI_STA, WIFI_AP, WIFI_AP_STA",
        ],
        "platformio_lib": "// Built-in ESP32",
        "notes": "ESP32 built-in. Use WiFi.begin() then check WiFi.status() == WL_CONNECTED.",
    },
    "PubSubClient": {
        "include": "#include <PubSubClient.h>",
        "depends": ["#include <WiFi.h>", "#include <WiFiClient.h>"],
        "class": "PubSubClient",
        "constructor": "PubSubClient(WiFiClient& client)",
        "methods": [
            "PubSubClient& setServer(const char* domain, uint16_t port)",
            "PubSubClient& setCallback(MQTT_CALLBACK_SIGNATURE)",
            "bool connect(const char* id, const char* user = NULL, const char* pass = NULL)",
            "bool connected()",
            "bool publish(const char* topic, const char* payload, bool retained = false)",
            "bool subscribe(const char* topic, uint8_t qos = 0)",
            "bool unsubscribe(const char* topic)",
            "bool loop()",
            "void disconnect()",
        ],
        "platformio_lib": "knolleary/PubSubClient@^2.8",
        "notes": "MQTT_CALLBACK_SIGNATURE = void callback(char* topic, byte* payload, unsigned int length). Must call client.loop() in loop().",
    },

    # ─── Actuators ───────────────────────────────────────
    "ESP32Servo": {
        "include": "#include <ESP32Servo.h>",
        "depends": [],
        "class": "Servo",
        "constructor": "Servo()",
        "methods": [
            "void attach(int pin, int minUs = 544, int maxUs = 2400)",
            "void detach()",
            "void write(int angle)  // 0-180 degrees",
            "void writeMicroseconds(int us)",
            "int read()",
            "bool attached()",
        ],
        "platformio_lib": "madhephaestus/ESP32Servo@^3.0.5",
        "notes": "ESP32 uses LEDC for PWM. attach() auto-assigns LEDC channel.",
    },

    # ─── Display ─────────────────────────────────────────
    "Adafruit_SSD1306": {
        "include": "#include <Adafruit_SSD1306.h>",
        "depends": ["#include <Wire.h>", "#include <Adafruit_GFX.h>"],
        "class": "Adafruit_SSD1306",
        "constructor": "Adafruit_SSD1306(int w, int h, TwoWire *twi = &Wire, int8_t rst = -1)",
        "methods": [
            "bool begin(uint8_t switchvcc = SSD1306_SWITCHCAPVCC, uint8_t i2caddr = 0x3C)",
            "void clearDisplay()",
            "void display()",
            "void setTextSize(uint8_t s)",
            "void setTextColor(uint16_t c)",
            "void setCursor(int16_t x, int16_t y)",
            "void println(const char* text)",
            "void drawPixel(int16_t x, int16_t y, uint16_t color)",
        ],
        "platformio_lib": "adafruit/Adafruit SSD1306@^2.5.9",
        "notes": "Common sizes: 128x64, 128x32. Must call display() after drawing.",
    },

    # ─── Audio ───────────────────────────────────────────
    "driver/i2s": {
        "include": "#include <driver/i2s.h>",
        "depends": [],
        "class": "// ESP-IDF I2S driver (C functions)",
        "constructor": "// No class, use i2s_driver_install()",
        "methods": [
            "esp_err_t i2s_driver_install(i2s_port_t port, const i2s_config_t *config, int queue_size, void *queue)",
            "esp_err_t i2s_set_pin(i2s_port_t port, const i2s_pin_config_t *pin)",
            "esp_err_t i2s_read(i2s_port_t port, void *dest, size_t size, size_t *bytes_read, TickType_t ticks)",
            "esp_err_t i2s_write(i2s_port_t port, const void *src, size_t size, size_t *bytes_written, TickType_t ticks)",
            "esp_err_t i2s_driver_uninstall(i2s_port_t port)",
        ],
        "platformio_lib": "// Built-in ESP-IDF",
        "notes": "i2s_config_t fields: mode, sample_rate, bits_per_sample, channel_format, communication_format, dma_buf_count, dma_buf_len.",
    },

    # ─── FreeRTOS ────────────────────────────────────────
    "freertos/FreeRTOS": {
        "include": "#include <freertos/FreeRTOS.h>\n#include <freertos/task.h>",
        "depends": [],
        "class": "// FreeRTOS C API",
        "constructor": "// No class",
        "methods": [
            "BaseType_t xTaskCreatePinnedToCore(TaskFunction_t pvTaskCode, const char *name, uint32_t stackDepth, void *pvParams, UBaseType_t priority, TaskHandle_t *handle, BaseType_t coreID)",
            "void vTaskDelay(TickType_t ticks)  // use pdMS_TO_TICKS(ms)",
            "void vTaskDelete(TaskHandle_t handle)",
            "BaseType_t xSemaphoreCreateMutex()",
            "BaseType_t xSemaphoreTake(SemaphoreHandle_t sem, TickType_t timeout)",
            "BaseType_t xSemaphoreGive(SemaphoreHandle_t sem)",
            "QueueHandle_t xQueueCreate(UBaseType_t length, UBaseType_t itemSize)",
            "BaseType_t xQueueSend(QueueHandle_t queue, const void *item, TickType_t timeout)",
            "BaseType_t xQueueReceive(QueueHandle_t queue, void *buffer, TickType_t timeout)",
        ],
        "platformio_lib": "// Built-in ESP32",
        "notes": "ESP32 is dual-core. Pin tasks to core 0 or 1. Core 0 = WiFi, Core 1 = app default.",
    },
}


def get_library_info(library_name: str) -> dict:
    """Look up a library's API by name or include path."""
    # Direct match
    if library_name in LIBRARY_REGISTRY:
        return LIBRARY_REGISTRY[library_name]

    # Case-insensitive partial match
    name_lower = library_name.lower()
    for key, info in LIBRARY_REGISTRY.items():
        if name_lower in key.lower() or key.lower() in name_lower:
            return info

    return {}


def get_libs_for_block(block: dict) -> list[dict]:
    """Get library API info for all libraries a block needs."""
    libs = block.get("libraries", [])
    result = []
    for lib in libs:
        info = get_library_info(lib)
        if info:
            result.append({"name": lib, **info})
        else:
            result.append({"name": lib, "include": f"#include <{lib}.h>", "methods": []})
    return result


def format_library_context(libs: list[dict]) -> str:
    """Format library API info into prompt context string."""
    if not libs:
        return ""

    lines = ["LIBRARY API REFERENCE (use these exact methods, do NOT hallucinate):"]
    for lib in libs:
        lines.append(f"\n--- {lib['name']} ---")
        lines.append(f"Include: {lib.get('include', '')}")
        if lib.get("depends"):
            lines.append(f"Also needs: {', '.join(lib['depends'])}")
        if lib.get("class"):
            lines.append(f"Class: {lib['class']}")
        if lib.get("constructor"):
            lines.append(f"Constructor: {lib['constructor']}")
        if lib.get("methods"):
            lines.append("Methods:")
            for m in lib["methods"]:
                lines.append(f"  - {m}")
        if lib.get("notes"):
            lines.append(f"Notes: {lib['notes']}")

    return "\n".join(lines)


def get_platformio_deps(libs: list[dict]) -> list[str]:
    """Get PlatformIO lib_deps entries for a set of libraries."""
    deps = []
    for lib in libs:
        dep = lib.get("platformio_lib", "")
        if dep and not dep.startswith("//"):
            deps.append(dep)
    return deps
