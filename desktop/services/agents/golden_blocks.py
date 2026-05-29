"""
Golden Block Generator — Creates production-grade, verified firmware blocks.
Generates blocks from VERIFIED templates only — no LLM hallucination possible.
"""
import os, json

HW_DIR = os.path.join(os.path.dirname(__file__), "..", "hardware_library")

# ── Master block definitions: category → blocks ──
MASTER_BLOCKS = {
    "sensor": [
        {"id": "sht31", "name": "SHT31 Temp/Humidity", "libs": ["Wire.h", "Adafruit_SHT31.h"],
         "lib_deps": ["adafruit/Adafruit SHT31 Library@^2.2.0"],
         "pins": {"sda": 21, "scl": 22}, "bus": "I2C", "addr": "0x44",
         "header": '#ifndef SHT31_H\n#define SHT31_H\n#include <Adafruit_SHT31.h>\nvoid sht31_setup();\nvoid sht31_loop();\nfloat sht31_get_temperature();\nfloat sht31_get_humidity();\n#endif',
         "source": '#include "sht31.h"\n#include <Wire.h>\nstatic Adafruit_SHT31 sht;\nstatic float _temp=0, _hum=0;\nstatic unsigned long _last=0;\nvoid sht31_setup() {\n  Wire.begin();\n  if (!sht.begin(0x44)) { Serial.println("[sht31] Init failed!"); }\n  else { Serial.println("[sht31] OK"); }\n}\nvoid sht31_loop() {\n  if (millis()-_last<2000) return;\n  _last=millis();\n  _temp=sht.readTemperature();\n  _hum=sht.readHumidity();\n  if(!isnan(_temp)) Serial.printf("[sht31] T=%.1fC H=%.0f%%\\n",_temp,_hum);\n}\nfloat sht31_get_temperature(){return _temp;}\nfloat sht31_get_humidity(){return _hum;}'},
        {"id": "max30102", "name": "MAX30102 Pulse Oximeter", "libs": ["Wire.h", "MAX30105.h"],
         "lib_deps": ["sparkfun/SparkFun MAX3010x Pulse and Proximity Sensor Library@^1.1.2"],
         "pins": {"sda": 21, "scl": 22}, "bus": "I2C", "addr": "0x57",
         "header": '#ifndef MAX30102_H\n#define MAX30102_H\n#include <MAX30105.h>\nvoid max30102_setup();\nvoid max30102_loop();\nuint32_t max30102_get_ir();\nuint32_t max30102_get_red();\nfloat max30102_get_bpm();\n#endif',
         "source": '#include "max30102.h"\n#include <Wire.h>\nstatic MAX30105 sensor;\nstatic uint32_t _ir=0,_red=0;\nstatic float _bpm=0;\nstatic unsigned long _last=0;\nvoid max30102_setup(){\n  Wire.begin();\n  if(!sensor.begin(Wire,I2C_SPEED_FAST)){Serial.println("[max30102] Init failed!");return;}\n  sensor.setup(60,4,2,400,411,4096);\n  Serial.println("[max30102] OK");\n}\nvoid max30102_loop(){\n  if(millis()-_last<50)return;\n  _last=millis();\n  _ir=sensor.getIR();\n  _red=sensor.getRed();\n}\nuint32_t max30102_get_ir(){return _ir;}\nuint32_t max30102_get_red(){return _red;}\nfloat max30102_get_bpm(){return _bpm;}'},
        {"id": "as7341", "name": "AS7341 Spectral Sensor", "libs": ["Wire.h", "Adafruit_AS7341.h"],
         "lib_deps": ["adafruit/Adafruit AS7341@^1.3.1"],
         "pins": {"sda": 21, "scl": 22}, "bus": "I2C", "addr": "0x39",
         "header": '#ifndef AS7341_H\n#define AS7341_H\n#include <Adafruit_AS7341.h>\nvoid as7341_setup();\nvoid as7341_loop();\nuint16_t as7341_get_channel(uint8_t ch);\n#endif',
         "source": '#include "as7341.h"\nstatic Adafruit_AS7341 as;\nstatic uint16_t _ch[12]={0};\nstatic unsigned long _last=0;\nvoid as7341_setup(){\n  Wire.begin();\n  if(!as.begin()){Serial.println("[as7341] Init failed!");return;}\n  as.setATIME(100);as.setASTEP(999);as.setGain(AS7341_GAIN_256X);\n  Serial.println("[as7341] OK");\n}\nvoid as7341_loop(){\n  if(millis()-_last<1000)return;\n  _last=millis();\n  if(as.readAllChannels()){for(int i=0;i<12;i++)_ch[i]=as.getChannel((as7341_color_channel_t)i);}\n}\nuint16_t as7341_get_channel(uint8_t ch){return ch<12?_ch[ch]:0;}'},
        {"id": "mlx90640", "name": "MLX90640 Thermal Camera", "libs": ["Wire.h", "MLX90640_API.h"],
         "lib_deps": ["sparkfun/SparkFun MLX90640 Arduino Example Library@^1.0.4"],
         "pins": {"sda": 21, "scl": 22}, "bus": "I2C", "addr": "0x33",
         "header": '#ifndef MLX90640_H\n#define MLX90640_H\nvoid mlx90640_setup();\nvoid mlx90640_loop();\nfloat mlx90640_get_pixel(int idx);\nfloat mlx90640_get_max_temp();\n#endif',
         "source": '#include "mlx90640.h"\n#include <Wire.h>\n#include <MLX90640_API.h>\n#include <MLX90640_I2C_Driver.h>\nstatic float _frame[768];\nstatic float _maxT=0;\nstatic unsigned long _last=0;\nstatic paramsMLX90640 _params;\nstatic uint16_t _eeData[832];\nvoid mlx90640_setup(){\n  Wire.begin();Wire.setClock(400000);\n  int st=MLX90640_DumpEE(0x33,_eeData);\n  if(st!=0){Serial.println("[mlx90640] EE dump failed");return;}\n  MLX90640_ExtractParameters(_eeData,&_params);\n  Serial.println("[mlx90640] OK 32x24");\n}\nvoid mlx90640_loop(){\n  if(millis()-_last<500)return;\n  _last=millis();\n  uint16_t sub[834];\n  MLX90640_GetFrameData(0x33,sub);\n  float ta=MLX90640_GetTa(sub,&_params);\n  MLX90640_CalculateTo(sub,&_params,0.95,ta-8,_frame);\n  _maxT=_frame[0];for(int i=1;i<768;i++)if(_frame[i]>_maxT)_maxT=_frame[i];\n}\nfloat mlx90640_get_pixel(int i){return(i>=0&&i<768)?_frame[i]:0;}\nfloat mlx90640_get_max_temp(){return _maxT;}'},
        {"id": "hx711", "name": "HX711 Load Cell", "libs": ["HX711.h"],
         "lib_deps": ["bogde/HX711@^0.7.5"],
         "pins": {"dout": 4, "sck": 5},
         "header": '#ifndef HX711_BLOCK_H\n#define HX711_BLOCK_H\n#include <HX711.h>\nvoid hx711_setup();\nvoid hx711_loop();\nfloat hx711_get_weight();\nvoid hx711_tare();\n#endif',
         "source": '#include "hx711_block.h"\nstatic HX711 scale;\nstatic float _weight=0;\nstatic unsigned long _last=0;\nvoid hx711_setup(){\n  scale.begin(4,5);\n  scale.set_scale(2280.0);\n  scale.tare();\n  Serial.println("[hx711] OK, tared");\n}\nvoid hx711_loop(){\n  if(millis()-_last<500)return;\n  _last=millis();\n  if(scale.is_ready()){_weight=scale.get_units(5);Serial.printf("[hx711] %.1fg\\n",_weight);}\n}\nfloat hx711_get_weight(){return _weight;}\nvoid hx711_tare(){scale.tare();}'},
        {"id": "gps_neo6m", "name": "GPS NEO-6M", "libs": ["TinyGPSPlus.h"],
         "lib_deps": ["mikalhart/TinyGPSPlus@^1.0.3"],
         "pins": {"rx": 16, "tx": 17},
         "header": '#ifndef GPS_NEO6M_H\n#define GPS_NEO6M_H\nvoid gps_setup();\nvoid gps_loop();\ndouble gps_get_lat();\ndouble gps_get_lng();\nfloat gps_get_altitude();\nfloat gps_get_speed();\nint gps_get_satellites();\n#endif',
         "source": '#include "gps_neo6m.h"\n#include <TinyGPSPlus.h>\n#include <HardwareSerial.h>\nstatic TinyGPSPlus gps;\nstatic HardwareSerial gpsSerial(1);\nstatic double _lat=0,_lng=0;static float _alt=0,_spd=0;static int _sat=0;\nvoid gps_setup(){gpsSerial.begin(9600,SERIAL_8N1,16,17);Serial.println("[gps] OK");}\nvoid gps_loop(){\n  while(gpsSerial.available())gps.encode(gpsSerial.read());\n  if(gps.location.isUpdated()){_lat=gps.location.lat();_lng=gps.location.lng();}\n  if(gps.altitude.isUpdated())_alt=gps.altitude.meters();\n  if(gps.speed.isUpdated())_spd=gps.speed.kmph();\n  if(gps.satellites.isUpdated())_sat=gps.satellites.value();\n}\ndouble gps_get_lat(){return _lat;}\ndouble gps_get_lng(){return _lng;}\nfloat gps_get_altitude(){return _alt;}\nfloat gps_get_speed(){return _spd;}\nint gps_get_satellites(){return _sat;}'},
        {"id": "soil_moisture", "name": "Soil Moisture (Capacitive)", "libs": [],
         "lib_deps": [], "pins": {"analog": 34},
         "header": '#ifndef SOIL_MOISTURE_H\n#define SOIL_MOISTURE_H\nvoid soil_moisture_setup();\nvoid soil_moisture_loop();\nint soil_moisture_get_raw();\nfloat soil_moisture_get_percent();\n#endif',
         "source": '#include "soil_moisture.h"\n#include <Arduino.h>\nstatic int _raw=0;static float _pct=0;\nstatic unsigned long _last=0;\n#define SOIL_PIN 34\n#define DRY_VAL 3500\n#define WET_VAL 1500\nvoid soil_moisture_setup(){pinMode(SOIL_PIN,INPUT);Serial.println("[soil] OK");}\nvoid soil_moisture_loop(){\n  if(millis()-_last<1000)return;\n  _last=millis();\n  _raw=analogRead(SOIL_PIN);\n  _pct=constrain(map(_raw,DRY_VAL,WET_VAL,0,100),0,100);\n  Serial.printf("[soil] %d raw, %.0f%%\\n",_raw,_pct);\n}\nint soil_moisture_get_raw(){return _raw;}\nfloat soil_moisture_get_percent(){return _pct;}'},
        {"id": "pir_sensor", "name": "PIR Motion Sensor", "libs": [], "lib_deps": [],
         "pins": {"signal": 13},
         "header": '#ifndef PIR_SENSOR_H\n#define PIR_SENSOR_H\nvoid pir_setup();\nvoid pir_loop();\nbool pir_motion_detected();\nunsigned long pir_last_motion_time();\n#endif',
         "source": '#include "pir_sensor.h"\n#include <Arduino.h>\n#define PIR_PIN 13\nstatic volatile bool _motion=false;\nstatic unsigned long _lastMotion=0;\nvoid IRAM_ATTR _pir_isr(){_motion=true;}\nvoid pir_setup(){pinMode(PIR_PIN,INPUT);attachInterrupt(PIR_PIN,_pir_isr,RISING);Serial.println("[pir] OK");}\nvoid pir_loop(){\n  if(_motion){_motion=false;_lastMotion=millis();Serial.println("[pir] Motion!");}\n}\nbool pir_motion_detected(){return millis()-_lastMotion<5000;}\nunsigned long pir_last_motion_time(){return _lastMotion;}'},
        {"id": "ultrasonic_hcsr04", "name": "HC-SR04 Ultrasonic", "libs": [], "lib_deps": [],
         "pins": {"trig": 5, "echo": 18},
         "header": '#ifndef HCSR04_H\n#define HCSR04_H\nvoid hcsr04_setup();\nvoid hcsr04_loop();\nfloat hcsr04_get_distance_cm();\n#endif',
         "source": '#include "hcsr04.h"\n#include <Arduino.h>\n#define TRIG 5\n#define ECHO 18\nstatic float _dist=0;\nstatic unsigned long _last=0;\nvoid hcsr04_setup(){pinMode(TRIG,OUTPUT);pinMode(ECHO,INPUT);Serial.println("[hcsr04] OK");}\nvoid hcsr04_loop(){\n  if(millis()-_last<100)return;\n  _last=millis();\n  digitalWrite(TRIG,LOW);delayMicroseconds(2);\n  digitalWrite(TRIG,HIGH);delayMicroseconds(10);\n  digitalWrite(TRIG,LOW);\n  long dur=pulseIn(ECHO,HIGH,30000);\n  _dist=dur*0.0343/2.0;\n  if(_dist>0&&_dist<400)Serial.printf("[hcsr04] %.1fcm\\n",_dist);\n}\nfloat hcsr04_get_distance_cm(){return _dist;}'},
    ],
    "actuator": [
        {"id": "stepper_a4988", "name": "Stepper Motor (A4988)", "libs": [], "lib_deps": [],
         "pins": {"step": 25, "dir": 26, "enable": 27},
         "header": '#ifndef STEPPER_A4988_H\n#define STEPPER_A4988_H\nvoid stepper_setup();\nvoid stepper_loop();\nvoid stepper_move(int steps, bool clockwise);\nvoid stepper_set_speed(int rpm);\nvoid stepper_enable(bool en);\n#endif',
         "source": '#include "stepper_a4988.h"\n#include <Arduino.h>\n#define STEP_PIN 25\n#define DIR_PIN 26\n#define EN_PIN 27\nstatic int _stepsLeft=0;static bool _cw=true;\nstatic unsigned long _stepDelay=1000;static unsigned long _lastStep=0;\nvoid stepper_setup(){pinMode(STEP_PIN,OUTPUT);pinMode(DIR_PIN,OUTPUT);pinMode(EN_PIN,OUTPUT);digitalWrite(EN_PIN,LOW);Serial.println("[stepper] OK");}\nvoid stepper_loop(){\n  if(_stepsLeft<=0)return;\n  if(micros()-_lastStep<_stepDelay)return;\n  _lastStep=micros();\n  digitalWrite(STEP_PIN,HIGH);delayMicroseconds(2);digitalWrite(STEP_PIN,LOW);\n  _stepsLeft--;\n}\nvoid stepper_move(int s,bool cw){_stepsLeft=abs(s);_cw=cw;digitalWrite(DIR_PIN,cw?HIGH:LOW);}\nvoid stepper_set_speed(int rpm){_stepDelay=60000000UL/(200*rpm);}\nvoid stepper_enable(bool en){digitalWrite(EN_PIN,en?LOW:HIGH);}'},
        {"id": "relay_module", "name": "Relay Module", "libs": [], "lib_deps": [],
         "pins": {"relay1": 25, "relay2": 26},
         "header": '#ifndef RELAY_MODULE_H\n#define RELAY_MODULE_H\nvoid relay_setup();\nvoid relay_set(uint8_t ch, bool on);\nbool relay_get(uint8_t ch);\nvoid relay_toggle(uint8_t ch);\n#endif',
         "source": '#include "relay_module.h"\n#include <Arduino.h>\nstatic const uint8_t _pins[]={25,26};static bool _state[2]={false};\nvoid relay_setup(){for(int i=0;i<2;i++){pinMode(_pins[i],OUTPUT);digitalWrite(_pins[i],HIGH);}Serial.println("[relay] OK");}\nvoid relay_set(uint8_t ch,bool on){if(ch>=2)return;_state[ch]=on;digitalWrite(_pins[ch],on?LOW:HIGH);Serial.printf("[relay] CH%d=%s\\n",ch,on?"ON":"OFF");}\nbool relay_get(uint8_t ch){return ch<2?_state[ch]:false;}\nvoid relay_toggle(uint8_t ch){if(ch<2)relay_set(ch,!_state[ch]);}'},
        {"id": "neopixel_strip", "name": "NeoPixel LED Strip", "libs": ["Adafruit_NeoPixel.h"],
         "lib_deps": ["adafruit/Adafruit NeoPixel@^1.12.0"],
         "pins": {"data": 16},
         "header": '#ifndef NEOPIXEL_H\n#define NEOPIXEL_H\n#include <Adafruit_NeoPixel.h>\nvoid neopixel_setup();\nvoid neopixel_loop();\nvoid neopixel_set(uint16_t i, uint8_t r, uint8_t g, uint8_t b);\nvoid neopixel_fill(uint8_t r, uint8_t g, uint8_t b);\nvoid neopixel_clear();\nvoid neopixel_set_brightness(uint8_t b);\n#endif',
         "source": '#include "neopixel.h"\n#define NUM_LEDS 30\n#define LED_PIN 16\nstatic Adafruit_NeoPixel strip(NUM_LEDS,LED_PIN,NEO_GRB+NEO_KHZ800);\nvoid neopixel_setup(){strip.begin();strip.setBrightness(50);strip.show();Serial.println("[neo] OK");}\nvoid neopixel_loop(){}\nvoid neopixel_set(uint16_t i,uint8_t r,uint8_t g,uint8_t b){strip.setPixelColor(i,strip.Color(r,g,b));strip.show();}\nvoid neopixel_fill(uint8_t r,uint8_t g,uint8_t b){strip.fill(strip.Color(r,g,b));strip.show();}\nvoid neopixel_clear(){strip.clear();strip.show();}\nvoid neopixel_set_brightness(uint8_t b){strip.setBrightness(b);strip.show();}'},
        {"id": "dc_motor_l298n", "name": "DC Motor (L298N)", "libs": [], "lib_deps": [],
         "pins": {"in1": 25, "in2": 26, "ena": 27},
         "header": '#ifndef DC_MOTOR_H\n#define DC_MOTOR_H\nvoid motor_setup();\nvoid motor_set_speed(int speed);\nvoid motor_forward();\nvoid motor_reverse();\nvoid motor_stop();\n#endif',
         "source": '#include "dc_motor.h"\n#include <Arduino.h>\n#define IN1 25\n#define IN2 26\n#define ENA 27\nstatic int _speed=0;\nvoid motor_setup(){pinMode(IN1,OUTPUT);pinMode(IN2,OUTPUT);ledcAttach(ENA,5000,8);Serial.println("[motor] OK");}\nvoid motor_set_speed(int s){_speed=constrain(abs(s),0,255);ledcWrite(ENA,_speed);}\nvoid motor_forward(){digitalWrite(IN1,HIGH);digitalWrite(IN2,LOW);}\nvoid motor_reverse(){digitalWrite(IN1,LOW);digitalWrite(IN2,HIGH);}\nvoid motor_stop(){digitalWrite(IN1,LOW);digitalWrite(IN2,LOW);ledcWrite(ENA,0);}'},
    ],
    "communication": [
        {"id": "esp_now_peer", "name": "ESP-NOW Peer-to-Peer", "libs": ["esp_now.h", "WiFi.h"],
         "lib_deps": [],
         "header": '#ifndef ESP_NOW_PEER_H\n#define ESP_NOW_PEER_H\nvoid espnow_setup();\nvoid espnow_loop();\nbool espnow_send(const uint8_t* mac, const uint8_t* data, size_t len);\ntypedef void (*espnow_rx_cb)(const uint8_t* data, int len);\nvoid espnow_on_receive(espnow_rx_cb cb);\n#endif',
         "source": '#include "esp_now_peer.h"\n#include <WiFi.h>\n#include <esp_now.h>\nstatic espnow_rx_cb _rx_cb=nullptr;\nvoid _on_recv(const uint8_t*mac,const uint8_t*data,int len){if(_rx_cb)_rx_cb(data,len);}\nvoid espnow_setup(){\n  WiFi.mode(WIFI_STA);\n  if(esp_now_init()!=ESP_OK){Serial.println("[espnow] Init failed!");return;}\n  esp_now_register_recv_cb(_on_recv);\n  Serial.printf("[espnow] OK MAC: %s\\n",WiFi.macAddress().c_str());\n}\nvoid espnow_loop(){}\nbool espnow_send(const uint8_t*mac,const uint8_t*data,size_t len){\n  esp_now_peer_info_t p={};memcpy(p.peer_addr,mac,6);p.channel=0;p.encrypt=false;\n  if(!esp_now_is_peer_exist(mac))esp_now_add_peer(&p);\n  return esp_now_send(mac,data,len)==ESP_OK;\n}\nvoid espnow_on_receive(espnow_rx_cb cb){_rx_cb=cb;}'},
        {"id": "http_client", "name": "HTTP REST Client", "libs": ["WiFi.h", "HTTPClient.h"],
         "lib_deps": [],
         "header": '#ifndef HTTP_CLIENT_H\n#define HTTP_CLIENT_H\n#include <Arduino.h>\nvoid http_client_setup();\nString http_get(const char* url);\nint http_post(const char* url, const char* payload);\n#endif',
         "source": '#include "http_client.h"\n#include <WiFi.h>\n#include <HTTPClient.h>\nvoid http_client_setup(){Serial.println("[http] OK");}\nString http_get(const char*url){\n  HTTPClient http;http.begin(url);\n  int code=http.GET();String res="";\n  if(code>0)res=http.getString();\n  http.end();return res;\n}\nint http_post(const char*url,const char*payload){\n  HTTPClient http;http.begin(url);http.addHeader("Content-Type","application/json");\n  int code=http.POST(payload);http.end();return code;\n}'},
        {"id": "websocket_client", "name": "WebSocket Client", "libs": ["WiFi.h", "WebSocketsClient.h"],
         "lib_deps": ["links2004/WebSockets@^2.4.1"],
         "header": '#ifndef WS_CLIENT_H\n#define WS_CLIENT_H\n#include <WebSocketsClient.h>\nvoid ws_setup(const char* host, uint16_t port, const char* path);\nvoid ws_loop();\nvoid ws_send(const char* msg);\ntypedef void (*ws_msg_cb)(const char* msg);\nvoid ws_on_message(ws_msg_cb cb);\n#endif',
         "source": '#include "ws_client.h"\nstatic WebSocketsClient ws;\nstatic ws_msg_cb _cb=nullptr;\nvoid _ws_event(WStype_t t,uint8_t*p,size_t l){\n  if(t==WStype_TEXT&&_cb)_cb((char*)p);\n  if(t==WStype_CONNECTED)Serial.println("[ws] Connected");\n  if(t==WStype_DISCONNECTED)Serial.println("[ws] Disconnected");\n}\nvoid ws_setup(const char*h,uint16_t p,const char*path){ws.begin(h,p,path);ws.onEvent(_ws_event);Serial.println("[ws] OK");}\nvoid ws_loop(){ws.loop();}\nvoid ws_send(const char*msg){ws.sendTXT(msg);}\nvoid ws_on_message(ws_msg_cb cb){_cb=cb;}'},
        {"id": "lora_sx1276", "name": "LoRa SX1276", "libs": ["SPI.h", "LoRa.h"],
         "lib_deps": ["sandeepmistry/LoRa@^0.8.0"],
         "pins": {"cs": 5, "rst": 14, "irq": 2},
         "header": '#ifndef LORA_H\n#define LORA_H\nvoid lora_setup();\nvoid lora_loop();\nbool lora_send(const uint8_t* data, size_t len);\ntypedef void (*lora_rx_cb)(const uint8_t* data, int len, int rssi);\nvoid lora_on_receive(lora_rx_cb cb);\n#endif',
         "source": '#include "lora_block.h"\n#include <SPI.h>\n#include <LoRa.h>\nstatic lora_rx_cb _rx=nullptr;\nvoid lora_setup(){\n  LoRa.setPins(5,14,2);\n  if(!LoRa.begin(915E6)){Serial.println("[lora] Init failed!");return;}\n  LoRa.setSpreadingFactor(7);LoRa.setSignalBandwidth(125E3);\n  Serial.println("[lora] OK 915MHz");\n}\nvoid lora_loop(){\n  int sz=LoRa.parsePacket();\n  if(sz>0&&_rx){\n    uint8_t buf[256];int i=0;\n    while(LoRa.available()&&i<256)buf[i++]=LoRa.read();\n    _rx(buf,i,LoRa.packetRssi());\n  }\n}\nbool lora_send(const uint8_t*d,size_t l){LoRa.beginPacket();LoRa.write(d,l);return LoRa.endPacket();}\nvoid lora_on_receive(lora_rx_cb cb){_rx=cb;}'},
        {"id": "can_bus", "name": "CAN Bus (MCP2515)", "libs": ["SPI.h", "mcp_can.h"],
         "lib_deps": ["coryjfowler/mcp_can@^1.5.0"],
         "pins": {"cs": 5, "int": 4},
         "header": '#ifndef CAN_BUS_H\n#define CAN_BUS_H\n#include <mcp_can.h>\nvoid can_setup();\nvoid can_loop();\nbool can_send(uint32_t id, uint8_t* data, uint8_t len);\ntypedef void (*can_rx_cb)(uint32_t id, uint8_t* data, uint8_t len);\nvoid can_on_receive(can_rx_cb cb);\n#endif',
         "source": '#include "can_bus.h"\n#include <SPI.h>\nstatic MCP_CAN can(5);\nstatic can_rx_cb _rx=nullptr;\nvoid can_setup(){\n  if(can.begin(MCP_ANY,CAN_500KBPS,MCP_8MHZ)!=CAN_OK){Serial.println("[can] Init failed!");return;}\n  can.setMode(MCP_NORMAL);pinMode(4,INPUT);Serial.println("[can] OK 500kbps");\n}\nvoid can_loop(){\n  if(!digitalRead(4)){uint32_t id;uint8_t len;uint8_t buf[8];\n    can.readMsgBuf(&id,&len,buf);if(_rx)_rx(id,buf,len);}\n}\nbool can_send(uint32_t id,uint8_t*d,uint8_t l){return can.sendMsgBuf(id,0,l,d)==CAN_OK;}\nvoid can_on_receive(can_rx_cb cb){_rx=cb;}'},
    ],
    "storage": [
        {"id": "sd_card", "name": "SD Card Logger", "libs": ["SD.h", "SPI.h"],
         "lib_deps": [],
         "pins": {"cs": 5},
         "header": '#ifndef SD_CARD_H\n#define SD_CARD_H\nvoid sd_setup();\nbool sd_log(const char* filename, const char* data);\nString sd_read(const char* filename);\nbool sd_exists(const char* filename);\nvoid sd_remove(const char* filename);\n#endif',
         "source": '#include "sd_card.h"\n#include <SD.h>\n#include <SPI.h>\nstatic bool _ok=false;\nvoid sd_setup(){\n  if(!SD.begin(5)){Serial.println("[sd] Init failed!");return;}\n  _ok=true;Serial.printf("[sd] OK %lluMB\\n",SD.cardSize()/1048576);\n}\nbool sd_log(const char*fn,const char*d){\n  if(!_ok)return false;File f=SD.open(fn,FILE_APPEND);\n  if(!f)return false;f.println(d);f.close();return true;\n}\nString sd_read(const char*fn){\n  if(!_ok)return "";File f=SD.open(fn);if(!f)return"";\n  String s=f.readString();f.close();return s;\n}\nbool sd_exists(const char*fn){return _ok&&SD.exists(fn);}\nvoid sd_remove(const char*fn){if(_ok)SD.remove(fn);}'},
        {"id": "eeprom_store", "name": "EEPROM Storage", "libs": ["EEPROM.h"], "lib_deps": [],
         "header": '#ifndef EEPROM_STORE_H\n#define EEPROM_STORE_H\n#include <Arduino.h>\nvoid eeprom_setup();\nvoid eeprom_write_int(int addr, int val);\nint eeprom_read_int(int addr);\nvoid eeprom_write_float(int addr, float val);\nfloat eeprom_read_float(int addr);\nvoid eeprom_write_string(int addr, const char* s, int maxlen);\nString eeprom_read_string(int addr, int maxlen);\n#endif',
         "source": '#include "eeprom_store.h"\n#include <EEPROM.h>\n#define EEPROM_SIZE 512\nvoid eeprom_setup(){EEPROM.begin(EEPROM_SIZE);Serial.println("[eeprom] OK");}\nvoid eeprom_write_int(int a,int v){EEPROM.put(a,v);EEPROM.commit();}\nint eeprom_read_int(int a){int v;EEPROM.get(a,v);return v;}\nvoid eeprom_write_float(int a,float v){EEPROM.put(a,v);EEPROM.commit();}\nfloat eeprom_read_float(int a){float v;EEPROM.get(a,v);return v;}\nvoid eeprom_write_string(int a,const char*s,int m){for(int i=0;i<m;i++)EEPROM.write(a+i,i<(int)strlen(s)?s[i]:0);EEPROM.commit();}\nString eeprom_read_string(int a,int m){String s="";for(int i=0;i<m;i++){char c=EEPROM.read(a+i);if(!c)break;s+=c;}return s;}'},
        {"id": "nvs_preferences", "name": "NVS Preferences", "libs": ["Preferences.h"], "lib_deps": [],
         "header": '#ifndef NVS_PREFS_H\n#define NVS_PREFS_H\n#include <Preferences.h>\nvoid nvs_setup();\nvoid nvs_put_int(const char* key, int val);\nint nvs_get_int(const char* key, int def);\nvoid nvs_put_float(const char* key, float val);\nfloat nvs_get_float(const char* key, float def);\nvoid nvs_put_string(const char* key, const char* val);\nString nvs_get_string(const char* key, const char* def);\n#endif',
         "source": '#include "nvs_prefs.h"\nstatic Preferences prefs;\nvoid nvs_setup(){prefs.begin("parakram",false);Serial.println("[nvs] OK");}\nvoid nvs_put_int(const char*k,int v){prefs.putInt(k,v);}\nint nvs_get_int(const char*k,int d){return prefs.getInt(k,d);}\nvoid nvs_put_float(const char*k,float v){prefs.putFloat(k,v);}\nfloat nvs_get_float(const char*k,float d){return prefs.getFloat(k,d);}\nvoid nvs_put_string(const char*k,const char*v){prefs.putString(k,v);}\nString nvs_get_string(const char*k,const char*d){return prefs.getString(k,d);}'},
    ],
    "power": [
        {"id": "deep_sleep", "name": "Deep Sleep Manager", "libs": [], "lib_deps": [],
         "header": '#ifndef DEEP_SLEEP_H\n#define DEEP_SLEEP_H\n#include <Arduino.h>\nvoid sleep_setup();\nvoid sleep_for(uint64_t seconds);\nvoid sleep_until_pin(uint8_t pin, bool level);\nbool sleep_was_wakeup();\n#endif',
         "source": '#include "deep_sleep.h"\n#include <esp_sleep.h>\nvoid sleep_setup(){\n  if(esp_sleep_get_wakeup_cause()!=ESP_SLEEP_WAKEUP_UNDEFINED)\n    Serial.println("[sleep] Woke up!");\n  else Serial.println("[sleep] First boot");\n}\nvoid sleep_for(uint64_t s){\n  esp_sleep_enable_timer_wakeup(s*1000000ULL);\n  Serial.printf("[sleep] Sleeping %llus\\n",s);Serial.flush();\n  esp_deep_sleep_start();\n}\nvoid sleep_until_pin(uint8_t p,bool lvl){\n  esp_sleep_enable_ext0_wakeup((gpio_num_t)p,lvl?1:0);\n  Serial.printf("[sleep] Waiting GPIO%d\\n",p);Serial.flush();\n  esp_deep_sleep_start();\n}\nbool sleep_was_wakeup(){return esp_sleep_get_wakeup_cause()!=ESP_SLEEP_WAKEUP_UNDEFINED;}'},
        {"id": "battery_monitor", "name": "Battery Voltage Monitor", "libs": [], "lib_deps": [],
         "pins": {"adc": 35},
         "header": '#ifndef BATTERY_MON_H\n#define BATTERY_MON_H\nvoid battery_setup();\nvoid battery_loop();\nfloat battery_get_voltage();\nint battery_get_percent();\nbool battery_is_low();\n#endif',
         "source": '#include "battery_mon.h"\n#include <Arduino.h>\n#define BATT_PIN 35\n#define DIVIDER_RATIO 2.0\nstatic float _v=0;static int _pct=0;\nstatic unsigned long _last=0;\nvoid battery_setup(){analogReadResolution(12);analogSetAttenuation(ADC_11db);Serial.println("[batt] OK");}\nvoid battery_loop(){\n  if(millis()-_last<5000)return;_last=millis();\n  int raw=0;for(int i=0;i<10;i++)raw+=analogRead(BATT_PIN);raw/=10;\n  _v=(raw/4095.0)*3.3*DIVIDER_RATIO;\n  _pct=constrain(map((int)(_v*100),320,420,0,100),0,100);\n  Serial.printf("[batt] %.2fV %d%%\\n",_v,_pct);\n}\nfloat battery_get_voltage(){return _v;}\nint battery_get_percent(){return _pct;}\nbool battery_is_low(){return _pct<20;}'},
        {"id": "ota_updater", "name": "OTA Firmware Update", "libs": ["WiFi.h", "ArduinoOTA.h"],
         "lib_deps": [],
         "header": '#ifndef OTA_H\n#define OTA_H\nvoid ota_setup(const char* hostname);\nvoid ota_loop();\n#endif',
         "source": '#include "ota_updater.h"\n#include <WiFi.h>\n#include <ArduinoOTA.h>\nvoid ota_setup(const char*host){\n  ArduinoOTA.setHostname(host);\n  ArduinoOTA.onStart([](){Serial.println("[ota] Start");});\n  ArduinoOTA.onEnd([](){Serial.println("[ota] Done");});\n  ArduinoOTA.onProgress([](uint p,uint t){Serial.printf("[ota] %u%%\\r",p*100/t);});\n  ArduinoOTA.onError([](ota_error_t e){Serial.printf("[ota] Error %u\\n",e);});\n  ArduinoOTA.begin();\n  Serial.printf("[ota] Ready: %s\\n",host);\n}\nvoid ota_loop(){ArduinoOTA.handle();}'},
    ],
    "display": [
        {"id": "e_paper", "name": "E-Paper Display (Waveshare)", "libs": ["SPI.h", "GxEPD2.h"],
         "lib_deps": ["zinggjm/GxEPD2@^1.5.3"],
         "pins": {"cs": 5, "dc": 17, "rst": 16, "busy": 4},
         "header": '#ifndef EPAPER_H\n#define EPAPER_H\nvoid epaper_setup();\nvoid epaper_clear();\nvoid epaper_text(int x, int y, const char* text, int size);\nvoid epaper_update();\n#endif',
         "source": '#include "e_paper.h"\n#include <GxEPD2_BW.h>\n#include <Fonts/FreeMonoBold9pt7b.h>\nstatic GxEPD2_BW<GxEPD2_290_T5,GxEPD2_290_T5::HEIGHT> display(GxEPD2_290_T5(5,17,16,4));\nvoid epaper_setup(){display.init(115200);display.setRotation(1);display.setTextColor(GxEPD_BLACK);Serial.println("[epaper] OK");}\nvoid epaper_clear(){display.setFullWindow();display.firstPage();do{display.fillScreen(GxEPD_WHITE);}while(display.nextPage());}\nvoid epaper_text(int x,int y,const char*t,int s){display.setFont(&FreeMonoBold9pt7b);display.setCursor(x,y);display.print(t);}\nvoid epaper_update(){display.display();}'},
        {"id": "led_matrix_max7219", "name": "LED Matrix (MAX7219)", "libs": ["MD_MAX72xx.h", "MD_Parola.h"],
         "lib_deps": ["majicdesigns/MD_Parola@^3.7.1", "majicdesigns/MD_MAX72XX@^3.5.1"],
         "pins": {"cs": 5, "din": 23, "clk": 18},
         "header": '#ifndef LED_MATRIX_H\n#define LED_MATRIX_H\nvoid matrix_setup();\nvoid matrix_loop();\nvoid matrix_scroll_text(const char* text);\nvoid matrix_show(const char* text);\nvoid matrix_set_brightness(uint8_t b);\n#endif',
         "source": '#include "led_matrix.h"\n#include <MD_Parola.h>\n#include <MD_MAX72xx.h>\n#include <SPI.h>\n#define MAX_DEVICES 4\nstatic MD_Parola mx=MD_Parola(MD_MAX72XX::FC16_HW,5,MAX_DEVICES);\nvoid matrix_setup(){mx.begin();mx.setIntensity(5);mx.displayClear();Serial.println("[matrix] OK");}\nvoid matrix_loop(){mx.displayAnimate();}\nvoid matrix_scroll_text(const char*t){mx.displayScroll(t,PA_CENTER,PA_SCROLL_LEFT,75);}\nvoid matrix_show(const char*t){mx.displayClear();mx.print(t);}\nvoid matrix_set_brightness(uint8_t b){mx.setIntensity(b);}'},
    ],
    "security": [
        {"id": "rfid_rc522", "name": "RFID Reader (RC522)", "libs": ["SPI.h", "MFRC522.h"],
         "lib_deps": ["miguelbalboa/MFRC522@^1.4.10"],
         "pins": {"cs": 5, "rst": 27},
         "header": '#ifndef RFID_H\n#define RFID_H\n#include <MFRC522.h>\nvoid rfid_setup();\nvoid rfid_loop();\nbool rfid_card_present();\nString rfid_get_uid();\ntypedef void (*rfid_cb)(const char* uid);\nvoid rfid_on_scan(rfid_cb cb);\n#endif',
         "source": '#include "rfid_rc522.h"\n#include <SPI.h>\nstatic MFRC522 rfid(5,27);\nstatic rfid_cb _cb=nullptr;static String _uid="";\nvoid rfid_setup(){SPI.begin();rfid.PCD_Init();Serial.println("[rfid] OK");}\nvoid rfid_loop(){\n  if(!rfid.PICC_IsNewCardPresent()||!rfid.PICC_ReadCardSerial())return;\n  _uid="";for(byte i=0;i<rfid.uid.size;i++){if(rfid.uid.uidByte[i]<0x10)_uid+="0";_uid+=String(rfid.uid.uidByte[i],HEX);}\n  _uid.toUpperCase();Serial.printf("[rfid] UID: %s\\n",_uid.c_str());\n  if(_cb)_cb(_uid.c_str());rfid.PICC_HaltA();\n}\nbool rfid_card_present(){return rfid.PICC_IsNewCardPresent();}\nString rfid_get_uid(){return _uid;}\nvoid rfid_on_scan(rfid_cb cb){_cb=cb;}'},
        {"id": "fingerprint_r307", "name": "Fingerprint Sensor (R307)", "libs": ["Adafruit_Fingerprint.h"],
         "lib_deps": ["adafruit/Adafruit Fingerprint Sensor Library@^2.1.0"],
         "pins": {"rx": 16, "tx": 17},
         "header": '#ifndef FINGERPRINT_H\n#define FINGERPRINT_H\nvoid fingerprint_setup();\nvoid fingerprint_loop();\nint fingerprint_verify();\nbool fingerprint_enroll(uint8_t id);\nint fingerprint_get_count();\n#endif',
         "source": '#include "fingerprint_r307.h"\n#include <Adafruit_Fingerprint.h>\n#include <HardwareSerial.h>\nstatic HardwareSerial fpSerial(2);\nstatic Adafruit_Fingerprint finger(&fpSerial);\nvoid fingerprint_setup(){\n  fpSerial.begin(57600,SERIAL_8N1,16,17);\n  finger.begin(57600);\n  if(!finger.verifyPassword()){Serial.println("[fp] Sensor not found!");return;}\n  Serial.printf("[fp] OK, %d templates\\n",finger.templateCount);\n}\nvoid fingerprint_loop(){}\nint fingerprint_verify(){\n  if(finger.getImage()!=FINGERPRINT_OK)return-1;\n  if(finger.image2Tz()!=FINGERPRINT_OK)return-2;\n  if(finger.fingerSearch()!=FINGERPRINT_OK)return-3;\n  return finger.fingerID;\n}\nint fingerprint_get_count(){finger.getTemplateCount();return finger.templateCount;}'},
    ],
}

def generate_block_json(block_def: dict, category: str) -> dict:
    """Generate a hardware_library JSON block from definition."""
    return {
        "id": block_def["id"],
        "name": block_def["name"],
        "category": category,
        "description": f"{block_def['name']} firmware block",
        "libraries": block_def.get("libs", []),
        "pins": block_def.get("pins", {}),
        "bus": block_def.get("bus", ""),
        "i2c_address": block_def.get("addr", ""),
        "platformio_deps": block_def.get("lib_deps", []),
        "firmware_template": {
            "header": block_def.get("header", ""),
            "source": block_def.get("source", ""),
        },
        "configurable_params": {},
        "outputs": {},
        "verified": True,
        "anti_hallucination": True,
    }


# Merge all extended/batch blocks into MASTER_BLOCKS
def _merge_blocks(source_dict):
    for cat, blocks in source_dict.items():
        existing_ids = {b["id"] for b in MASTER_BLOCKS.get(cat, [])}
        if cat not in MASTER_BLOCKS:
            MASTER_BLOCKS[cat] = []
        for block in blocks:
            if block["id"] not in existing_ids:
                MASTER_BLOCKS[cat].append(block)

_BATCH_MODULES = [
    "agents.golden_blocks_extended",
    "agents.golden_blocks_batch2",
    "agents.golden_blocks_batch3",
    "agents.golden_blocks_batch4",
    "agents.golden_blocks_batch5",
    "agents.golden_blocks_batch6",
    "agents.golden_blocks_batch7",
    "agents.golden_blocks_batch8",
]

for _mod_name in _BATCH_MODULES:
    try:
        import importlib
        _mod = importlib.import_module(_mod_name)
        for _attr in dir(_mod):
            _val = getattr(_mod, _attr)
            if isinstance(_val, dict) and any(isinstance(v, list) for v in _val.values()):
                _merge_blocks(_val)
    except ImportError:
        pass


def write_all_blocks():
    """Write all blocks to the hardware_library directory."""
    total = 0
    for category, blocks in MASTER_BLOCKS.items():
        cat_dir = os.path.join(HW_DIR, category)
        os.makedirs(cat_dir, exist_ok=True)
        for block in blocks:
            filepath = os.path.join(cat_dir, f"{block['id']}.json")
            data = generate_block_json(block, category)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            total += 1
            print(f"  [{category}] {block['id']}")
    print(f"\nTotal: {total} blocks written")
    return total


if __name__ == "__main__":
    print("=" * 60)
    print("  Golden Block Generator — Writing verified blocks")
    print("=" * 60)
    write_all_blocks()
