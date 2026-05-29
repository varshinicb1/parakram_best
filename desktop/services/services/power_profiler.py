"""
Power Profiler — Real-time power consumption analysis for embedded systems.

Estimates and tracks power consumption based on:
  - MCU sleep modes and active states
  - Peripheral power draw (WiFi, BLE, sensors, displays)
  - FreeRTOS task scheduling overhead
  - Battery life projections across multiple battery types

This feature goes beyond Embedder by providing actionable optimization suggestions.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PowerState:
    name: str
    current_ma: float
    voltage: float = 3.3
    duty_cycle: float = 1.0  # 0-1, fraction of time in this state
    description: str = ""


@dataclass
class PowerProfile:
    board: str
    states: list[PowerState] = field(default_factory=list)
    avg_current_ma: float = 0
    peak_current_ma: float = 0
    avg_power_mw: float = 0
    battery_estimates: dict = field(default_factory=dict)
    optimization_tips: list[str] = field(default_factory=list)


# ── MCU Power Database ────────────────────────────────────

MCU_POWER = {
    "esp32": {
        "active_wifi": PowerState("Active + WiFi TX", 240, duty_cycle=0.1, description="WiFi transmitting"),
        "active_ble": PowerState("Active + BLE", 130, duty_cycle=0.05, description="BLE advertising"),
        "active_cpu": PowerState("Active (CPU only)", 80, duty_cycle=0.3, description="Processing without radio"),
        "modem_sleep": PowerState("Modem Sleep", 20, duty_cycle=0.4, description="WiFi off, CPU active"),
        "light_sleep": PowerState("Light Sleep", 0.8, duty_cycle=0.1, description="CPU paused, RAM retained"),
        "deep_sleep": PowerState("Deep Sleep", 0.01, duty_cycle=0.05, description="RTC only, RAM lost"),
    },
    "esp32-s3": {
        "active_wifi": PowerState("Active + WiFi TX", 310, duty_cycle=0.1),
        "active_ble": PowerState("Active + BLE", 150, duty_cycle=0.05),
        "active_cpu": PowerState("Active (CPU only)", 100, duty_cycle=0.3),
        "modem_sleep": PowerState("Modem Sleep", 25, duty_cycle=0.4),
        "light_sleep": PowerState("Light Sleep", 0.24, duty_cycle=0.1),
        "deep_sleep": PowerState("Deep Sleep", 0.007, duty_cycle=0.05),
    },
    "stm32f4": {
        "run_168mhz": PowerState("Run 168MHz", 150, duty_cycle=0.3),
        "run_84mhz": PowerState("Run 84MHz", 80, duty_cycle=0.3),
        "sleep": PowerState("Sleep", 2.5, duty_cycle=0.3),
        "stop": PowerState("Stop", 0.4, duty_cycle=0.05),
        "standby": PowerState("Standby", 0.003, duty_cycle=0.05),
    },
    "rp2040": {
        "active_133mhz": PowerState("Active 133MHz", 100, duty_cycle=0.4),
        "active_48mhz": PowerState("Active 48MHz", 36, duty_cycle=0.3),
        "sleep": PowerState("Sleep", 1.3, duty_cycle=0.2),
        "dormant": PowerState("Dormant", 0.18, duty_cycle=0.1),
    },
    "nrf52840": {
        "active_ble": PowerState("Active + BLE", 8.2, duty_cycle=0.1),
        "active_cpu": PowerState("Active (CPU only)", 4.6, duty_cycle=0.3),
        "system_on": PowerState("System ON (idle)", 1.5, duty_cycle=0.4),
        "system_off": PowerState("System OFF", 0.0004, duty_cycle=0.2),
    },
}

PERIPHERAL_POWER = {
    "wifi_tx": 180, "wifi_rx": 100, "ble_adv": 12, "ble_conn": 8,
    "oled_ssd1306": 20, "tft_ili9341": 80, "epaper": 8,
    "bme280": 0.6, "mpu6050": 3.9, "gps_neo6m": 45, "vl53l0x": 19,
    "sd_card_active": 80, "sd_card_idle": 0.2,
    "neopixel_per_led": 60, "servo": 250, "motor_l298n": 2000,
    "lora_tx": 120, "lora_rx": 12, "can_mcp2515": 5,
    "relay": 72, "buzzer": 30,
}

BATTERY_TYPES = {
    "CR2032": {"capacity_mah": 220, "voltage": 3.0, "type": "Coin Cell"},
    "AA_alkaline": {"capacity_mah": 2800, "voltage": 1.5, "type": "AA Alkaline (x2 = 3V)"},
    "18650_LiIon": {"capacity_mah": 3000, "voltage": 3.7, "type": "18650 Li-Ion"},
    "LiPo_500": {"capacity_mah": 500, "voltage": 3.7, "type": "LiPo 500mAh"},
    "LiPo_1000": {"capacity_mah": 1000, "voltage": 3.7, "type": "LiPo 1000mAh"},
    "LiPo_2000": {"capacity_mah": 2000, "voltage": 3.7, "type": "LiPo 2000mAh"},
    "LiPo_5000": {"capacity_mah": 5000, "voltage": 3.7, "type": "LiPo 5000mAh"},
    "USB_powered": {"capacity_mah": 999999, "voltage": 5.0, "type": "USB (unlimited)"},
}


class PowerProfiler:
    """Analyze and optimize power consumption for embedded projects."""

    def profile(self, board: str, peripherals: list[str] = [], duty_cycles: dict = {}) -> dict:
        """Generate a full power profile."""
        board_key = board.lower().replace("-", "").replace("_", "")
        # Find matching MCU
        mcu_states = None
        for key in MCU_POWER:
            if key.replace("-", "").replace("_", "") in board_key or board_key in key.replace("-", "").replace("_", ""):
                mcu_states = MCU_POWER[key]
                break
        if not mcu_states:
            mcu_states = MCU_POWER.get("esp32", {})

        # Apply custom duty cycles
        states = []
        for key, state in mcu_states.items():
            s = PowerState(
                name=state.name,
                current_ma=state.current_ma,
                voltage=state.voltage,
                duty_cycle=duty_cycles.get(key, state.duty_cycle),
                description=state.description,
            )
            states.append(s)

        # Add peripheral power
        peripheral_current = 0
        for p in peripherals:
            p_key = p.lower().replace(" ", "_").replace("-", "_")
            if p_key in PERIPHERAL_POWER:
                peripheral_current += PERIPHERAL_POWER[p_key]

        # Calculate weighted average
        total_duty = sum(s.duty_cycle for s in states)
        if total_duty > 0:
            avg_current = sum(s.current_ma * s.duty_cycle for s in states) / total_duty + peripheral_current
        else:
            avg_current = peripheral_current

        peak_current = max(s.current_ma for s in states) + peripheral_current
        avg_power = avg_current * 3.3

        # Battery estimates
        battery_estimates = {}
        for bat_id, bat in BATTERY_TYPES.items():
            hours = bat["capacity_mah"] / avg_current if avg_current > 0 else float('inf')
            days = hours / 24
            battery_estimates[bat_id] = {
                "type": bat["type"],
                "capacity_mah": bat["capacity_mah"],
                "hours": round(hours, 1),
                "days": round(days, 1),
                "months": round(days / 30, 1),
            }

        # Optimization tips
        tips = self._generate_tips(states, peripherals, avg_current)

        return {
            "board": board,
            "states": [{"name": s.name, "current_ma": s.current_ma, "duty_cycle": s.duty_cycle, "desc": s.description} for s in states],
            "peripherals": peripherals,
            "peripheral_current_ma": peripheral_current,
            "avg_current_ma": round(avg_current, 2),
            "peak_current_ma": round(peak_current, 2),
            "avg_power_mw": round(avg_power, 2),
            "battery_estimates": battery_estimates,
            "optimization_tips": tips,
        }

    def _generate_tips(self, states: list[PowerState], peripherals: list[str], avg_current: float) -> list[str]:
        tips = []

        # Check for deep sleep usage
        has_deep_sleep = any("deep" in s.name.lower() or "standby" in s.name.lower() for s in states)
        if not has_deep_sleep and avg_current > 10:
            tips.append("💡 Enable deep sleep between readings — can reduce average current by 90%+")

        # WiFi power optimization
        if any("wifi" in p.lower() for p in peripherals):
            tips.append("📡 Use WiFi power save mode (WIFI_PS_MIN_MODEM) — reduces idle WiFi power by 50%")
            tips.append("⏰ Batch data and send at intervals instead of real-time — reduces WiFi duty cycle")

        # Display optimization
        if any("oled" in p.lower() or "tft" in p.lower() for p in peripherals):
            tips.append("🖥️ Turn off display after timeout — OLED draws 20-80mA continuously")

        # Sensor optimization
        sensor_count = sum(1 for p in peripherals if any(s in p.lower() for s in ["bme", "mpu", "gps", "vl53"]))
        if sensor_count > 2:
            tips.append("🔬 Power down sensors between readings using GPIO enable pins")

        # GPS optimization
        if any("gps" in p.lower() for p in peripherals):
            tips.append("🛰️ GPS draws 45mA — use backup mode or reduce fix interval to save power")

        # General tips
        if avg_current > 100:
            tips.append("⚡ Consider reducing CPU clock frequency — halving clock can reduce power by 30-40%")
        if avg_current > 50:
            tips.append("🔋 Use a switching regulator instead of LDO — 85%+ efficiency vs 60% for LDO")

        return tips

    def compare_boards(self, boards: list[str], peripherals: list[str] = []) -> dict:
        """Compare power consumption across multiple boards."""
        profiles = {}
        for board in boards:
            profiles[board] = self.profile(board, peripherals)
        return {
            "comparison": profiles,
            "most_efficient": min(profiles, key=lambda b: profiles[b]["avg_current_ma"]),
        }


def get_power_profiler() -> PowerProfiler:
    return PowerProfiler()
