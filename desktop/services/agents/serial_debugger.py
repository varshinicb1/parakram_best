"""
Serial Debugger — Captures serial output from simulation or real hardware,
identifies anomalies, and auto-generates fixes.

Patterns detected:
- Crash dumps (Guru Meditation, stack traces)
- Sensor failures (NaN, -127, 0 readings)
- Connection failures (WiFi timeout, MQTT disconnect)
- Resource exhaustion (heap low, stack overflow)
- Assertion failures
"""

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SerialAnomaly:
    """A detected anomaly in serial output."""
    severity: str          # "crash", "error", "warning"
    pattern: str           # What triggered the detection
    description: str       # Human-readable description
    likely_cause: str      # Most probable root cause
    suggested_fix: str     # How to fix it
    line_number: int = 0   # Line in serial output


class SerialDebugger:
    """
    Analyzes serial output from firmware execution.
    Detects crashes, sensor failures, and runtime anomalies.
    """

    # ── Crash patterns ──────────────────────────────────
    CRASH_PATTERNS = [
        {
            "regex": r"Guru Meditation Error: Core\s+(\d+) panic'ed \((.+?)\)",
            "severity": "crash",
            "description": "ESP32 kernel panic on core {1}: {2}",
            "cause": "Unhandled exception. Common causes: null pointer, stack overflow, watchdog timeout.",
            "fix": "Check for null pointers, increase task stack size, avoid blocking calls.",
        },
        {
            "regex": r"assert failed:\s*(.+)",
            "severity": "crash",
            "description": "Assertion failed: {1}",
            "cause": "Code invariant violated.",
            "fix": "Check the assertion condition and fix the logic.",
        },
        {
            "regex": r"Stack overflow in task (.+)",
            "severity": "crash",
            "description": "Stack overflow in FreeRTOS task: {1}",
            "cause": "Task stack size too small or deep recursion.",
            "fix": "Increase task stack size (4096+ recommended) or reduce local variables.",
        },
        {
            "regex": r"abort\(\) was called",
            "severity": "crash",
            "description": "Firmware called abort()",
            "cause": "Fatal error condition detected.",
            "fix": "Check error handling and exception catching.",
        },
        {
            "regex": r"LoadProhibited|StoreProhibited",
            "severity": "crash",
            "description": "Memory access violation",
            "cause": "Null pointer dereference or accessing freed memory.",
            "fix": "Check pointer initialization and bounds checking.",
        },
    ]

    # ── Sensor failure patterns ─────────────────────────
    SENSOR_PATTERNS = [
        {
            "regex": r"(?:temperature|temp)\s*[:=]\s*(-127|nan|NaN|inf|-inf|0\.00)",
            "severity": "error",
            "description": "Sensor returning invalid temperature: {0}",
            "cause": "Sensor not connected, wrong pin, or wrong I2C address.",
            "fix": "Check wiring, verify I2C address with I2C scanner, ensure pull-up resistors on SDA/SCL.",
        },
        {
            "regex": r"(?:humidity|hum)\s*[:=]\s*(nan|NaN|0\.00|-1)",
            "severity": "error",
            "description": "Humidity sensor returning invalid value: {1}",
            "cause": "DHT sensor not responding. Minimum 2s between reads.",
            "fix": "Add delay between reads, check data pin wiring, verify DHT type (DHT11 vs DHT22).",
        },
        {
            "regex": r"(?:distance|range)\s*[:=]\s*(8190|65535|0)\s",
            "severity": "warning",
            "description": "Distance sensor out of range or timeout",
            "cause": "VL53L0X returns 8190 on timeout, target too far or too close.",
            "fix": "Check sensor range (30-1200mm for VL53L0X), verify I2C connection.",
        },
        {
            "regex": r"Failed to read|Read failed|Sensor error|Init failed",
            "severity": "error",
            "description": "Sensor init/read failure detected",
            "cause": "Hardware communication error.",
            "fix": "Check wiring, I2C pull-ups (4.7K), power supply, address conflicts.",
        },
    ]

    # ── Connection patterns ─────────────────────────────
    CONNECTION_PATTERNS = [
        {
            "regex": r"WiFi.*(?:failed|timeout|disconnected|FAIL)",
            "severity": "error",
            "description": "WiFi connection failed",
            "cause": "Wrong SSID/password, signal too weak, or router issue.",
            "fix": "Verify credentials, check RSSI, ensure 2.4GHz network (ESP32 doesn't support 5GHz).",
        },
        {
            "regex": r"MQTT.*(?:failed|disconnect|error|refuse)",
            "severity": "error",
            "description": "MQTT broker connection issue",
            "cause": "Broker unreachable, wrong port, or auth failure.",
            "fix": "Verify broker address/port, check credentials, ensure client.loop() is called.",
        },
        {
            "regex": r"E \(\d+\) (?:wifi|esp-tls|HTTP)",
            "severity": "error",
            "description": "ESP-IDF WiFi/TLS error",
            "cause": "Low-level networking error.",
            "fix": "Check ESP-IDF error codes, verify network configuration.",
        },
    ]

    # ── Resource patterns ───────────────────────────────
    RESOURCE_PATTERNS = [
        {
            "regex": r"Free heap:\s*(\d+)",
            "severity": "warning",
            "description": "Heap status: {1} bytes free",
            "cause": "Low heap may cause malloc failures.",
            "fix": "Reduce dynamic allocations, use stack arrays, avoid String concatenation.",
            "threshold_check": lambda m: int(m.group(1)) < 10000,
        },
        {
            "regex": r"Task.*watermark:\s*(\d+)",
            "severity": "warning",
            "description": "Task stack watermark: {1} bytes remaining",
            "cause": "Stack usage approaching limit.",
            "fix": "Increase task stack size or reduce local variable usage.",
            "threshold_check": lambda m: int(m.group(1)) < 512,
        },
    ]

    def analyze(self, serial_output: str) -> list[SerialAnomaly]:
        """Analyze serial output and return detected anomalies."""
        anomalies = []
        lines = serial_output.split("\n")

        all_patterns = (
            self.CRASH_PATTERNS +
            self.SENSOR_PATTERNS +
            self.CONNECTION_PATTERNS +
            self.RESOURCE_PATTERNS
        )

        for line_num, line in enumerate(lines, 1):
            for pattern_def in all_patterns:
                match = re.search(pattern_def["regex"], line, re.IGNORECASE)
                if match:
                    # Check threshold if present
                    threshold_fn = pattern_def.get("threshold_check")
                    if threshold_fn and not threshold_fn(match):
                        continue

                    # Format description with capture groups
                    desc = pattern_def["description"]
                    for i, group in enumerate(match.groups(), 1):
                        desc = desc.replace(f"{{{i}}}", str(group))
                    desc = desc.replace("{0}", match.group(0))

                    anomalies.append(SerialAnomaly(
                        severity=pattern_def["severity"],
                        pattern=pattern_def["regex"][:30],
                        description=desc,
                        likely_cause=pattern_def["cause"],
                        suggested_fix=pattern_def["fix"],
                        line_number=line_num,
                    ))

        # Check for no output at all
        if not serial_output.strip():
            anomalies.append(SerialAnomaly(
                severity="crash",
                pattern="empty_output",
                description="No serial output received",
                likely_cause="Firmware stuck in boot loop, infinite loop before Serial.begin, or crash during setup.",
                suggested_fix="Ensure Serial.begin(115200) is first line in setup(). Check for blocking calls in setup().",
            ))

        # Check for boot loop (repeated reset messages)
        rst_count = len(re.findall(r"rst:0x[0-9a-f]+", serial_output, re.IGNORECASE))
        if rst_count > 2:
            anomalies.append(SerialAnomaly(
                severity="crash",
                pattern="boot_loop",
                description=f"Boot loop detected ({rst_count} resets)",
                likely_cause="Crash during setup() causing continuous reboot.",
                suggested_fix="Check for null pointers, memory corruption, or brownout in setup().",
            ))

        return anomalies

    def build_fix_prompt(self, source: str, anomalies: list[SerialAnomaly]) -> str:
        """Build an LLM prompt to fix issues found in serial output."""
        issues = "\n".join(
            f"- [{a.severity.upper()}] {a.description}\n"
            f"  Cause: {a.likely_cause}\n"
            f"  Fix: {a.suggested_fix}"
            for a in anomalies[:5]
        )

        return f"""The firmware produced these runtime errors (from serial output):

{issues}

Source code:
```cpp
{source}
```

Fix the source code to resolve these issues. Return ONLY the corrected source code.
Key rules:
- Add null pointer checks before dereferencing
- Add timeouts to all while loops
- Ensure Serial.begin() is called before any Serial.print()
- Handle sensor init failures gracefully (retry with backoff)
"""

    def format_report(self, anomalies: list[SerialAnomaly]) -> str:
        """Format anomalies into a readable report."""
        if not anomalies:
            return "Serial output clean — no anomalies detected."

        icons = {"crash": "[CRASH]", "error": "[ERROR]", "warning": "[WARN]"}
        lines = [f"Serial Analysis: {len(anomalies)} anomalies\n"]

        for a in anomalies:
            icon = icons.get(a.severity, "[?]")
            loc = f"L{a.line_number}" if a.line_number else ""
            lines.append(f"  {icon} {loc} {a.description}")
            lines.append(f"       Cause: {a.likely_cause}")
            lines.append(f"       Fix: {a.suggested_fix}")

        return "\n".join(lines)
