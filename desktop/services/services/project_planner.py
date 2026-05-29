"""
Project Planner — AI-powered project architecture generator.

Given a hardware project description, generates:
  - Component list with estimated costs
  - Wiring diagram description
  - PlatformIO project structure
  - FreeRTOS task breakdown (if multi-threaded)
  - Power budget calculation
  - BOM (Bill of Materials)
  - Risk assessment
"""

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Component:
    name: str
    category: str  # mcu, sensor, actuator, display, power, communication, storage
    quantity: int = 1
    estimated_cost_usd: float = 0.0
    interface: str = ""  # I2C, SPI, UART, GPIO, analog
    voltage: str = "3.3V"
    current_ma: float = 0
    datasheet_url: str = ""
    notes: str = ""


@dataclass
class WiringConnection:
    from_component: str
    from_pin: str
    to_component: str
    to_pin: str
    signal_type: str = ""  # power, ground, data, clock, cs, interrupt


@dataclass
class FreeRTOSTask:
    name: str
    priority: int = 1
    stack_size: int = 4096
    description: str = ""
    period_ms: int = 0  # 0 = event-driven


@dataclass
class ProjectPlan:
    title: str
    description: str
    board: str
    components: list[Component] = field(default_factory=list)
    wiring: list[WiringConnection] = field(default_factory=list)
    tasks: list[FreeRTOSTask] = field(default_factory=list)
    total_cost_usd: float = 0
    power_budget_mw: float = 0
    estimated_battery_hours: float = 0
    complexity: str = "medium"  # beginner, medium, advanced, expert
    risks: list[str] = field(default_factory=list)
    required_libraries: list[str] = field(default_factory=list)


# ── Component Database ─────────────────────────────────────

COMPONENT_DB = {
    # MCU boards
    "esp32": Component("ESP32 DevKit V1", "mcu", estimated_cost_usd=5.0, interface="—", voltage="3.3V/5V", current_ma=240),
    "esp32-s3": Component("ESP32-S3 DevKitC", "mcu", estimated_cost_usd=8.0, interface="—", voltage="3.3V/5V", current_ma=310),
    "stm32f4": Component("STM32F446RE Nucleo", "mcu", estimated_cost_usd=15.0, interface="—", voltage="3.3V", current_ma=150),
    "rp2040": Component("Raspberry Pi Pico", "mcu", estimated_cost_usd=4.0, interface="—", voltage="3.3V", current_ma=100),
    "arduino": Component("Arduino Mega 2560", "mcu", estimated_cost_usd=12.0, interface="—", voltage="5V", current_ma=200),

    # Sensors
    "bme280": Component("BME280", "sensor", estimated_cost_usd=3.0, interface="I2C/SPI", voltage="3.3V", current_ma=0.6),
    "mpu6050": Component("MPU6050", "sensor", estimated_cost_usd=2.0, interface="I2C", voltage="3.3V", current_ma=3.9),
    "dht22": Component("DHT22", "sensor", estimated_cost_usd=3.0, interface="GPIO", voltage="3.3-5V", current_ma=1.5),
    "bmp390": Component("BMP390", "sensor", estimated_cost_usd=5.0, interface="I2C/SPI", voltage="3.3V", current_ma=0.7),
    "vl53l0x": Component("VL53L0X ToF", "sensor", estimated_cost_usd=4.0, interface="I2C", voltage="3.3-5V", current_ma=19),
    "ads1115": Component("ADS1115 ADC", "sensor", estimated_cost_usd=5.0, interface="I2C", voltage="3.3-5V", current_ma=0.15),
    "ina219": Component("INA219 Current", "sensor", estimated_cost_usd=3.0, interface="I2C", voltage="3.3-5V", current_ma=1),
    "hx711": Component("HX711 Load Cell", "sensor", estimated_cost_usd=2.0, interface="GPIO", voltage="3.3-5V", current_ma=1.5),
    "max31855": Component("MAX31855 Thermocouple", "sensor", estimated_cost_usd=8.0, interface="SPI", voltage="3.3V", current_ma=1.5),
    "gps": Component("NEO-6M GPS", "sensor", estimated_cost_usd=8.0, interface="UART", voltage="3.3-5V", current_ma=45),
    "ultrasonic": Component("HC-SR04", "sensor", estimated_cost_usd=1.5, interface="GPIO", voltage="5V", current_ma=15),
    "rfid": Component("MFRC522", "sensor", estimated_cost_usd=3.0, interface="SPI", voltage="3.3V", current_ma=13),
    "pir": Component("HC-SR501 PIR", "sensor", estimated_cost_usd=1.0, interface="GPIO", voltage="5V", current_ma=0.065),

    # Displays
    "oled": Component("SSD1306 0.96\" OLED", "display", estimated_cost_usd=4.0, interface="I2C", voltage="3.3-5V", current_ma=20),
    "tft": Component("ILI9341 2.4\" TFT", "display", estimated_cost_usd=6.0, interface="SPI", voltage="3.3V", current_ma=80),
    "lcd": Component("16x2 I2C LCD", "display", estimated_cost_usd=3.0, interface="I2C", voltage="5V", current_ma=25),
    "epaper": Component("2.9\" E-Paper", "display", estimated_cost_usd=12.0, interface="SPI", voltage="3.3V", current_ma=8),

    # Actuators
    "relay": Component("5V Relay Module", "actuator", estimated_cost_usd=1.5, interface="GPIO", voltage="5V", current_ma=72),
    "servo": Component("SG90 Micro Servo", "actuator", estimated_cost_usd=2.0, interface="PWM", voltage="5V", current_ma=250),
    "stepper": Component("28BYJ-48 + ULN2003", "actuator", estimated_cost_usd=3.0, interface="GPIO", voltage="5V", current_ma=240),
    "motor": Component("DC Motor + L298N", "actuator", estimated_cost_usd=5.0, interface="PWM", voltage="5-12V", current_ma=2000),
    "neopixel": Component("WS2812B LED Strip", "actuator", estimated_cost_usd=8.0, interface="GPIO", voltage="5V", current_ma=60),
    "buzzer": Component("Piezo Buzzer", "actuator", estimated_cost_usd=0.5, interface="GPIO", voltage="3.3-5V", current_ma=30),

    # Communication
    "lora": Component("SX1276 LoRa Module", "communication", estimated_cost_usd=10.0, interface="SPI", voltage="3.3V", current_ma=120),
    "ethernet": Component("W5500 Ethernet", "communication", estimated_cost_usd=6.0, interface="SPI", voltage="3.3V", current_ma=132),
    "can": Component("MCP2515 CAN", "communication", estimated_cost_usd=4.0, interface="SPI", voltage="5V", current_ma=5),
    "sd_card": Component("MicroSD Module", "storage", estimated_cost_usd=1.5, interface="SPI", voltage="3.3-5V", current_ma=80),
}


class ProjectPlanner:
    """AI-powered project architecture planner."""

    def plan_from_prompt(self, prompt: str) -> dict:
        """Generate a full project plan from a natural language description."""
        prompt_lower = prompt.lower()
        plan = ProjectPlan(
            title=self._generate_title(prompt),
            description=prompt,
            board=self._detect_board(prompt_lower),
        )

        # Detect required components
        detected = self._detect_components(prompt_lower)
        plan.components = [COMPONENT_DB[plan.board]] + [COMPONENT_DB[c] for c in detected if c in COMPONENT_DB]

        # Calculate costs
        plan.total_cost_usd = sum(c.estimated_cost_usd * c.quantity for c in plan.components)

        # Generate wiring
        plan.wiring = self._generate_wiring(plan.board, detected)

        # Generate FreeRTOS tasks
        plan.tasks = self._generate_tasks(detected, prompt_lower)

        # Power budget
        plan.power_budget_mw = sum(c.current_ma * 3.3 for c in plan.components)

        # Battery estimate (assuming 2000mAh LiPo)
        total_current = sum(c.current_ma for c in plan.components)
        plan.estimated_battery_hours = (2000 / total_current) if total_current > 0 else 0

        # Complexity
        plan.complexity = self._assess_complexity(detected, prompt_lower)

        # Risks
        plan.risks = self._assess_risks(plan)

        # Libraries
        plan.required_libraries = self._resolve_libraries(detected)

        return self._plan_to_dict(plan)

    def _generate_title(self, prompt: str) -> str:
        words = prompt.split()[:6]
        return " ".join(w.capitalize() for w in words)

    def _detect_board(self, prompt: str) -> str:
        if "stm32" in prompt: return "stm32f4"
        if "pico" in prompt or "rp2040" in prompt: return "rp2040"
        if "arduino" in prompt or "mega" in prompt: return "arduino"
        if "esp32-s3" in prompt or "esp32s3" in prompt: return "esp32-s3"
        return "esp32"

    def _detect_components(self, prompt: str) -> list[str]:
        found = []
        keywords = {
            "temperature": "bme280", "humidity": "bme280", "pressure": "bme280", "weather": "bme280",
            "accelerometer": "mpu6050", "gyro": "mpu6050", "imu": "mpu6050", "motion": "mpu6050",
            "oled": "oled", "display": "oled", "screen": "oled",
            "tft": "tft", "lcd": "lcd",
            "relay": "relay", "switch": "relay",
            "servo": "servo", "motor": "motor", "stepper": "stepper",
            "gps": "gps", "location": "gps", "tracking": "gps",
            "neopixel": "neopixel", "led strip": "neopixel", "ws2812": "neopixel", "rgb": "neopixel",
            "lora": "lora", "lorawan": "lora", "long range": "lora",
            "ultrasonic": "ultrasonic", "distance": "ultrasonic", "range": "ultrasonic",
            "rfid": "rfid", "nfc": "rfid", "card reader": "rfid",
            "sd card": "sd_card", "data log": "sd_card", "storage": "sd_card",
            "buzzer": "buzzer", "alarm": "buzzer", "sound": "buzzer",
            "ethernet": "ethernet", "can bus": "can", "can-bus": "can",
            "current": "ina219", "power monitor": "ina219",
            "e-paper": "epaper", "e-ink": "epaper",
            "load cell": "hx711", "weight": "hx711", "scale": "hx711",
            "thermocouple": "max31855",
            "pir": "pir", "motion detect": "pir",
        }
        seen = set()
        for kw, component in keywords.items():
            if kw in prompt and component not in seen:
                found.append(component)
                seen.add(component)
        return found

    def _generate_wiring(self, board: str, components: list[str]) -> list[WiringConnection]:
        """Auto-generate wiring based on board and component interfaces."""
        wiring = []
        esp32_i2c = {"sda": "GPIO21", "scl": "GPIO22"}
        esp32_spi = {"mosi": "GPIO23", "miso": "GPIO19", "sck": "GPIO18", "cs": "GPIO5"}
        gpio_pin = 4  # Start assigning GPIO pins

        for comp_id in components:
            comp = COMPONENT_DB.get(comp_id)
            if not comp:
                continue
            if "I2C" in comp.interface:
                wiring.append(WiringConnection(comp.name, "SDA", board.upper(), esp32_i2c["sda"], "data"))
                wiring.append(WiringConnection(comp.name, "SCL", board.upper(), esp32_i2c["scl"], "clock"))
            elif "SPI" in comp.interface:
                wiring.append(WiringConnection(comp.name, "MOSI", board.upper(), esp32_spi["mosi"], "data"))
                wiring.append(WiringConnection(comp.name, "MISO", board.upper(), esp32_spi["miso"], "data"))
                wiring.append(WiringConnection(comp.name, "SCK", board.upper(), esp32_spi["sck"], "clock"))
                wiring.append(WiringConnection(comp.name, "CS", board.upper(), f"GPIO{gpio_pin}", "cs"))
                gpio_pin += 1
            elif "GPIO" in comp.interface or "PWM" in comp.interface:
                wiring.append(WiringConnection(comp.name, "DATA/SIG", board.upper(), f"GPIO{gpio_pin}", "data"))
                gpio_pin += 1
            elif "UART" in comp.interface:
                wiring.append(WiringConnection(comp.name, "TX", board.upper(), "GPIO16", "data"))
                wiring.append(WiringConnection(comp.name, "RX", board.upper(), "GPIO17", "data"))

            # Always add power
            wiring.append(WiringConnection(comp.name, "VCC", board.upper(), comp.voltage, "power"))
            wiring.append(WiringConnection(comp.name, "GND", board.upper(), "GND", "ground"))

        return wiring

    def _generate_tasks(self, components: list[str], prompt: str) -> list[FreeRTOSTask]:
        tasks = [FreeRTOSTask("SensorRead", priority=2, stack_size=4096, description="Read all sensors periodically", period_ms=1000)]

        if any(c in components for c in ["oled", "tft", "lcd", "epaper"]):
            tasks.append(FreeRTOSTask("DisplayUpdate", priority=1, stack_size=8192, description="Update display", period_ms=500))

        if "wifi" in prompt or "mqtt" in prompt or "web" in prompt:
            tasks.append(FreeRTOSTask("NetworkComm", priority=3, stack_size=8192, description="WiFi/MQTT communication", period_ms=5000))

        if any(c in components for c in ["sd_card"]):
            tasks.append(FreeRTOSTask("DataLogger", priority=1, stack_size=4096, description="Log data to SD card", period_ms=10000))

        if any(c in components for c in ["motor", "servo", "stepper", "relay"]):
            tasks.append(FreeRTOSTask("ActuatorControl", priority=4, stack_size=4096, description="Control actuators", period_ms=100))

        return tasks

    def _assess_complexity(self, components: list[str], prompt: str) -> str:
        score = len(components)
        if "freertos" in prompt or "rtos" in prompt: score += 3
        if "ota" in prompt: score += 2
        if "mqtt" in prompt or "web server" in prompt: score += 2
        if "deep sleep" in prompt: score += 1
        if "can bus" in prompt or "lora" in prompt: score += 2

        if score <= 2: return "beginner"
        if score <= 5: return "medium"
        if score <= 8: return "advanced"
        return "expert"

    def _assess_risks(self, plan: ProjectPlan) -> list[str]:
        risks = []
        if plan.power_budget_mw > 2000:
            risks.append("High power consumption — may need external power supply for battery operation")
        if len(plan.components) > 6:
            risks.append("Many components — ensure all I2C addresses are unique, check SPI CS pin assignments")
        if any(c.interface == "5V" and plan.board in ["esp32", "esp32-s3"] for c in plan.components):
            risks.append("Voltage mismatch — some components need 5V but ESP32 GPIO is 3.3V only (use level shifter)")
        if any(c.category == "communication" for c in plan.components):
            risks.append("RF interference — keep antenna away from high-current traces")
        return risks

    def _resolve_libraries(self, components: list[str]) -> list[str]:
        lib_map = {
            "bme280": "adafruit/Adafruit BME280 Library",
            "mpu6050": "electroniccats/MPU6050",
            "oled": "adafruit/Adafruit SSD1306",
            "tft": "bodmer/TFT_eSPI",
            "neopixel": "adafruit/Adafruit NeoPixel",
            "gps": "mikalhart/TinyGPSPlus",
            "lora": "sandeepmistry/LoRa",
            "rfid": "miguelbalboa/MFRC522",
            "servo": "madhephaestus/ESP32Servo",
            "lcd": "marcoschwartz/LiquidCrystal_I2C",
            "can": "sandeepmistry/CAN",
        }
        return [lib_map[c] for c in components if c in lib_map]

    def _plan_to_dict(self, plan: ProjectPlan) -> dict:
        return {
            "title": plan.title,
            "description": plan.description,
            "board": plan.board,
            "complexity": plan.complexity,
            "total_cost_usd": round(plan.total_cost_usd, 2),
            "power_budget_mw": round(plan.power_budget_mw, 1),
            "estimated_battery_hours": round(plan.estimated_battery_hours, 1),
            "components": [
                {"name": c.name, "category": c.category, "cost": c.estimated_cost_usd,
                 "interface": c.interface, "voltage": c.voltage, "current_ma": c.current_ma}
                for c in plan.components
            ],
            "wiring": [
                {"from": f"{w.from_component}:{w.from_pin}", "to": f"{w.to_component}:{w.to_pin}", "type": w.signal_type}
                for w in plan.wiring
            ],
            "tasks": [
                {"name": t.name, "priority": t.priority, "stack": t.stack_size, "period_ms": t.period_ms, "desc": t.description}
                for t in plan.tasks
            ],
            "libraries": plan.required_libraries,
            "risks": plan.risks,
            "component_count": len(plan.components),
            "estimated_bom": plan.total_cost_usd,
        }


def get_project_planner() -> ProjectPlanner:
    return ProjectPlanner()
