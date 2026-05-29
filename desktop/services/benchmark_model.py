"""
Parakram Coder Benchmark — Compare firmware generation quality against 7B models.

Benchmarks:
  - CodeLlama-7B-Instruct
  - DeepSeek-Coder-6.7B-Instruct
  - StarCoder2-3B
  - Qwen2.5-Coder-1.5B (Parakram fine-tuned)

Metrics:
  - Compilability: Does the code compile with PlatformIO?
  - Keyword accuracy: Does it use correct APIs/functions?
  - MISRA compliance: How clean is the code?
  - Code length: Is it concise but complete?
  - Library correctness: Does it include right libraries?
"""

import json
from datetime import datetime
from pathlib import Path

BENCHMARK_PROMPTS = [
    # Basic GPIO
    {"id": "B01", "prompt": "Blink an LED on GPIO2 every 500ms on ESP32", "board": "esp32dev",
     "expected": ["pinMode", "digitalWrite", "delay", "OUTPUT"], "category": "basic", "difficulty": 1},
    {"id": "B02", "prompt": "Read a push button on GPIO4 and turn on LED on GPIO2 when pressed, ESP32", "board": "esp32dev",
     "expected": ["digitalRead", "digitalWrite", "INPUT_PULLUP"], "category": "basic", "difficulty": 1},

    # Sensors (I2C)
    {"id": "S01", "prompt": "Read temperature and humidity from BME280 over I2C on ESP32", "board": "esp32dev",
     "expected": ["Wire", "BME280", "readTemperature", "readHumidity", "begin"], "category": "sensor", "difficulty": 2},
    {"id": "S02", "prompt": "Read acceleration from MPU6050 over I2C and print X,Y,Z values", "board": "esp32dev",
     "expected": ["Wire", "MPU6050", "getAcceleration"], "category": "sensor", "difficulty": 2},
    {"id": "S03", "prompt": "Read distance from HC-SR04 ultrasonic sensor on ESP32, trig=GPIO5, echo=GPIO18", "board": "esp32dev",
     "expected": ["pulseIn", "trig", "echo", "duration", "distance"], "category": "sensor", "difficulty": 2},

    # Connectivity
    {"id": "C01", "prompt": "Connect ESP32 to WiFi and print IP address", "board": "esp32dev",
     "expected": ["WiFi", "begin", "status", "WL_CONNECTED", "localIP"], "category": "connectivity", "difficulty": 2},
    {"id": "C02", "prompt": "ESP32 MQTT client publishing temperature every 10 seconds to broker.hivemq.com", "board": "esp32dev",
     "expected": ["PubSubClient", "publish", "connect", "loop"], "category": "connectivity", "difficulty": 3},
    {"id": "C03", "prompt": "ESP32 BLE beacon broadcasting device name 'Parakram'", "board": "esp32dev",
     "expected": ["BLE", "advertising", "start", "setName"], "category": "connectivity", "difficulty": 3},

    # Display
    {"id": "D01", "prompt": "Show 'Hello World' on SSD1306 128x64 OLED via I2C on ESP32", "board": "esp32dev",
     "expected": ["SSD1306", "display", "drawString", "begin"], "category": "display", "difficulty": 2},
    {"id": "D02", "prompt": "NeoPixel rainbow animation on 16 LEDs, GPIO13, Arduino Uno", "board": "uno",
     "expected": ["NeoPixel", "setPixelColor", "show", "begin"], "category": "display", "difficulty": 3},

    # Power
    {"id": "P01", "prompt": "ESP32 deep sleep for 5 minutes, wake by timer", "board": "esp32dev",
     "expected": ["esp_deep_sleep", "timer_wakeup", "RTC_DATA_ATTR"], "category": "power", "difficulty": 2},
    {"id": "P02", "prompt": "ESP32 light sleep with GPIO wakeup on button press", "board": "esp32dev",
     "expected": ["esp_light_sleep", "gpio_wakeup", "esp_sleep_enable"], "category": "power", "difficulty": 3},

    # Motor Control
    {"id": "M01", "prompt": "Servo motor sweep 0-180 degrees on Arduino Uno pin 9", "board": "uno",
     "expected": ["Servo", "attach", "write"], "category": "actuator", "difficulty": 1},
    {"id": "M02", "prompt": "Stepper motor 200 steps clockwise using A4988 driver, ESP32", "board": "esp32dev",
     "expected": ["step", "direction", "pulse", "delay"], "category": "actuator", "difficulty": 2},

    # RTOS
    {"id": "R01", "prompt": "FreeRTOS two tasks: one reads sensor, other updates display, with queue, ESP32", "board": "esp32dev",
     "expected": ["xTaskCreate", "xQueueSend", "xQueueReceive", "vTaskDelay"], "category": "rtos", "difficulty": 3},

    # Protocol
    {"id": "PR01", "prompt": "SPI communication with MCP2515 CAN controller on ESP32", "board": "esp32dev",
     "expected": ["SPI", "MCP2515", "CAN", "begin"], "category": "protocol", "difficulty": 3},

    # Web Server
    {"id": "W01", "prompt": "ESP32 web server with REST API returning sensor data as JSON", "board": "esp32dev",
     "expected": ["WebServer", "server.on", "server.begin", "application/json"], "category": "web", "difficulty": 3},

    # Advanced
    {"id": "A01", "prompt": "WiFi weather station with BME280, SSD1306 OLED, MQTT to HiveMQ, deep sleep every 5min, ESP32", "board": "esp32dev",
     "expected": ["BME280", "SSD1306", "WiFi", "PubSubClient", "esp_deep_sleep"], "category": "advanced", "difficulty": 4},
    {"id": "A02", "prompt": "Smart relay controller: ESP32 web server, 4 relays on GPIO 12,13,14,27, REST API to toggle each", "board": "esp32dev",
     "expected": ["WebServer", "relay", "digitalWrite", "JSON", "toggle"], "category": "advanced", "difficulty": 4},

    # Cross-platform
    {"id": "X01", "prompt": "I2C scanner for Raspberry Pi Pico", "board": "pico",
     "expected": ["Wire", "beginTransmission", "endTransmission"], "category": "cross-platform", "difficulty": 2},
]


def score_generation(code: str, expected_keywords: list, category: str) -> dict:
    """Score a generated code sample."""
    code_lower = code.lower()

    # Keyword accuracy
    found = [kw for kw in expected_keywords if kw.lower() in code_lower]
    keyword_score = len(found) / len(expected_keywords) * 100 if expected_keywords else 100

    # Completeness checks
    has_setup = "void setup" in code_lower or "def setup" in code_lower
    has_loop = "void loop" in code_lower or "while" in code_lower
    has_include = "#include" in code_lower or "import" in code_lower
    has_serial = "serial" in code_lower

    completeness = sum([has_setup, has_loop, has_include, has_serial]) / 4 * 100

    # Code quality
    line_count = len(code.strip().split('\n'))
    has_comments = '//' in code or '/*' in code

    return {
        "keyword_score": round(keyword_score, 1),
        "keywords_found": found,
        "keywords_missing": [kw for kw in expected_keywords if kw.lower() not in code_lower],
        "completeness": round(completeness, 1),
        "has_setup": has_setup,
        "has_loop": has_loop,
        "has_includes": has_include,
        "has_comments": has_comments,
        "line_count": line_count,
        "char_count": len(code),
    }


def run_benchmark_report():
    """Generate a benchmark report template."""
    report = {
        "benchmark": "Parakram Firmware Generation Benchmark v1.0",
        "date": datetime.now().isoformat(),
        "prompts": len(BENCHMARK_PROMPTS),
        "categories": {},
        "models_to_test": [
            {"name": "Parakram-Coder-1.5B", "type": "fine-tuned", "base": "Qwen2.5-Coder-1.5B-Instruct"},
            {"name": "CodeLlama-7B-Instruct", "type": "baseline", "params": "7B"},
            {"name": "DeepSeek-Coder-6.7B", "type": "baseline", "params": "6.7B"},
            {"name": "StarCoder2-3B", "type": "baseline", "params": "3B"},
            {"name": "Qwen2.5-Coder-7B", "type": "baseline", "params": "7B"},
        ],
        "scoring": {
            "keyword_accuracy": "% of expected API functions/keywords found in output",
            "completeness": "Has setup(), loop(), includes, serial init",
            "compilability": "Compiles with PlatformIO (manual test)",
            "misra_score": "MISRA C:2012 compliance %",
        },
        "difficulty_scale": "1=trivial, 2=intermediate, 3=advanced, 4=complex project",
    }

    # Count by category
    for p in BENCHMARK_PROMPTS:
        cat = p["category"]
        if cat not in report["categories"]:
            report["categories"][cat] = 0
        report["categories"][cat] += 1

    return report


# Training data format for fine-tuning
TRAINING_FORMAT = """
## Retraining Strategy for Parakram-Coder

### Base Model: Qwen2.5-Coder-1.5B-Instruct

### Training Data Format (JSONL):
```json
{
  "messages": [
    {"role": "system", "content": "You are Parakram, an expert embedded firmware engineer..."},
    {"role": "user", "content": "<firmware prompt>"},
    {"role": "assistant", "content": "<complete, compilable firmware code>"}
  ]
}
```

### Data Sources:
1. PlatformIO example projects (scraped from GitHub)
2. ESP-IDF examples (official Espressif)
3. Arduino library examples
4. STM32Cube examples
5. Custom hand-written firmware for edge cases

### Training Recipe (QLoRA):
- Quantization: 4-bit NF4
- LoRA rank: 64
- LoRA alpha: 128
- Learning rate: 2e-4
- Epochs: 3-5
- Batch size: 4 (gradient accumulation 8)
- Max sequence length: 4096

### Benchmark Target:
- Beat CodeLlama-7B on keyword accuracy (>85%)
- Beat DeepSeek-Coder-6.7B on completeness (>90%)
- Achieve >70% first-attempt compilability
- MISRA compliance >60% on generated code
"""


if __name__ == "__main__":
    report = run_benchmark_report()
    print(json.dumps(report, indent=2))
    print(f"\nTotal prompts: {len(BENCHMARK_PROMPTS)}")
    print(f"Categories: {report['categories']}")
    print(f"\nModels to benchmark: {len(report['models_to_test'])}")
    print("\nRun with: python benchmark_model.py")
