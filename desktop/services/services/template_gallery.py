"""
Community Template Gallery — Browse, publish, and import shared firmware projects.

Provides a local gallery of curated templates plus API scaffold for
community sharing.
"""
from typing import Optional


# Curated built-in template library
TEMPLATES = [
    {
        "id": "weather-station",
        "title": "IoT Weather Station",
        "description": "BME280 sensor with OLED display, MQTT reporting, and deep sleep",
        "author": "Parakram Team",
        "board": "esp32dev",
        "tags": ["sensor", "mqtt", "oled", "deepsleep"],
        "blocks": ["esp32_manifest", "bme280", "ssd1306_oled", "mqtt_client", "deep_sleep"],
        "difficulty": "beginner",
        "estimated_cost": 12.50,
        "downloads": 4820,
        "stars": 342,
    },
    {
        "id": "smart-garden",
        "title": "Automated Smart Garden",
        "description": "Soil moisture sensing, relay-controlled pump, Blynk dashboard",
        "author": "Parakram Team",
        "board": "esp32dev",
        "tags": ["agriculture", "relay", "sensor", "blynk"],
        "blocks": ["esp32_manifest", "soil_moisture", "relay_module", "dht22", "wifi_manager"],
        "difficulty": "intermediate",
        "estimated_cost": 18.00,
        "downloads": 3210,
        "stars": 287,
    },
    {
        "id": "air-quality-monitor",
        "title": "Air Quality Monitor",
        "description": "MQ-135 gas sensor, PM2.5 particulate, OLED + web dashboard",
        "author": "Parakram Team",
        "board": "esp32dev",
        "tags": ["air-quality", "environment", "dashboard"],
        "blocks": ["esp32_manifest", "mq2_gas", "bme280", "ssd1306_oled", "web_server"],
        "difficulty": "intermediate",
        "estimated_cost": 22.00,
        "downloads": 2890,
        "stars": 198,
    },
    {
        "id": "robot-car",
        "title": "WiFi Robot Car",
        "description": "L298N motor driver, ultrasonic obstacle avoidance, web control",
        "author": "Parakram Team",
        "board": "esp32dev",
        "tags": ["robotics", "motor", "ultrasonic", "web-control"],
        "blocks": ["esp32_manifest", "dc_motor_l298n", "hcsr04_ultrasonic", "servo_sg90", "web_server"],
        "difficulty": "intermediate",
        "estimated_cost": 28.00,
        "downloads": 5430,
        "stars": 456,
    },
    {
        "id": "water-quality",
        "title": "Aquaculture Water Monitor",
        "description": "pH, TDS, temperature monitoring with calibration and alerts",
        "author": "Parakram Team",
        "board": "esp32dev",
        "tags": ["water-quality", "aquaculture", "calibration"],
        "blocks": ["esp32_manifest", "ph_sensor", "tds_meter", "ds18b20", "lcd_i2c_16x2", "mqtt_client"],
        "difficulty": "advanced",
        "estimated_cost": 35.00,
        "downloads": 1980,
        "stars": 167,
    },
    {
        "id": "hme-automation",
        "title": "Home Automation Hub",
        "description": "Multi-relay control, PIR motion, temperature, MQTT + Home Assistant",
        "author": "Parakram Team",
        "board": "esp32dev",
        "tags": ["home-automation", "relay", "mqtt", "ha"],
        "blocks": ["esp32_manifest", "relay_module", "pir_sensor", "dht22", "mqtt_client", "ota_update"],
        "difficulty": "intermediate",
        "estimated_cost": 20.00,
        "downloads": 6120,
        "stars": 523,
    },
    {
        "id": "gps-tracker",
        "title": "GPS Asset Tracker",
        "description": "NEO-6M GPS, SIM800L cellular, SD card logging, geofencing",
        "author": "Parakram Team",
        "board": "esp32dev",
        "tags": ["gps", "tracking", "cellular", "logging"],
        "blocks": ["esp32_manifest", "gps_neo6m", "sim800l_gsm", "sd_card", "deep_sleep"],
        "difficulty": "advanced",
        "estimated_cost": 32.00,
        "downloads": 2340,
        "stars": 201,
    },
    {
        "id": "led-matrix",
        "title": "LED Matrix Display",
        "description": "WS2812B NeoPixel matrix with animations, web picker, music reactive",
        "author": "Parakram Team",
        "board": "esp32dev",
        "tags": ["led", "neopixel", "animation", "web-control"],
        "blocks": ["esp32_manifest", "neopixel_strip", "web_server", "microphone_i2s"],
        "difficulty": "beginner",
        "estimated_cost": 15.00,
        "downloads": 7890,
        "stars": 612,
    },
    {
        "id": "security-system",
        "title": "IoT Security System",
        "description": "PIR motion, door sensors, RFID access, Telegram/MQTT alerts",
        "author": "Parakram Team",
        "board": "esp32dev",
        "tags": ["security", "rfid", "alert", "motion"],
        "blocks": ["esp32_manifest", "pir_sensor", "rfid_rc522", "buzzer_passive", "mqtt_client", "relay_module"],
        "difficulty": "intermediate",
        "estimated_cost": 25.00,
        "downloads": 3670,
        "stars": 298,
    },
    {
        "id": "data-logger",
        "title": "Multi-Sensor Data Logger",
        "description": "BME280 + INA219 + ADS1115, SD card CSV logging, web plot viewer",
        "author": "Parakram Team",
        "board": "esp32dev",
        "tags": ["datalogger", "sd-card", "csv", "sensor"],
        "blocks": ["esp32_manifest", "bme280", "ina219_current", "ads1115_adc", "sd_card", "rtc_ds3231"],
        "difficulty": "intermediate",
        "estimated_cost": 30.00,
        "downloads": 2100,
        "stars": 187,
    },
    {
        "id": "pico-thermostat",
        "title": "Smart Thermostat (Pico W)",
        "description": "RP2040 PID-controlled thermostat with web dashboard",
        "author": "Parakram Team",
        "board": "pico_w",
        "tags": ["thermostat", "pid", "rp2040", "web"],
        "blocks": ["rp2040_manifest", "dht22", "relay_module", "ssd1306_oled", "web_server"],
        "difficulty": "intermediate",
        "estimated_cost": 16.00,
        "downloads": 1540,
        "stars": 134,
    },
    {
        "id": "stm32-motor-control",
        "title": "Precision Motor Control (STM32)",
        "description": "FOC motor control with encoder feedback on STM32F411",
        "author": "Parakram Team",
        "board": "stm32f411",
        "tags": ["motor", "foc", "stm32", "encoder"],
        "blocks": ["stm32_manifest", "dc_motor_l298n", "rotary_encoder", "ssd1306_oled"],
        "difficulty": "advanced",
        "estimated_cost": 22.00,
        "downloads": 980,
        "stars": 98,
    },
]


class TemplateGallery:
    """Manages the community template gallery."""

    def list_templates(
        self,
        category: Optional[str] = None,
        difficulty: Optional[str] = None,
        board: Optional[str] = None,
        search: Optional[str] = None,
    ) -> list[dict]:
        """List templates with optional filtering."""
        results = list(TEMPLATES)

        if category:
            results = [t for t in results if category in t["tags"]]
        if difficulty:
            results = [t for t in results if t["difficulty"] == difficulty]
        if board:
            results = [t for t in results if t["board"] == board]
        if search:
            q = search.lower()
            results = [t for t in results
                       if q in t["title"].lower() or q in t["description"].lower()
                       or any(q in tag for tag in t["tags"])]

        return sorted(results, key=lambda t: t["downloads"], reverse=True)

    def get_template(self, template_id: str) -> Optional[dict]:
        """Get a specific template by ID."""
        for t in TEMPLATES:
            if t["id"] == template_id:
                return t
        return None

    def get_categories(self) -> list[dict]:
        """Get unique categories/tags with counts."""
        tag_counts: dict[str, int] = {}
        for t in TEMPLATES:
            for tag in t["tags"]:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        return [{"tag": tag, "count": count}
                for tag, count in sorted(tag_counts.items(), key=lambda x: -x[1])]

    def get_stats(self) -> dict:
        """Get gallery statistics."""
        total = len(TEMPLATES)
        total_downloads = sum(t["downloads"] for t in TEMPLATES)
        boards = list({t["board"] for t in TEMPLATES})
        return {
            "total_templates": total,
            "total_downloads": total_downloads,
            "boards": boards,
            "difficulties": ["beginner", "intermediate", "advanced"],
        }
