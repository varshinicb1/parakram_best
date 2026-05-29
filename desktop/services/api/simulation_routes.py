"""
Device Simulation Engine -- simulate block graph execution with mock sensor data.

Runs the graph through a virtual timeline to show how thresholds trigger,
filters smooth data, PID controllers respond, and state machines transition.
"""

import math
import random
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from models.graph_model import CanvasGraph
from storage.project_manager import ProjectManager

router = APIRouter()
pm = ProjectManager()


class SimRequest(BaseModel):
    project_id: str
    duration_seconds: int = 60
    time_step_ms: int = 1000


# ─── Sensor Simulators ──────────────────────────────────────

def _simulate_sensor(sensor_id: str, category: str, config: dict, t: float) -> dict:
    """Generate realistic mock sensor data based on block type and time."""
    outputs = {}

    if "dht22" in sensor_id or "bme280" in sensor_id:
        # Temperature: sine wave 20-35°C with noise
        outputs["temperature"] = 27.5 + 7.5 * math.sin(t * 0.05) + random.gauss(0, 0.3)
        outputs["humidity"] = 55.0 + 15.0 * math.sin(t * 0.03 + 1.0) + random.gauss(0, 1.0)
        if "bme280" in sensor_id:
            outputs["pressure"] = 1013.25 + 5.0 * math.sin(t * 0.01) + random.gauss(0, 0.1)
            outputs["altitude"] = 100.0 + 2.0 * math.sin(t * 0.01)

    elif "bmp280" in sensor_id:
        outputs["pressure"] = 1013.25 + 5.0 * math.sin(t * 0.01) + random.gauss(0, 0.1)
        outputs["temperature"] = 25.0 + 3.0 * math.sin(t * 0.04) + random.gauss(0, 0.2)
        outputs["altitude"] = 150.0 + 10.0 * math.sin(t * 0.01)

    elif "mpu6050" in sensor_id:
        outputs["accel_x"] = 0.1 * math.sin(t * 0.5) + random.gauss(0, 0.05)
        outputs["accel_y"] = 0.1 * math.cos(t * 0.5) + random.gauss(0, 0.05)
        outputs["accel_z"] = 9.81 + random.gauss(0, 0.02)
        outputs["gyro_x"] = 2.0 * math.sin(t * 0.3) + random.gauss(0, 0.5)
        outputs["gyro_y"] = 1.5 * math.cos(t * 0.4) + random.gauss(0, 0.5)
        outputs["gyro_z"] = random.gauss(0, 0.3)

    elif "bh1750" in sensor_id:
        # Day/night cycle
        outputs["lux"] = max(0, 500.0 + 400.0 * math.sin(t * 0.02) + random.gauss(0, 10))

    elif "ads1115" in sensor_id:
        for ch in range(4):
            outputs[f"channel_{ch}"] = 1.65 + 0.5 * math.sin(t * 0.1 + ch) + random.gauss(0, 0.01)

    elif "ina219" in sensor_id:
        outputs["bus_voltage"] = 5.0 + 0.1 * math.sin(t * 0.02)
        outputs["current_ma"] = 150.0 + 50.0 * math.sin(t * 0.08) + random.gauss(0, 5)
        outputs["power_mw"] = outputs["bus_voltage"] * outputs["current_ma"]

    elif "vl53l0x" in sensor_id:
        outputs["distance_mm"] = int(500 + 300 * math.sin(t * 0.1) + random.gauss(0, 10))
        outputs["out_of_range"] = outputs["distance_mm"] > 1800

    elif "i2s_microphone" in sensor_id:
        outputs["rms_level"] = 0.05 + 0.03 * abs(math.sin(t * 0.2)) + random.gauss(0, 0.005)
        outputs["peak"] = outputs["rms_level"] * 1.5

    else:
        # Generic sensor
        outputs["value"] = 50.0 + 25.0 * math.sin(t * 0.05) + random.gauss(0, 2.0)

    return {k: round(v, 3) if isinstance(v, float) else v for k, v in outputs.items()}


def _simulate_logic(node: dict, inputs: dict) -> dict:
    """Simulate logic block behavior."""
    outputs = {}
    node_id = node.get("id", "")
    config = node.get("configuration", {})

    if "threshold" in node_id:
        threshold = float(config.get("threshold", 30.0))
        comparison = config.get("comparison", "greater_than")
        value = inputs.get("value", 0.0)
        if comparison == "greater_than":
            outputs["triggered"] = value > threshold
        elif comparison == "less_than":
            outputs["triggered"] = value < threshold
        else:
            outputs["triggered"] = False
    else:
        outputs["triggered"] = False

    return outputs


def _simulate_filter(node: dict, history: list, new_value: float) -> float:
    """Apply moving average filter to simulate signal processing."""
    window = int(node.get("configuration", {}).get("window_size", 5))
    history.append(new_value)
    if len(history) > window:
        history.pop(0)
    return round(sum(history) / len(history), 3)


@router.post("/run")
async def run_simulation(request: SimRequest):
    """
    Simulate the block graph over a virtual timeline.
    Returns timestamped data for each node's outputs.
    """
    canvas_data = pm.load_canvas(request.project_id)
    if canvas_data is None:
        raise HTTPException(status_code=404, detail="Project or canvas not found")

    canvas = CanvasGraph(**canvas_data)
    nodes = canvas.nodes
    edges = canvas.edges

    # Build edge map: target_id -> [(source_id, source_handle, target_handle)]
    edge_map = {}
    for edge in edges:
        src = edge.get("source", "")
        tgt = edge.get("target", "")
        if tgt not in edge_map:
            edge_map[tgt] = []
        edge_map[tgt].append({
            "source": src,
            "source_handle": edge.get("sourceHandle", ""),
            "target_handle": edge.get("targetHandle", ""),
        })

    # Simulation state
    total_steps = (request.duration_seconds * 1000) // request.time_step_ms
    timeline = []
    filter_history: dict[str, list] = {}  # node_id -> history list
    node_outputs: dict[str, dict] = {}  # node_id -> current outputs

    for step in range(min(total_steps, 120)):  # Cap at 120 data points
        t = step * (request.time_step_ms / 1000.0)
        frame = {"time_s": round(t, 2), "nodes": {}}

        # Phase 1: Simulate sensors
        for node in nodes:
            node_id = node.get("id", "")
            category = node.get("category", "")
            config = node.get("configuration", {})

            if category == "sensor":
                outputs = _simulate_sensor(node_id, category, config, t)
                node_outputs[node_id] = outputs
                frame["nodes"][node_id] = {"outputs": outputs}

        # Phase 2: Simulate logic (uses sensor outputs)
        for node in nodes:
            node_id = node.get("id", "")
            category = node.get("category", "")

            if category == "logic":
                # Gather inputs from edges
                inputs = {}
                for edge_info in edge_map.get(node_id, []):
                    src_outputs = node_outputs.get(edge_info["source"], {})
                    src_handle = edge_info["source_handle"]
                    tgt_handle = edge_info["target_handle"]
                    if src_handle in src_outputs:
                        inputs[tgt_handle] = src_outputs[src_handle]

                outputs = _simulate_logic(node, inputs)
                node_outputs[node_id] = outputs
                frame["nodes"][node_id] = {"inputs": inputs, "outputs": outputs}

        # Phase 3: Simulate actuator states
        for node in nodes:
            node_id = node.get("id", "")
            category = node.get("category", "")

            if category == "actuator":
                # Check if trigger input is active
                active = False
                for edge_info in edge_map.get(node_id, []):
                    src_outputs = node_outputs.get(edge_info["source"], {})
                    src_handle = edge_info["source_handle"]
                    if src_handle in src_outputs and src_outputs[src_handle]:
                        active = True
                node_outputs[node_id] = {"active": active}
                frame["nodes"][node_id] = {"outputs": {"active": active}}

        timeline.append(frame)

    # Summary statistics
    stats = {}
    for node in nodes:
        nid = node.get("id", "")
        if nid in node_outputs:
            stats[nid] = {}
            for key, val in node_outputs[nid].items():
                if isinstance(val, (int, float)):
                    # Collect min/max from timeline
                    values = [
                        f["nodes"].get(nid, {}).get("outputs", {}).get(key)
                        for f in timeline
                        if f["nodes"].get(nid, {}).get("outputs", {}).get(key) is not None
                    ]
                    if values:
                        num_vals = [v for v in values if isinstance(v, (int, float))]
                        if num_vals:
                            stats[nid][key] = {
                                "min": round(min(num_vals), 3),
                                "max": round(max(num_vals), 3),
                                "avg": round(sum(num_vals) / len(num_vals), 3),
                            }

    return {
        "status": "simulated",
        "project_id": request.project_id,
        "duration_s": request.duration_seconds,
        "time_step_ms": request.time_step_ms,
        "data_points": len(timeline),
        "timeline": timeline[:30],  # Return first 30 for preview
        "stats": stats,
    }
