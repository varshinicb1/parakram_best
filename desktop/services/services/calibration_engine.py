"""
Universal Calibration Engine — Multi-point calibration for analog sensors.

Provides:
  1. Backend CalibrationEngine for managing calibration data
  2. Firmware-side calibration golden block (stored in NVS)
  3. Auto-calibration workflow via API

Supports: pH, TDS, turbidity, EC, thermistor, load cell, pressure,
          gas sensors, and any custom analog-to-value mapping.
"""

import json
import os
import numpy as np

CALIBRATION_DIR = os.path.join(os.path.dirname(__file__), "..", "calibration_data")


class CalibrationProfile:
    """Single sensor calibration profile with multi-point polynomial fit."""

    def __init__(self, sensor_id: str, unit: str = ""):
        self.sensor_id = sensor_id
        self.unit = unit
        self.points: list[dict] = []  # [{"raw": 1234, "reference": 7.0}, ...]
        self.coefficients: list[float] = []  # polynomial coefficients
        self.degree: int = 1  # linear by default
        self.r_squared: float = 0.0

    def add_point(self, raw_value: float, reference_value: float):
        """Add a calibration point (raw ADC reading → known reference value)."""
        self.points.append({"raw": raw_value, "reference": reference_value})
        if len(self.points) >= 2:
            self._fit()

    def _fit(self):
        """Fit polynomial to calibration points."""
        raws = [p["raw"] for p in self.points]
        refs = [p["reference"] for p in self.points]

        # Auto-select degree: linear(2pts), quadratic(3+), cubic(5+)
        n = len(self.points)
        self.degree = min(3, max(1, n - 1))

        coeffs = list(reversed(list(map(float, list(
            __import__("numpy").polyfit(raws, refs, self.degree)
        )))))
        self.coefficients = coeffs

        # Calculate R²
        predicted = [self.apply(r) for r in raws]
        ss_res = sum((r - p) ** 2 for r, p in zip(refs, predicted))
        mean_ref = sum(refs) / len(refs)
        ss_tot = sum((r - mean_ref) ** 2 for r in refs)
        self.r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 1.0

    def apply(self, raw_value: float) -> float:
        """Apply calibration to raw ADC value → calibrated value."""
        if not self.coefficients:
            return raw_value
        result = 0.0
        for i, c in enumerate(self.coefficients):
            result += c * (raw_value ** i)
        return result

    def generate_firmware_constants(self) -> str:
        """Generate C constants for firmware-side calibration."""
        if not self.coefficients:
            return "// No calibration data"

        lines = [f"// Calibration for {self.sensor_id} — R²={self.r_squared:.6f}"]
        lines.append(f"#define CAL_{self.sensor_id.upper()}_DEGREE {self.degree}")
        for i, c in enumerate(self.coefficients):
            lines.append(f"#define CAL_{self.sensor_id.upper()}_C{i} {c:.10f}f")
        lines.append(f"static const float cal_{self.sensor_id}_coeffs[] = {{")
        lines.append("  " + ", ".join(f"{c:.10f}f" for c in self.coefficients))
        lines.append("};")

        # Generate apply function
        lines.append(f"static float cal_{self.sensor_id}_apply(float raw) {{")
        lines.append("  float result = 0.0f;")
        lines.append("  float power = 1.0f;")
        lines.append(f"  for (int i = 0; i <= {self.degree}; i++) {{")
        lines.append(f"    result += cal_{self.sensor_id}_coeffs[i] * power;")
        lines.append("    power *= raw;")
        lines.append("  }")
        lines.append("  return result;")
        lines.append("}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "sensor_id": self.sensor_id,
            "unit": self.unit,
            "points": self.points,
            "coefficients": self.coefficients,
            "degree": self.degree,
            "r_squared": self.r_squared,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CalibrationProfile":
        p = cls(data["sensor_id"], data.get("unit", ""))
        p.points = data.get("points", [])
        p.coefficients = data.get("coefficients", [])
        p.degree = data.get("degree", 1)
        p.r_squared = data.get("r_squared", 0.0)
        return p


class CalibrationEngine:
    """Manages calibration profiles for all sensors in a project."""

    def __init__(self):
        self.profiles: dict[str, CalibrationProfile] = {}
        os.makedirs(CALIBRATION_DIR, exist_ok=True)

    def create_profile(self, sensor_id: str, unit: str = "") -> CalibrationProfile:
        p = CalibrationProfile(sensor_id, unit)
        self.profiles[sensor_id] = p
        return p

    def calibrate(self, sensor_id: str, raw: float, reference: float) -> dict:
        """Add calibration point and return updated profile."""
        if sensor_id not in self.profiles:
            self.create_profile(sensor_id)
        p = self.profiles[sensor_id]
        p.add_point(raw, reference)
        self._save(sensor_id)
        return {
            "sensor_id": sensor_id,
            "points": len(p.points),
            "degree": p.degree,
            "r_squared": p.r_squared,
            "coefficients": p.coefficients,
            "firmware_code": p.generate_firmware_constants(),
        }

    def get_calibrated_value(self, sensor_id: str, raw: float) -> float:
        if sensor_id in self.profiles:
            return self.profiles[sensor_id].apply(raw)
        return raw

    def get_firmware_calibration(self, sensor_ids: list[str]) -> str:
        """Generate C code for all requested sensors' calibration data."""
        lines = ["// Auto-generated calibration constants", "#pragma once", ""]
        for sid in sensor_ids:
            if sid in self.profiles:
                lines.append(self.profiles[sid].generate_firmware_constants())
                lines.append("")
        return "\n".join(lines)

    def _save(self, sensor_id: str):
        path = os.path.join(CALIBRATION_DIR, f"{sensor_id}.json")
        with open(path, "w") as f:
            json.dump(self.profiles[sensor_id].to_dict(), f, indent=2)

    def load_all(self):
        for fname in os.listdir(CALIBRATION_DIR):
            if fname.endswith(".json"):
                with open(os.path.join(CALIBRATION_DIR, fname)) as f:
                    data = json.load(f)
                    self.profiles[data["sensor_id"]] = CalibrationProfile.from_dict(data)

    # ── Pre-built calibration recipes ──
    KNOWN_CALIBRATIONS = {
        "ph_sensor": {
            "unit": "pH",
            "standard_points": [
                {"label": "pH 4.0 buffer", "reference": 4.01},
                {"label": "pH 7.0 buffer", "reference": 7.01},
                {"label": "pH 10.0 buffer", "reference": 10.01},
            ],
        },
        "tds_meter": {
            "unit": "ppm",
            "standard_points": [
                {"label": "Distilled water", "reference": 0},
                {"label": "342 ppm standard", "reference": 342},
                {"label": "1413 ppm standard", "reference": 1413},
            ],
        },
        "ec_sensor": {
            "unit": "µS/cm",
            "standard_points": [
                {"label": "Distilled water", "reference": 0},
                {"label": "1413 µS/cm standard", "reference": 1413},
                {"label": "12880 µS/cm standard", "reference": 12880},
            ],
        },
        "turbidity": {
            "unit": "NTU",
            "standard_points": [
                {"label": "Clear water", "reference": 0},
                {"label": "100 NTU standard", "reference": 100},
                {"label": "1000 NTU standard", "reference": 1000},
            ],
        },
        "load_cell_hx710": {
            "unit": "g",
            "standard_points": [
                {"label": "No load (tare)", "reference": 0},
                {"label": "100g weight", "reference": 100},
                {"label": "500g weight", "reference": 500},
            ],
        },
        "hx711": {
            "unit": "g",
            "standard_points": [
                {"label": "No load (tare)", "reference": 0},
                {"label": "Known weight 1", "reference": 100},
                {"label": "Known weight 2", "reference": 500},
            ],
        },
        "thermistor": {
            "unit": "°C",
            "standard_points": [
                {"label": "Ice water", "reference": 0.0},
                {"label": "Room temp", "reference": 25.0},
                {"label": "Boiling water", "reference": 100.0},
            ],
        },
        "mq_gas_sensor": {
            "unit": "ppm",
            "standard_points": [
                {"label": "Fresh air", "reference": 0},
                {"label": "Known gas concentration 1", "reference": 200},
            ],
        },
        "current_acs712": {
            "unit": "A",
            "standard_points": [
                {"label": "No current", "reference": 0.0},
                {"label": "Known current 1A", "reference": 1.0},
                {"label": "Known current 5A", "reference": 5.0},
            ],
        },
        "voltage_divider": {
            "unit": "V",
            "standard_points": [
                {"label": "0V reference", "reference": 0.0},
                {"label": "Known voltage", "reference": 12.0},
            ],
        },
    }

    def get_calibration_recipe(self, sensor_id: str) -> dict | None:
        return self.KNOWN_CALIBRATIONS.get(sensor_id)

    def list_calibratable_sensors(self) -> list[str]:
        return list(self.KNOWN_CALIBRATIONS.keys())
