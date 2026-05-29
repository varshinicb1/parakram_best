"""
LLM Data Interpreter — Uses LLM to make sense of sensor data.

Provides:
  1. Anomaly detection and explanation
  2. Sensor data summarization
  3. Predictive alerts
  4. Natural language insight generation
  5. Auto-generated firmware data processing code
"""

import json


class DataInterpreter:
    """LLM-powered sensor data analysis and code generation."""

    def __init__(self, llm_router=None):
        self.llm_router = llm_router

    async def interpret_readings(self, readings: dict, context: str = "") -> dict:
        """Analyze sensor readings and provide insights."""
        prompt = f"""You are an embedded systems data analyst. Analyze these sensor readings and provide:
1. Status summary (normal/warning/critical)
2. Anomalies detected
3. Recommended actions
4. Predicted trends

Sensor Data: {json.dumps(readings, indent=2)}
Context: {context or 'General IoT monitoring'}

Respond in JSON format:
{{
  "status": "normal|warning|critical",
  "summary": "one-line summary",
  "anomalies": ["list of detected anomalies"],
  "actions": ["recommended actions"],
  "trends": ["predicted trends"],
  "insights": ["additional insights"]
}}"""

        if self.llm_router:
            response = await self.llm_router.generate(prompt)
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                return {"status": "unknown", "summary": response, "anomalies": [], "actions": [], "trends": [], "insights": []}

        # Deterministic fallback — no LLM needed
        return self._rule_based_analysis(readings)

    def _rule_based_analysis(self, readings: dict) -> dict:
        """100% deterministic rule-based analysis (no LLM)."""
        anomalies = []
        actions = []
        status = "normal"

        # Known thresholds for common sensors
        THRESHOLDS = {
            "temperature": {"low": -10, "high": 60, "unit": "°C"},
            "humidity": {"low": 10, "high": 95, "unit": "%"},
            "pressure": {"low": 900, "high": 1100, "unit": "hPa"},
            "co2": {"low": 400, "high": 2000, "unit": "ppm"},
            "tvoc": {"low": 0, "high": 500, "unit": "ppb"},
            "pm25": {"low": 0, "high": 35, "unit": "µg/m³"},
            "ph": {"low": 5.5, "high": 8.5, "unit": "pH"},
            "tds": {"low": 0, "high": 500, "unit": "ppm"},
            "ec": {"low": 0, "high": 2000, "unit": "µS/cm"},
            "turbidity": {"low": 0, "high": 5, "unit": "NTU"},
            "voltage": {"low": 3.0, "high": 14.0, "unit": "V"},
            "current": {"low": -10, "high": 10, "unit": "A"},
            "gas": {"low": 0, "high": 300, "unit": "kΩ"},
            "distance": {"low": 2, "high": 4000, "unit": "mm"},
            "lux": {"low": 0, "high": 100000, "unit": "lux"},
        }

        for key, value in readings.items():
            if not isinstance(value, (int, float)):
                continue

            # Find matching threshold
            matched = None
            for tkey, tval in THRESHOLDS.items():
                if tkey in key.lower():
                    matched = tval
                    break

            if matched:
                if value < matched["low"]:
                    anomalies.append(f"{key}={value}{matched['unit']} is below minimum ({matched['low']})")
                    status = "warning"
                    actions.append(f"Check {key} sensor — reading below expected range")
                elif value > matched["high"]:
                    anomalies.append(f"{key}={value}{matched['unit']} exceeds maximum ({matched['high']})")
                    status = "critical" if value > matched["high"] * 1.5 else "warning"
                    actions.append(f"ALERT: {key} is critically high — take immediate action")

            # NaN / infinity check
            if value != value:  # NaN check
                anomalies.append(f"{key} is NaN — sensor disconnected or malfunction")
                actions.append(f"Check {key} wiring and connections")
                status = "critical"

        summary = f"{len(readings)} readings analyzed, {len(anomalies)} anomalies"
        return {
            "status": status,
            "summary": summary,
            "anomalies": anomalies,
            "actions": actions,
            "trends": [],
            "insights": [f"Monitoring {len(readings)} sensor channels"],
        }

    def generate_anomaly_detector_code(self, sensor_configs: list[dict]) -> str:
        """Generate firmware-side anomaly detection C code."""
        lines = [
            "// Auto-generated anomaly detection — deterministic, no LLM at runtime",
            '#include "anomaly_detector.h"',
            '#include <Arduino.h>',
            "",
            "typedef struct {",
            "  const char* name;",
            "  float min_val;",
            "  float max_val;",
            "  float rate_limit;  // max change per second",
            "  float last_val;",
            "  unsigned long last_time;",
            "  bool alert;",
            "} sensor_monitor_t;",
            "",
        ]

        # Generate monitor array
        lines.append(f"#define NUM_MONITORS {len(sensor_configs)}")
        lines.append("static sensor_monitor_t monitors[NUM_MONITORS] = {")
        for cfg in sensor_configs:
            name = cfg.get("id", "unknown")
            lo = cfg.get("min", -999)
            hi = cfg.get("max", 999)
            rate = cfg.get("rate_limit", 100)
            lines.append(f'  {{"{name}", {lo}f, {hi}f, {rate}f, 0, 0, false}},')
        lines.append("};")
        lines.append("")

        # Generate check function
        lines.extend([
            "bool anomaly_check(uint8_t idx, float value) {",
            "  if (idx >= NUM_MONITORS) return false;",
            "  sensor_monitor_t* m = &monitors[idx];",
            "  bool anomaly = false;",
            "",
            "  // Range check",
            "  if (value < m->min_val || value > m->max_val) {",
            '    Serial.printf("[ANOMALY] %s=%.2f out of range [%.1f, %.1f]\\n",',
            "      m->name, value, m->min_val, m->max_val);",
            "    anomaly = true;",
            "  }",
            "",
            "  // Rate-of-change check",
            "  unsigned long now = millis();",
            "  if (m->last_time > 0) {",
            "    float dt = (now - m->last_time) / 1000.0f;",
            "    if (dt > 0) {",
            "      float rate = abs(value - m->last_val) / dt;",
            "      if (rate > m->rate_limit) {",
            '        Serial.printf("[ANOMALY] %s rate=%.1f/s exceeds limit %.1f\\n",',
            "          m->name, rate, m->rate_limit);",
            "        anomaly = true;",
            "      }",
            "    }",
            "  }",
            "",
            "  // NaN check",
            "  if (value != value) {",
            '    Serial.printf("[ANOMALY] %s is NaN!\\n", m->name);',
            "    anomaly = true;",
            "  }",
            "",
            "  m->last_val = value;",
            "  m->last_time = now;",
            "  m->alert = anomaly;",
            "  return anomaly;",
            "}",
            "",
            "bool anomaly_any_alert() {",
            "  for (int i = 0; i < NUM_MONITORS; i++) {",
            "    if (monitors[i].alert) return true;",
            "  }",
            "  return false;",
            "}",
        ])

        return "\n".join(lines)

    def generate_data_pipeline_code(self, sensors: list[str], output: str = "serial") -> str:
        """Generate firmware code that reads, filters, calibrates, and outputs data."""
        lines = [
            "// Auto-generated data pipeline",
            '#include <Arduino.h>',
            '#include "calibrator.h"',
            '#include "anomaly_detector.h"',
            "",
        ]

        # Include all sensor headers
        for s in sensors:
            lines.append(f'#include "{s}.h"')

        lines.extend(["", "void data_pipeline_setup() {"])
        for s in sensors:
            lines.append(f"  {s}_setup();")
        lines.append('  Serial.println("[pipeline] OK");')
        lines.append("}")
        lines.append("")

        lines.append("void data_pipeline_loop() {")
        lines.append("  static unsigned long last = 0;")
        lines.append("  if (millis() - last < 1000) return;")
        lines.append("  last = millis();")
        lines.append("")

        for i, s in enumerate(sensors):
            lines.append(f"  {s}_loop();")

        if output == "json":
            lines.append('  Serial.print("{");')
            for i, s in enumerate(sensors):
                sep = ',' if i < len(sensors) - 1 else ''
                lines.append(f'  Serial.printf("\\"{s}\\": {{}}%s", {s}_get_value(){sep});')
            lines.append('  Serial.println("}");')
        else:
            for s in sensors:
                lines.append(f'  Serial.printf("[{s}] reading done\\n");')

        lines.append("}")

        return "\n".join(lines)
