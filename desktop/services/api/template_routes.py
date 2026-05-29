"""
Project Templates -- pre-built starter projects for common IoT use cases.

Each template defines a complete graph with nodes, edges, and configuration
that gets loaded onto the canvas instantly.
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


# ─── Template definitions ────────────────────────────────────

TEMPLATES = {
    "smart_home": {
        "id": "smart_home",
        "name": "🏠 Smart Home Hub",
        "description": "WiFi + MQTT + DHT22 + Relay + OLED display. Reads temperature/humidity and publishes to MQTT broker. OLED shows current readings.",
        "difficulty": "beginner",
        "blocks": ["wifi_station", "mqtt_client", "dht22_temperature_humidity", "led_output", "i2c_oled", "threshold_logic", "ntp_client", "ota_updater"],
        "graph": {
            "nodes": [
                {"id": "wifi_1", "name": "WiFi Station", "category": "communication", "configuration": {"ssid": "MyNetwork", "password": ""}, "position": {"x": 50, "y": 200}},
                {"id": "mqtt_1", "name": "MQTT Client", "category": "communication", "configuration": {"broker": "mqtt.example.com", "topic": "home/sensors"}, "position": {"x": 300, "y": 100}},
                {"id": "sensor_1", "name": "DHT22 Sensor", "category": "sensor", "configuration": {"pin": "4"}, "position": {"x": 50, "y": 50}},
                {"id": "oled_1", "name": "I2C OLED", "category": "display", "configuration": {"i2c_address": "0x3C"}, "position": {"x": 300, "y": 300}},
                {"id": "logic_1", "name": "Threshold Logic", "category": "logic", "configuration": {"threshold": "30.0", "comparison": "greater_than"}, "position": {"x": 300, "y": 200}},
                {"id": "relay_1", "name": "LED Output", "category": "actuator", "configuration": {"pin": "2"}, "position": {"x": 550, "y": 200}},
                {"id": "ntp_1", "name": "NTP Time Sync", "category": "communication", "configuration": {"gmt_offset": "19800"}, "position": {"x": 50, "y": 350}},
                {"id": "ota_1", "name": "OTA Updates", "category": "communication", "configuration": {"hostname": "smart-home"}, "position": {"x": 550, "y": 350}},
            ],
            "edges": [
                {"source": "sensor_1", "sourceHandle": "temperature", "target": "mqtt_1", "targetHandle": "data"},
                {"source": "sensor_1", "sourceHandle": "temperature", "target": "logic_1", "targetHandle": "value"},
                {"source": "sensor_1", "sourceHandle": "temperature", "target": "oled_1", "targetHandle": "text"},
                {"source": "logic_1", "sourceHandle": "triggered", "target": "relay_1", "targetHandle": "trigger"},
                {"source": "wifi_1", "sourceHandle": "connected", "target": "mqtt_1", "targetHandle": "wifi_connected"},
                {"source": "wifi_1", "sourceHandle": "connected", "target": "ntp_1", "targetHandle": "wifi_connected"},
                {"source": "wifi_1", "sourceHandle": "connected", "target": "ota_1", "targetHandle": "wifi_connected"},
            ],
        },
    },
    "weather_station": {
        "id": "weather_station",
        "name": "🌦️ Weather Station",
        "description": "BME280 + BH1750 + WiFi + HTTP Client. Reads temp/humidity/pressure/lux and posts data to a REST API. Includes signal filtering.",
        "difficulty": "intermediate",
        "blocks": ["wifi_station", "bme280", "bh1750", "http_client", "i2c_oled", "serial_output"],
        "graph": {
            "nodes": [
                {"id": "wifi_1", "name": "WiFi Station", "category": "communication", "configuration": {"ssid": "WeatherNet", "password": ""}, "position": {"x": 50, "y": 250}},
                {"id": "bme_1", "name": "BME280", "category": "sensor", "configuration": {"i2c_address": "0x76", "sda_pin": "21", "scl_pin": "22"}, "position": {"x": 50, "y": 50}},
                {"id": "light_1", "name": "BH1750 Light", "category": "sensor", "configuration": {"i2c_address": "0x23"}, "position": {"x": 50, "y": 150}},
                {"id": "http_1", "name": "HTTP Client", "category": "communication", "configuration": {"url": "http://api.example.com/weather", "method": "POST"}, "position": {"x": 350, "y": 150}},
                {"id": "oled_1", "name": "I2C OLED", "category": "display", "configuration": {"i2c_address": "0x3C"}, "position": {"x": 350, "y": 300}},
                {"id": "serial_1", "name": "Serial Output", "category": "output", "configuration": {"baud_rate": "115200"}, "position": {"x": 350, "y": 50}},
            ],
            "edges": [
                {"source": "bme_1", "sourceHandle": "temperature", "target": "http_1", "targetHandle": "data"},
                {"source": "bme_1", "sourceHandle": "temperature", "target": "serial_1", "targetHandle": "data"},
                {"source": "bme_1", "sourceHandle": "temperature", "target": "oled_1", "targetHandle": "text"},
                {"source": "light_1", "sourceHandle": "lux", "target": "http_1", "targetHandle": "data"},
                {"source": "wifi_1", "sourceHandle": "connected", "target": "http_1", "targetHandle": "wifi_connected"},
            ],
        },
    },
    "iot_gateway": {
        "id": "iot_gateway",
        "name": "🌐 Industrial IoT Gateway",
        "description": "FreeRTOS multi-task architecture. Sensors on Core 0, WiFi/MQTT on Core 1. ADS1115 + INA219 + TLS + BLE + RTOS tasks.",
        "difficulty": "advanced",
        "blocks": ["wifi_station", "mqtt_client", "ads1115", "ina219", "tls_config", "ble_server", "rtos_task", "rtos_semaphore", "rtos_queue"],
        "graph": {
            "nodes": [
                {"id": "wifi_1", "name": "WiFi Station", "category": "communication", "configuration": {"ssid": "Industrial", "password": ""}, "position": {"x": 50, "y": 250}},
                {"id": "mqtt_1", "name": "MQTT Client", "category": "communication", "configuration": {"broker": "mqtt.factory.local", "topic": "factory/sensors"}, "position": {"x": 350, "y": 250}},
                {"id": "tls_1", "name": "TLS Config", "category": "security", "configuration": {"verify_server": "true"}, "position": {"x": 50, "y": 350}},
                {"id": "adc_1", "name": "ADS1115 ADC", "category": "sensor", "configuration": {"i2c_address": "0x48", "gain": "GAIN_ONE"}, "position": {"x": 50, "y": 50}},
                {"id": "power_1", "name": "INA219 Power", "category": "sensor", "configuration": {"i2c_address": "0x40"}, "position": {"x": 50, "y": 150}},
                {"id": "ble_1", "name": "BLE Server", "category": "communication", "configuration": {"device_name": "IIoT-Gateway"}, "position": {"x": 350, "y": 350}},
                {"id": "task_1", "name": "FreeRTOS Task", "category": "freertos", "configuration": {"task_name": "sensor_task", "core_id": "0", "priority": "8"}, "position": {"x": 350, "y": 50}},
                {"id": "mutex_1", "name": "FreeRTOS Mutex", "category": "freertos", "configuration": {"sem_name": "i2c_mutex"}, "position": {"x": 350, "y": 150}},
                {"id": "queue_1", "name": "FreeRTOS Queue", "category": "freertos", "configuration": {"queue_length": "20", "item_size": "64"}, "position": {"x": 600, "y": 150}},
            ],
            "edges": [
                {"source": "adc_1", "sourceHandle": "channel_0", "target": "mqtt_1", "targetHandle": "data"},
                {"source": "power_1", "sourceHandle": "current_ma", "target": "mqtt_1", "targetHandle": "data"},
                {"source": "wifi_1", "sourceHandle": "connected", "target": "mqtt_1", "targetHandle": "wifi_connected"},
            ],
        },
    },
    "audio_intercom": {
        "id": "audio_intercom",
        "name": "🎤 Audio Intercom",
        "description": "I2S mic + speaker + audio processing + WebSocket streaming. Real-time audio with FFT analysis.",
        "difficulty": "advanced",
        "blocks": ["i2s_microphone", "i2s_speaker", "audio_processor", "wifi_station", "websocket_client", "rtos_task"],
        "graph": {
            "nodes": [
                {"id": "mic_1", "name": "I2S Microphone", "category": "audio", "configuration": {"bck_pin": "26", "ws_pin": "25", "data_pin": "22", "sample_rate": "16000"}, "position": {"x": 50, "y": 50}},
                {"id": "spk_1", "name": "I2S Speaker", "category": "audio", "configuration": {"bck_pin": "27", "ws_pin": "14", "data_pin": "12"}, "position": {"x": 50, "y": 200}},
                {"id": "proc_1", "name": "Audio Processor", "category": "audio", "configuration": {"fft_size": "1024"}, "position": {"x": 300, "y": 50}},
                {"id": "wifi_1", "name": "WiFi Station", "category": "communication", "configuration": {"ssid": "IntercomNet"}, "position": {"x": 300, "y": 300}},
                {"id": "ws_1", "name": "WebSocket", "category": "communication", "configuration": {"ws_url": "ws://192.168.1.100:8080"}, "position": {"x": 550, "y": 150}},
                {"id": "task_1", "name": "FreeRTOS Task", "category": "freertos", "configuration": {"task_name": "audio_task", "core_id": "0", "priority": "10", "stack_size": "8192"}, "position": {"x": 550, "y": 50}},
            ],
            "edges": [
                {"source": "mic_1", "sourceHandle": "audio_data", "target": "proc_1", "targetHandle": "audio_data"},
                {"source": "mic_1", "sourceHandle": "audio_data", "target": "ws_1", "targetHandle": "message_out"},
                {"source": "ws_1", "sourceHandle": "message_in", "target": "spk_1", "targetHandle": "audio_data"},
                {"source": "wifi_1", "sourceHandle": "connected", "target": "ws_1", "targetHandle": "wifi_connected"},
            ],
        },
    },
    "lvgl_dashboard": {
        "id": "lvgl_dashboard",
        "name": "📊 LVGL Dashboard",
        "description": "LVGL display + BME280 + MPU6050. Shows sensor data on a TFT display with gauges and charts. Touch-enabled.",
        "difficulty": "intermediate",
        "blocks": ["lvgl_app", "spi_display", "bme280", "mpu6050", "rtos_task"],
        "graph": {
            "nodes": [
                {"id": "lvgl_1", "name": "LVGL Application", "category": "display", "configuration": {"screen_width": "320", "screen_height": "240", "rotation": "1"}, "position": {"x": 350, "y": 150}},
                {"id": "bme_1", "name": "BME280", "category": "sensor", "configuration": {"i2c_address": "0x76"}, "position": {"x": 50, "y": 50}},
                {"id": "imu_1", "name": "MPU6050 IMU", "category": "sensor", "configuration": {"i2c_address": "0x68"}, "position": {"x": 50, "y": 200}},
                {"id": "task_1", "name": "FreeRTOS Task", "category": "freertos", "configuration": {"task_name": "ui_task", "core_id": "1", "priority": "4", "stack_size": "16384"}, "position": {"x": 350, "y": 300}},
                {"id": "task_2", "name": "FreeRTOS Task", "category": "freertos", "configuration": {"task_name": "sensor_task", "core_id": "0", "priority": "8"}, "position": {"x": 50, "y": 350}},
            ],
            "edges": [
                {"source": "bme_1", "sourceHandle": "temperature", "target": "lvgl_1", "targetHandle": "data"},
                {"source": "imu_1", "sourceHandle": "accel_x", "target": "lvgl_1", "targetHandle": "data"},
            ],
        },
    },
}


@router.get("/list")
async def list_templates():
    """List all available project templates."""
    return {
        "templates": [
            {
                "id": t["id"],
                "name": t["name"],
                "description": t["description"],
                "difficulty": t["difficulty"],
                "block_count": len(t["blocks"]),
            }
            for t in TEMPLATES.values()
        ]
    }


@router.get("/{template_id}")
async def get_template(template_id: str):
    """Get the full template definition including graph data."""
    template = TEMPLATES.get(template_id)
    if not template:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")
    return template
