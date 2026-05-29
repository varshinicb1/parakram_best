"""
Extended Golden Blocks — Additional verified components from official sources.

Sources:
  - Adafruit official Arduino libraries (BME680, INA219, ADS1115, APDS9960, VL53L0X, MPU6050)
  - SparkFun official libraries (BME680, MPU6050)
  - Espressif official ESP-IDF (BLE, I2S)
  - BlocklyDuino verified patterns (buzzer, rotary encoder, IR, LCD)
  - Arduino official libraries (Servo, LiquidCrystal, IRremote)

All method signatures verified against official documentation.
"""

EXTENDED_BLOCKS = {
    "sensor": [
        # ── BME680 — Official Adafruit API ──
        {"id": "bme680", "name": "BME680 Gas/Env Sensor", "libs": ["Wire.h", "Adafruit_BME680.h"],
         "lib_deps": ["adafruit/Adafruit BME680 Library@^2.0.4"],
         "pins": {"sda": 21, "scl": 22}, "bus": "I2C", "addr": "0x77",
         "header": '#ifndef BME680_H\n#define BME680_H\n#include <Adafruit_BME680.h>\nvoid bme680_setup();\nvoid bme680_loop();\nfloat bme680_get_temperature();\nfloat bme680_get_humidity();\nfloat bme680_get_pressure();\nfloat bme680_get_gas();\n#endif',
         "source": '#include "bme680.h"\n#include <Wire.h>\nstatic Adafruit_BME680 bme;\nstatic float _temp=0,_hum=0,_pres=0,_gas=0;\nstatic unsigned long _last=0;\nvoid bme680_setup() {\n  Wire.begin();\n  if (!bme.begin(0x77)) { Serial.println("[bme680] Init failed!"); return; }\n  bme.setTemperatureOversampling(BME680_OS_8X);\n  bme.setHumidityOversampling(BME680_OS_2X);\n  bme.setPressureOversampling(BME680_OS_4X);\n  bme.setIIRFilterSize(BME680_FILTER_SIZE_3);\n  bme.setGasHeater(320, 150);\n  Serial.println("[bme680] OK");\n}\nvoid bme680_loop() {\n  if (millis()-_last < 3000) return;\n  _last = millis();\n  if (bme.performReading()) {\n    _temp = bme.temperature;\n    _hum = bme.humidity;\n    _pres = bme.pressure / 100.0F;\n    _gas = bme.gas_resistance / 1000.0F;\n    Serial.printf("[bme680] T=%.1fC H=%.0f%% P=%.0fhPa G=%.1fkOhm\\n",_temp,_hum,_pres,_gas);\n  }\n}\nfloat bme680_get_temperature(){return _temp;}\nfloat bme680_get_humidity(){return _hum;}\nfloat bme680_get_pressure(){return _pres;}\nfloat bme680_get_gas(){return _gas;}'},

        # ── MPU6050 — Official Adafruit API ──
        {"id": "mpu6050", "name": "MPU6050 IMU 6-Axis", "libs": ["Wire.h", "Adafruit_MPU6050.h"],
         "lib_deps": ["adafruit/Adafruit MPU6050@^2.2.6"],
         "pins": {"sda": 21, "scl": 22}, "bus": "I2C", "addr": "0x68",
         "header": '#ifndef MPU6050_H\n#define MPU6050_H\n#include <Adafruit_MPU6050.h>\nvoid mpu6050_setup();\nvoid mpu6050_loop();\nfloat mpu6050_get_accel_x();\nfloat mpu6050_get_accel_y();\nfloat mpu6050_get_accel_z();\nfloat mpu6050_get_gyro_x();\nfloat mpu6050_get_gyro_y();\nfloat mpu6050_get_gyro_z();\nfloat mpu6050_get_temperature();\n#endif',
         "source": '#include "mpu6050.h"\n#include <Wire.h>\n#include <Adafruit_Sensor.h>\nstatic Adafruit_MPU6050 mpu;\nstatic float _ax=0,_ay=0,_az=0,_gx=0,_gy=0,_gz=0,_t=0;\nstatic unsigned long _last=0;\nvoid mpu6050_setup() {\n  Wire.begin();\n  if (!mpu.begin()) { Serial.println("[mpu6050] Init failed!"); return; }\n  mpu.setAccelerometerRange(MPU6050_RANGE_8_G);\n  mpu.setGyroRange(MPU6050_RANGE_500_DEG);\n  mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);\n  Serial.println("[mpu6050] OK");\n}\nvoid mpu6050_loop() {\n  if (millis()-_last < 50) return;\n  _last = millis();\n  sensors_event_t a, g, temp;\n  mpu.getEvent(&a, &g, &temp);\n  _ax=a.acceleration.x; _ay=a.acceleration.y; _az=a.acceleration.z;\n  _gx=g.gyro.x; _gy=g.gyro.y; _gz=g.gyro.z;\n  _t=temp.temperature;\n}\nfloat mpu6050_get_accel_x(){return _ax;}\nfloat mpu6050_get_accel_y(){return _ay;}\nfloat mpu6050_get_accel_z(){return _az;}\nfloat mpu6050_get_gyro_x(){return _gx;}\nfloat mpu6050_get_gyro_y(){return _gy;}\nfloat mpu6050_get_gyro_z(){return _gz;}\nfloat mpu6050_get_temperature(){return _t;}'},

        # ── INA219 — Official Adafruit API ──
        {"id": "ina219", "name": "INA219 Current/Power Monitor", "libs": ["Wire.h", "Adafruit_INA219.h"],
         "lib_deps": ["adafruit/Adafruit INA219@^1.2.1"],
         "pins": {"sda": 21, "scl": 22}, "bus": "I2C", "addr": "0x40",
         "header": '#ifndef INA219_H\n#define INA219_H\n#include <Adafruit_INA219.h>\nvoid ina219_setup();\nvoid ina219_loop();\nfloat ina219_get_bus_voltage();\nfloat ina219_get_shunt_voltage();\nfloat ina219_get_current_mA();\nfloat ina219_get_power_mW();\n#endif',
         "source": '#include "ina219.h"\n#include <Wire.h>\nstatic Adafruit_INA219 ina;\nstatic float _busV=0,_shuntV=0,_mA=0,_mW=0;\nstatic unsigned long _last=0;\nvoid ina219_setup() {\n  Wire.begin();\n  if (!ina.begin()) { Serial.println("[ina219] Init failed!"); return; }\n  ina.setCalibration_32V_2A();\n  Serial.println("[ina219] OK");\n}\nvoid ina219_loop() {\n  if (millis()-_last < 500) return;\n  _last = millis();\n  _busV = ina.getBusVoltage_V();\n  _shuntV = ina.getShuntVoltage_mV();\n  _mA = ina.getCurrent_mA();\n  _mW = ina.getPower_mW();\n  Serial.printf("[ina219] %.2fV %.1fmA %.1fmW\\n",_busV,_mA,_mW);\n}\nfloat ina219_get_bus_voltage(){return _busV;}\nfloat ina219_get_shunt_voltage(){return _shuntV;}\nfloat ina219_get_current_mA(){return _mA;}\nfloat ina219_get_power_mW(){return _mW;}'},

        # ── ADS1115 — Official Adafruit API ──
        {"id": "ads1115", "name": "ADS1115 16-bit ADC", "libs": ["Wire.h", "Adafruit_ADS1X15.h"],
         "lib_deps": ["adafruit/Adafruit ADS1X15@^2.5.0"],
         "pins": {"sda": 21, "scl": 22}, "bus": "I2C", "addr": "0x48",
         "header": '#ifndef ADS1115_H\n#define ADS1115_H\n#include <Adafruit_ADS1X15.h>\nvoid ads1115_setup();\nvoid ads1115_loop();\nint16_t ads1115_read_channel(uint8_t ch);\nfloat ads1115_read_voltage(uint8_t ch);\n#endif',
         "source": '#include "ads1115.h"\n#include <Wire.h>\nstatic Adafruit_ADS1115 ads;\nstatic int16_t _raw[4] = {0};\nstatic unsigned long _last = 0;\nvoid ads1115_setup() {\n  Wire.begin();\n  if (!ads.begin(0x48)) { Serial.println("[ads1115] Init failed!"); return; }\n  ads.setGain(GAIN_TWOTHIRDS);\n  Serial.println("[ads1115] OK 16-bit");\n}\nvoid ads1115_loop() {\n  if (millis()-_last < 200) return;\n  _last = millis();\n  for (uint8_t i = 0; i < 4; i++) {\n    _raw[i] = ads.readADC_SingleEnded(i);\n  }\n}\nint16_t ads1115_read_channel(uint8_t ch) { return (ch < 4) ? _raw[ch] : 0; }\nfloat ads1115_read_voltage(uint8_t ch) { return (ch < 4) ? ads.computeVolts(_raw[ch]) : 0.0f; }'},

        # ── VL53L0X — Official Adafruit API ──
        {"id": "vl53l0x", "name": "VL53L0X ToF Distance", "libs": ["Wire.h", "Adafruit_VL53L0X.h"],
         "lib_deps": ["adafruit/Adafruit_VL53L0X@^1.2.4"],
         "pins": {"sda": 21, "scl": 22}, "bus": "I2C", "addr": "0x29",
         "header": '#ifndef VL53L0X_H\n#define VL53L0X_H\n#include <Adafruit_VL53L0X.h>\nvoid vl53l0x_setup();\nvoid vl53l0x_loop();\nuint16_t vl53l0x_get_distance_mm();\nbool vl53l0x_in_range();\n#endif',
         "source": '#include "vl53l0x.h"\n#include <Wire.h>\nstatic Adafruit_VL53L0X lox;\nstatic uint16_t _mm = 0;\nstatic bool _valid = false;\nstatic unsigned long _last = 0;\nvoid vl53l0x_setup() {\n  Wire.begin();\n  if (!lox.begin()) { Serial.println("[vl53l0x] Init failed!"); return; }\n  Serial.println("[vl53l0x] OK");\n}\nvoid vl53l0x_loop() {\n  if (millis()-_last < 100) return;\n  _last = millis();\n  VL53L0X_RangingMeasurementData_t m;\n  lox.rangingTest(&m, false);\n  if (m.RangeStatus != 4) { _mm = m.RangeMilliMeter; _valid = true; }\n  else { _valid = false; }\n}\nuint16_t vl53l0x_get_distance_mm() { return _mm; }\nbool vl53l0x_in_range() { return _valid; }'},

        # ── APDS9960 — Official SparkFun API ──
        {"id": "apds9960", "name": "APDS9960 Gesture/Proximity", "libs": ["Wire.h", "SparkFun_APDS9960.h"],
         "lib_deps": ["sparkfun/SparkFun APDS9960 RGB and Gesture Sensor@^1.4.3"],
         "pins": {"sda": 21, "scl": 22, "int": 2}, "bus": "I2C", "addr": "0x39",
         "header": '#ifndef APDS9960_H\n#define APDS9960_H\nvoid apds9960_setup();\nvoid apds9960_loop();\nint apds9960_get_gesture();\nuint8_t apds9960_get_proximity();\nuint16_t apds9960_get_red();\nuint16_t apds9960_get_green();\nuint16_t apds9960_get_blue();\n#endif',
         "source": '#include "apds9960.h"\n#include <Wire.h>\n#include <SparkFun_APDS9960.h>\nstatic SparkFun_APDS9960 apds;\nstatic int _gesture = 0;\nstatic uint8_t _prox = 0;\nstatic uint16_t _r=0,_g=0,_b=0;\nstatic unsigned long _last = 0;\nvoid apds9960_setup() {\n  Wire.begin();\n  if (!apds.init()) { Serial.println("[apds9960] Init failed!"); return; }\n  apds.enableGestureSensor(true);\n  apds.enableProximitySensor(false);\n  apds.enableLightSensor(false);\n  Serial.println("[apds9960] OK");\n}\nvoid apds9960_loop() {\n  if (millis()-_last < 100) return;\n  _last = millis();\n  if (apds.isGestureAvailable()) { _gesture = apds.readGesture(); }\n  apds.readProximity(_prox);\n  apds.readRedLight(_r); apds.readGreenLight(_g); apds.readBlueLight(_b);\n}\nint apds9960_get_gesture(){return _gesture;}\nuint8_t apds9960_get_proximity(){return _prox;}\nuint16_t apds9960_get_red(){return _r;}\nuint16_t apds9960_get_green(){return _g;}\nuint16_t apds9960_get_blue(){return _b;}'},

        # ── BMP280 — Official Adafruit API ──
        {"id": "bmp280", "name": "BMP280 Pressure/Altitude", "libs": ["Wire.h", "Adafruit_BMP280.h"],
         "lib_deps": ["adafruit/Adafruit BMP280 Library@^2.6.8"],
         "pins": {"sda": 21, "scl": 22}, "bus": "I2C", "addr": "0x76",
         "header": '#ifndef BMP280_H\n#define BMP280_H\n#include <Adafruit_BMP280.h>\nvoid bmp280_setup();\nvoid bmp280_loop();\nfloat bmp280_get_temperature();\nfloat bmp280_get_pressure();\nfloat bmp280_get_altitude();\n#endif',
         "source": '#include "bmp280.h"\n#include <Wire.h>\nstatic Adafruit_BMP280 bmp;\nstatic float _temp=0, _pres=0, _alt=0;\nstatic unsigned long _last=0;\nvoid bmp280_setup() {\n  Wire.begin();\n  if (!bmp.begin(0x76)) { Serial.println("[bmp280] Init failed!"); return; }\n  bmp.setSampling(Adafruit_BMP280::MODE_NORMAL,\n    Adafruit_BMP280::SAMPLING_X2, Adafruit_BMP280::SAMPLING_X16,\n    Adafruit_BMP280::FILTER_X16, Adafruit_BMP280::STANDBY_MS_500);\n  Serial.println("[bmp280] OK");\n}\nvoid bmp280_loop() {\n  if (millis()-_last < 2000) return;\n  _last = millis();\n  _temp = bmp.readTemperature();\n  _pres = bmp.readPressure() / 100.0F;\n  _alt = bmp.readAltitude(1013.25);\n  Serial.printf("[bmp280] T=%.1fC P=%.0fhPa Alt=%.1fm\\n",_temp,_pres,_alt);\n}\nfloat bmp280_get_temperature(){return _temp;}\nfloat bmp280_get_pressure(){return _pres;}\nfloat bmp280_get_altitude(){return _alt;}'},

        # ── MQ Gas Sensor — BlocklyDuino pattern ──
        {"id": "mq_gas_sensor", "name": "MQ Gas Sensor (MQ-2/MQ-135)", "libs": [],
         "lib_deps": [], "pins": {"analog": 34, "digital": 35},
         "header": '#ifndef MQ_GAS_H\n#define MQ_GAS_H\nvoid mq_gas_setup();\nvoid mq_gas_loop();\nint mq_gas_get_raw();\nfloat mq_gas_get_ppm();\nbool mq_gas_alert();\n#endif',
         "source": '#include "mq_gas_sensor.h"\n#include <Arduino.h>\n#define MQ_ANALOG_PIN 34\n#define MQ_DIGITAL_PIN 35\n#define MQ_THRESHOLD 2000\nstatic int _raw = 0;\nstatic float _ppm = 0;\nstatic bool _alert = false;\nstatic unsigned long _last = 0;\nvoid mq_gas_setup() {\n  pinMode(MQ_ANALOG_PIN, INPUT);\n  pinMode(MQ_DIGITAL_PIN, INPUT);\n  Serial.println("[mq] OK — warm-up 60s");\n}\nvoid mq_gas_loop() {\n  if (millis()-_last < 1000) return;\n  _last = millis();\n  _raw = analogRead(MQ_ANALOG_PIN);\n  _ppm = (float)_raw / 4095.0f * 1000.0f;\n  _alert = !digitalRead(MQ_DIGITAL_PIN);\n  if (_alert) Serial.printf("[mq] ALERT! raw=%d ppm=%.0f\\n",_raw,_ppm);\n}\nint mq_gas_get_raw(){return _raw;}\nfloat mq_gas_get_ppm(){return _ppm;}\nbool mq_gas_alert(){return _alert;}'},

        # ── Rotary Encoder — BlocklyDuino pattern ──
        {"id": "rotary_encoder", "name": "Rotary Encoder (KY-040)", "libs": [],
         "lib_deps": [], "pins": {"clk": 32, "dt": 33, "sw": 25},
         "header": '#ifndef ROTARY_ENCODER_H\n#define ROTARY_ENCODER_H\nvoid encoder_setup();\nvoid encoder_loop();\nint encoder_get_position();\nbool encoder_button_pressed();\nvoid encoder_reset();\n#endif',
         "source": '#include "rotary_encoder.h"\n#include <Arduino.h>\n#define ENC_CLK 32\n#define ENC_DT 33\n#define ENC_SW 25\nstatic volatile int _pos = 0;\nstatic volatile bool _btn = false;\nstatic int _lastCLK = HIGH;\nvoid IRAM_ATTR _enc_isr() {\n  int clk = digitalRead(ENC_CLK);\n  if (clk != _lastCLK && clk == LOW) {\n    if (digitalRead(ENC_DT) != clk) _pos++; else _pos--;\n  }\n  _lastCLK = clk;\n}\nvoid IRAM_ATTR _btn_isr() { _btn = true; }\nvoid encoder_setup() {\n  pinMode(ENC_CLK, INPUT_PULLUP);\n  pinMode(ENC_DT, INPUT_PULLUP);\n  pinMode(ENC_SW, INPUT_PULLUP);\n  attachInterrupt(ENC_CLK, _enc_isr, CHANGE);\n  attachInterrupt(ENC_SW, _btn_isr, FALLING);\n  Serial.println("[encoder] OK");\n}\nvoid encoder_loop() {}\nint encoder_get_position(){return _pos;}\nbool encoder_button_pressed(){bool b=_btn;_btn=false;return b;}\nvoid encoder_reset(){_pos=0;}'},
    ],

    "actuator": [
        # ── Servo — Official Arduino Servo library ──
        {"id": "servo_motor", "name": "Servo Motor (SG90/MG996R)", "libs": ["ESP32Servo.h"],
         "lib_deps": ["madhephaestus/ESP32Servo@^3.0.5"],
         "pins": {"signal": 13},
         "header": '#ifndef SERVO_MOTOR_H\n#define SERVO_MOTOR_H\n#include <ESP32Servo.h>\nvoid servo_setup();\nvoid servo_loop();\nvoid servo_set_angle(int angle);\nint servo_get_angle();\nvoid servo_sweep(int from, int to, int step_delay);\n#endif',
         "source": '#include "servo_motor.h"\n#define SERVO_PIN 13\nstatic Servo _servo;\nstatic int _angle = 90;\nvoid servo_setup() {\n  _servo.attach(SERVO_PIN, 500, 2400);\n  _servo.write(90);\n  Serial.println("[servo] OK pin=13");\n}\nvoid servo_loop() {}\nvoid servo_set_angle(int a) {\n  _angle = constrain(a, 0, 180);\n  _servo.write(_angle);\n  Serial.printf("[servo] %d deg\\n", _angle);\n}\nint servo_get_angle() { return _angle; }\nvoid servo_sweep(int from, int to, int d) {\n  int step = (to > from) ? 1 : -1;\n  for (int i = from; i != to; i += step) {\n    _servo.write(i);\n    delay(d);\n  }\n}'},

        # ── Buzzer / Piezo — BlocklyDuino pattern ──
        {"id": "buzzer", "name": "Piezo Buzzer", "libs": [],
         "lib_deps": [], "pins": {"signal": 15},
         "header": '#ifndef BUZZER_H\n#define BUZZER_H\nvoid buzzer_setup();\nvoid buzzer_tone(uint16_t freq, uint16_t duration_ms);\nvoid buzzer_beep();\nvoid buzzer_alarm();\nvoid buzzer_off();\n#endif',
         "source": '#include "buzzer.h"\n#include <Arduino.h>\n#define BUZZER_PIN 15\n#define BUZZER_CHANNEL 0\nvoid buzzer_setup() {\n  ledcAttach(BUZZER_PIN, 2000, 8);\n  Serial.println("[buzzer] OK pin=15");\n}\nvoid buzzer_tone(uint16_t freq, uint16_t dur) {\n  ledcWriteTone(BUZZER_PIN, freq);\n  delay(dur);\n  ledcWriteTone(BUZZER_PIN, 0);\n}\nvoid buzzer_beep() { buzzer_tone(1000, 100); }\nvoid buzzer_alarm() {\n  for (int i = 0; i < 3; i++) {\n    buzzer_tone(2000, 200);\n    delay(100);\n  }\n}\nvoid buzzer_off() { ledcWriteTone(BUZZER_PIN, 0); }'},

        # ── LED Output — BlocklyDuino pattern ──
        {"id": "led_output", "name": "LED Output (PWM)", "libs": [],
         "lib_deps": [], "pins": {"led": 2},
         "header": '#ifndef LED_OUTPUT_H\n#define LED_OUTPUT_H\nvoid led_setup();\nvoid led_on();\nvoid led_off();\nvoid led_set_brightness(uint8_t b);\nvoid led_blink(uint16_t on_ms, uint16_t off_ms);\n#endif',
         "source": '#include "led_output.h"\n#include <Arduino.h>\n#define LED_PIN 2\nstatic bool _on = false;\nstatic unsigned long _blinkLast = 0;\nstatic uint16_t _blinkOn = 0, _blinkOff = 0;\nvoid led_setup() {\n  ledcAttach(LED_PIN, 5000, 8);\n  Serial.println("[led] OK pin=2");\n}\nvoid led_on() { ledcWrite(LED_PIN, 255); _on = true; }\nvoid led_off() { ledcWrite(LED_PIN, 0); _on = false; }\nvoid led_set_brightness(uint8_t b) { ledcWrite(LED_PIN, b); _on = (b > 0); }\nvoid led_blink(uint16_t on_ms, uint16_t off_ms) { _blinkOn = on_ms; _blinkOff = off_ms; }'},
    ],

    "communication": [
        # ── BLE Server — Official Espressif BLE API ──
        {"id": "ble_server", "name": "BLE Peripheral (GATT)", "libs": ["BLEDevice.h"],
         "lib_deps": [],
         "header": '#ifndef BLE_SERVER_H\n#define BLE_SERVER_H\nvoid ble_setup(const char* name);\nvoid ble_loop();\nvoid ble_notify(const char* value);\nbool ble_is_connected();\n#endif',
         "source": '#include "ble_server.h"\n#include <BLEDevice.h>\n#include <BLEServer.h>\n#include <BLEUtils.h>\n#include <BLE2902.h>\n#define SERVICE_UUID "4fafc201-1fb5-459e-8fcc-c5c9c331914b"\n#define CHAR_UUID    "beb5483e-36e1-4688-b7f5-ea07361b26a8"\nstatic BLECharacteristic* pChar = nullptr;\nstatic bool _connected = false;\nclass MyCB : public BLEServerCallbacks {\n  void onConnect(BLEServer*) { _connected = true; Serial.println("[ble] Connected"); }\n  void onDisconnect(BLEServer* s) { _connected = false; s->startAdvertising(); Serial.println("[ble] Disconnected"); }\n};\nvoid ble_setup(const char* name) {\n  BLEDevice::init(name);\n  BLEServer* s = BLEDevice::createServer();\n  s->setCallbacks(new MyCB());\n  BLEService* svc = s->createService(SERVICE_UUID);\n  pChar = svc->createCharacteristic(CHAR_UUID, BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_NOTIFY);\n  pChar->addDescriptor(new BLE2902());\n  svc->start();\n  s->getAdvertising()->start();\n  Serial.printf("[ble] OK: %s\\n", name);\n}\nvoid ble_loop() {}\nvoid ble_notify(const char* v) { if (pChar && _connected) { pChar->setValue(v); pChar->notify(); } }\nbool ble_is_connected() { return _connected; }'},

        # ── WiFi Station — Official ESP32 WiFi ──
        {"id": "wifi_station", "name": "WiFi Station", "libs": ["WiFi.h"],
         "lib_deps": [],
         "header": '#ifndef WIFI_STATION_H\n#define WIFI_STATION_H\n#include <WiFi.h>\nvoid wifi_setup(const char* ssid, const char* pass);\nvoid wifi_loop();\nbool wifi_connected();\nString wifi_get_ip();\nint wifi_get_rssi();\n#endif',
         "source": '#include "wifi_station.h"\nstatic bool _connected = false;\nvoid wifi_setup(const char* ssid, const char* pass) {\n  WiFi.mode(WIFI_STA);\n  WiFi.begin(ssid, pass);\n  Serial.printf("[wifi] Connecting to %s", ssid);\n  int retries = 0;\n  while (WiFi.status() != WL_CONNECTED && retries < 40) {\n    delay(500); Serial.print("."); retries++;\n  }\n  if (WiFi.status() == WL_CONNECTED) {\n    _connected = true;\n    Serial.printf("\\n[wifi] OK IP=%s RSSI=%d\\n", WiFi.localIP().toString().c_str(), WiFi.RSSI());\n  } else {\n    Serial.println("\\n[wifi] FAILED!");\n  }\n}\nvoid wifi_loop() {\n  _connected = (WiFi.status() == WL_CONNECTED);\n}\nbool wifi_connected() { return _connected; }\nString wifi_get_ip() { return WiFi.localIP().toString(); }\nint wifi_get_rssi() { return WiFi.RSSI(); }'},

        # ── MQTT Client — Official PubSubClient API ──
        {"id": "mqtt_client", "name": "MQTT Client", "libs": ["WiFi.h", "PubSubClient.h"],
         "lib_deps": ["knolleary/PubSubClient@^2.8"],
         "header": '#ifndef MQTT_CLIENT_H\n#define MQTT_CLIENT_H\n#include <PubSubClient.h>\nvoid mqtt_setup(const char* server, uint16_t port);\nvoid mqtt_loop();\nbool mqtt_publish(const char* topic, const char* payload);\nvoid mqtt_subscribe(const char* topic);\ntypedef void (*mqtt_cb)(const char* topic, const char* payload);\nvoid mqtt_on_message(mqtt_cb cb);\nbool mqtt_connected();\n#endif',
         "source": '#include "mqtt_client.h"\n#include <WiFi.h>\nstatic WiFiClient _wifiClient;\nstatic PubSubClient _mqtt(_wifiClient);\nstatic mqtt_cb _userCb = nullptr;\nstatic const char* _server = "";\nstatic uint16_t _port = 1883;\nvoid _mqtt_callback(char* topic, byte* payload, unsigned int len) {\n  char buf[256];\n  unsigned int n = (len < 255) ? len : 255;\n  memcpy(buf, payload, n); buf[n] = 0;\n  if (_userCb) _userCb(topic, buf);\n}\nvoid mqtt_setup(const char* server, uint16_t port) {\n  _server = server; _port = port;\n  _mqtt.setServer(server, port);\n  _mqtt.setCallback(_mqtt_callback);\n  Serial.printf("[mqtt] Server %s:%d\\n", server, port);\n}\nvoid mqtt_loop() {\n  if (!_mqtt.connected()) {\n    if (_mqtt.connect("parakram-device")) {\n      Serial.println("[mqtt] Connected");\n    }\n  }\n  _mqtt.loop();\n}\nbool mqtt_publish(const char* t, const char* p) { return _mqtt.publish(t, p); }\nvoid mqtt_subscribe(const char* t) { _mqtt.subscribe(t); }\nvoid mqtt_on_message(mqtt_cb cb) { _userCb = cb; }\nbool mqtt_connected() { return _mqtt.connected(); }'},
    ],

    "display": [
        # ── I2C OLED — Official Adafruit SSD1306 API ──
        {"id": "i2c_oled", "name": "SSD1306 OLED 128x64", "libs": ["Wire.h", "Adafruit_SSD1306.h"],
         "lib_deps": ["adafruit/Adafruit SSD1306@^2.5.9", "adafruit/Adafruit GFX Library@^1.11.9"],
         "pins": {"sda": 21, "scl": 22}, "bus": "I2C", "addr": "0x3C",
         "header": '#ifndef I2C_OLED_H\n#define I2C_OLED_H\n#include <Adafruit_SSD1306.h>\nvoid oled_setup();\nvoid oled_clear();\nvoid oled_text(int x, int y, const char* text, int size);\nvoid oled_update();\nvoid oled_draw_rect(int x, int y, int w, int h);\nvoid oled_draw_progress(int x, int y, int w, int h, int percent);\n#endif',
         "source": '#include "i2c_oled.h"\n#include <Wire.h>\n#include <Adafruit_GFX.h>\nstatic Adafruit_SSD1306 display(128, 64, &Wire, -1);\nvoid oled_setup() {\n  Wire.begin();\n  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {\n    Serial.println("[oled] Init failed!"); return;\n  }\n  display.clearDisplay();\n  display.setTextColor(SSD1306_WHITE);\n  display.display();\n  Serial.println("[oled] OK 128x64");\n}\nvoid oled_clear() { display.clearDisplay(); }\nvoid oled_text(int x, int y, const char* t, int s) {\n  display.setTextSize(s); display.setCursor(x, y); display.print(t);\n}\nvoid oled_update() { display.display(); }\nvoid oled_draw_rect(int x, int y, int w, int h) { display.drawRect(x,y,w,h,SSD1306_WHITE); }\nvoid oled_draw_progress(int x, int y, int w, int h, int pct) {\n  display.drawRect(x,y,w,h,SSD1306_WHITE);\n  int fill = (w-2) * constrain(pct,0,100) / 100;\n  display.fillRect(x+1,y+1,fill,h-2,SSD1306_WHITE);\n}'},

        # ── LCD I2C 16x2 — Official LiquidCrystal_I2C ──
        {"id": "lcd_i2c", "name": "LCD 16x2 (I2C)", "libs": ["Wire.h", "LiquidCrystal_I2C.h"],
         "lib_deps": ["marcoschwartz/LiquidCrystal_I2C@^1.1.4"],
         "pins": {"sda": 21, "scl": 22}, "bus": "I2C", "addr": "0x27",
         "header": '#ifndef LCD_I2C_H\n#define LCD_I2C_H\n#include <LiquidCrystal_I2C.h>\nvoid lcd_setup();\nvoid lcd_clear();\nvoid lcd_print(int row, const char* text);\nvoid lcd_print_at(int col, int row, const char* text);\nvoid lcd_backlight(bool on);\n#endif',
         "source": '#include "lcd_i2c.h"\n#include <Wire.h>\nstatic LiquidCrystal_I2C lcd(0x27, 16, 2);\nvoid lcd_setup() {\n  Wire.begin();\n  lcd.init();\n  lcd.backlight();\n  lcd.clear();\n  Serial.println("[lcd] OK 16x2");\n}\nvoid lcd_clear() { lcd.clear(); }\nvoid lcd_print(int row, const char* t) {\n  lcd.setCursor(0, constrain(row, 0, 1));\n  lcd.print(t);\n}\nvoid lcd_print_at(int col, int row, const char* t) {\n  lcd.setCursor(col, row); lcd.print(t);\n}\nvoid lcd_backlight(bool on) { if (on) lcd.backlight(); else lcd.noBacklight(); }'},

        # ── ILI9341 TFT — Official Adafruit API ──
        {"id": "spi_display", "name": "ILI9341 TFT 2.4\" SPI", "libs": ["SPI.h", "Adafruit_ILI9341.h"],
         "lib_deps": ["adafruit/Adafruit ILI9341@^1.6.0", "adafruit/Adafruit GFX Library@^1.11.9"],
         "pins": {"cs": 15, "dc": 2, "rst": 4},
         "header": '#ifndef SPI_DISPLAY_H\n#define SPI_DISPLAY_H\n#include <Adafruit_ILI9341.h>\nvoid tft_setup();\nvoid tft_clear(uint16_t color);\nvoid tft_text(int x, int y, const char* text, uint16_t color, int size);\nvoid tft_rect(int x, int y, int w, int h, uint16_t color);\nvoid tft_fill_rect(int x, int y, int w, int h, uint16_t color);\nvoid tft_line(int x0, int y0, int x1, int y1, uint16_t color);\n#endif',
         "source": '#include "spi_display.h"\n#include <SPI.h>\n#include <Adafruit_GFX.h>\nstatic Adafruit_ILI9341 tft(15, 2, 4);\nvoid tft_setup() {\n  tft.begin();\n  tft.setRotation(1);\n  tft.fillScreen(ILI9341_BLACK);\n  Serial.println("[tft] OK 320x240");\n}\nvoid tft_clear(uint16_t c) { tft.fillScreen(c); }\nvoid tft_text(int x, int y, const char* t, uint16_t c, int s) {\n  tft.setCursor(x, y); tft.setTextColor(c); tft.setTextSize(s); tft.print(t);\n}\nvoid tft_rect(int x, int y, int w, int h, uint16_t c) { tft.drawRect(x,y,w,h,c); }\nvoid tft_fill_rect(int x, int y, int w, int h, uint16_t c) { tft.fillRect(x,y,w,h,c); }\nvoid tft_line(int x0, int y0, int x1, int y1, uint16_t c) { tft.drawLine(x0,y0,x1,y1,c); }'},
    ],

    "audio": [
        # ── I2S Microphone — Official ESP-IDF I2S API ──
        {"id": "i2s_microphone", "name": "I2S MEMS Microphone (INMP441)", "libs": ["driver/i2s.h"],
         "lib_deps": [],
         "pins": {"ws": 25, "sd": 33, "sck": 26},
         "header": '#ifndef I2S_MIC_H\n#define I2S_MIC_H\n#include <Arduino.h>\nvoid i2s_mic_setup();\nvoid i2s_mic_loop();\nint16_t i2s_mic_get_sample();\nfloat i2s_mic_get_db();\n#endif',
         "source": '#include "i2s_microphone.h"\n#include <driver/i2s.h>\n#define I2S_WS 25\n#define I2S_SD 33\n#define I2S_SCK 26\n#define SAMPLE_RATE 16000\nstatic int16_t _sample = 0;\nstatic float _db = 0;\nvoid i2s_mic_setup() {\n  i2s_config_t cfg = {};\n  cfg.mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX);\n  cfg.sample_rate = SAMPLE_RATE;\n  cfg.bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT;\n  cfg.channel_format = I2S_CHANNEL_FMT_ONLY_LEFT;\n  cfg.communication_format = I2S_COMM_FORMAT_STAND_I2S;\n  cfg.intr_alloc_flags = ESP_INTR_FLAG_LEVEL1;\n  cfg.dma_buf_count = 4;\n  cfg.dma_buf_len = 1024;\n  i2s_driver_install(I2S_NUM_0, &cfg, 0, NULL);\n  i2s_pin_config_t pins = { .bck_io_num = I2S_SCK, .ws_io_num = I2S_WS, .data_out_num = -1, .data_in_num = I2S_SD };\n  i2s_set_pin(I2S_NUM_0, &pins);\n  Serial.println("[i2s_mic] OK 16kHz");\n}\nvoid i2s_mic_loop() {\n  int16_t buf[64];\n  size_t rd = 0;\n  i2s_read(I2S_NUM_0, buf, sizeof(buf), &rd, portMAX_DELAY);\n  if (rd > 0) {\n    int32_t sum = 0;\n    int n = rd / 2;\n    for (int i = 0; i < n; i++) sum += abs(buf[i]);\n    _sample = buf[0];\n    float rms = (float)sum / n;\n    _db = (rms > 0) ? 20.0f * log10f(rms / 32768.0f) + 94.0f : 0;\n  }\n}\nint16_t i2s_mic_get_sample() { return _sample; }\nfloat i2s_mic_get_db() { return _db; }'},

        # ── I2S Speaker — Official ESP-IDF I2S + MAX98357 ──
        {"id": "i2s_speaker", "name": "I2S Speaker (MAX98357)", "libs": ["driver/i2s.h"],
         "lib_deps": [],
         "pins": {"bclk": 26, "lrc": 25, "din": 22},
         "header": '#ifndef I2S_SPEAKER_H\n#define I2S_SPEAKER_H\n#include <Arduino.h>\nvoid i2s_spk_setup();\nvoid i2s_spk_write(const int16_t* samples, size_t count);\nvoid i2s_spk_tone(uint16_t freq, uint16_t duration_ms);\nvoid i2s_spk_stop();\n#endif',
         "source": '#include "i2s_speaker.h"\n#include <driver/i2s.h>\n#include <math.h>\n#define SPK_BCLK 26\n#define SPK_LRC 25\n#define SPK_DIN 22\n#define SPK_RATE 44100\nvoid i2s_spk_setup() {\n  i2s_config_t cfg = {};\n  cfg.mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX);\n  cfg.sample_rate = SPK_RATE;\n  cfg.bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT;\n  cfg.channel_format = I2S_CHANNEL_FMT_RIGHT_LEFT;\n  cfg.communication_format = I2S_COMM_FORMAT_STAND_I2S;\n  cfg.dma_buf_count = 8;\n  cfg.dma_buf_len = 1024;\n  i2s_driver_install(I2S_NUM_1, &cfg, 0, NULL);\n  i2s_pin_config_t pins = { .bck_io_num = SPK_BCLK, .ws_io_num = SPK_LRC, .data_out_num = SPK_DIN, .data_in_num = -1 };\n  i2s_set_pin(I2S_NUM_1, &pins);\n  Serial.println("[i2s_spk] OK 44.1kHz");\n}\nvoid i2s_spk_write(const int16_t* s, size_t n) {\n  size_t written = 0;\n  i2s_write(I2S_NUM_1, s, n * 2, &written, portMAX_DELAY);\n}\nvoid i2s_spk_tone(uint16_t freq, uint16_t dur) {\n  int samples = SPK_RATE * dur / 1000;\n  int16_t buf[256];\n  for (int i = 0; i < samples; i += 256) {\n    int chunk = (samples - i < 256) ? samples - i : 256;\n    for (int j = 0; j < chunk; j++) {\n      buf[j] = (int16_t)(sinf(2.0f * 3.14159f * freq * (i+j) / SPK_RATE) * 16000);\n    }\n    i2s_spk_write(buf, chunk);\n  }\n}\nvoid i2s_spk_stop() {\n  int16_t silence[64] = {0};\n  i2s_spk_write(silence, 64);\n}'},
    ],

    "freertos": [
        # ── FreeRTOS Task Manager — Official ESP-IDF API ──
        {"id": "freertos_tasks", "name": "FreeRTOS Task Manager", "libs": [],
         "lib_deps": [],
         "header": '#ifndef FREERTOS_TASKS_H\n#define FREERTOS_TASKS_H\n#include <Arduino.h>\nvoid task_manager_setup();\nvoid task_create(const char* name, void (*fn)(void*), uint32_t stack, int priority, int core);\nvoid task_delay_ms(uint32_t ms);\nuint32_t task_get_free_heap();\n#endif',
         "source": '#include "freertos_tasks.h"\nvoid task_manager_setup() {\n  Serial.printf("[rtos] Free heap: %lu bytes\\n", (unsigned long)ESP.getFreeHeap());\n  Serial.printf("[rtos] Cores: %d\\n", ESP.getChipCores());\n}\nvoid task_create(const char* name, void (*fn)(void*), uint32_t stack, int pri, int core) {\n  BaseType_t r = xTaskCreatePinnedToCore(fn, name, stack, NULL, pri, NULL, core);\n  Serial.printf("[rtos] Task \'%s\' on core %d: %s\\n", name, core, r == pdPASS ? "OK" : "FAIL");\n}\nvoid task_delay_ms(uint32_t ms) { vTaskDelay(ms / portTICK_PERIOD_MS); }\nuint32_t task_get_free_heap() { return ESP.getFreeHeap(); }'},
    ],
}
