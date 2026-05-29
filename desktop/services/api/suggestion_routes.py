"""
AI Suggestions -- analyzes block graphs and suggests improvements.

Uses the multi-LLM provider to provide intelligent recommendations
for safety, performance, security, and best practices.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from models.graph_model import CanvasGraph
from storage.project_manager import ProjectManager

router = APIRouter()
pm = ProjectManager()


class SuggestRequest(BaseModel):
    project_id: str


# ─── Deterministic rules (always run, no LLM needed) ────────

SAFETY_RULES = [
    {
        "id": "no_watchdog",
        "check": lambda nodes, edges: not any(
            "watchdog" in n.get("name", "").lower() or "wdt" in n.get("id", "").lower()
            for n in nodes
        ),
        "severity": "warning",
        "title": "No Watchdog Timer",
        "message": "Your system has no watchdog timer. If firmware hangs, the device won't recover. Add a watchdog timer block.",
        "suggested_block": "watchdog_timer",
    },
    {
        "id": "wifi_no_tls",
        "check": lambda nodes, edges: (
            any(n.get("id", "") in ("wifi_station", "mqtt_client", "http_client") for n in nodes)
            and not any(n.get("id", "") == "tls_config" for n in nodes)
        ),
        "severity": "warning",
        "title": "Network Without TLS",
        "message": "WiFi/MQTT/HTTP blocks detected without TLS configuration. Data is transmitted unencrypted. Add a TLS Config block.",
        "suggested_block": "tls_config",
    },
    {
        "id": "mqtt_no_auth",
        "check": lambda nodes, edges: any(
            n.get("id", "") == "mqtt_client"
            and not n.get("configuration", {}).get("username")
            for n in nodes
        ),
        "severity": "info",
        "title": "MQTT Without Authentication",
        "message": "MQTT client has no username configured. Consider adding MQTT authentication for production deployments.",
    },
    {
        "id": "no_ota",
        "check": lambda nodes, edges: (
            any(n.get("category") == "communication" for n in nodes)
            and not any(n.get("id", "") == "ota_updater" for n in nodes)
        ),
        "severity": "info",
        "title": "No OTA Updates",
        "message": "Network-connected device without OTA update capability. Add an OTA Updater block for remote firmware updates.",
        "suggested_block": "ota_updater",
    },
    {
        "id": "sensor_no_filter",
        "check": lambda nodes, edges: any(
            n.get("category") == "sensor"
            and any(o.get("data_type") == "float" for o in n.get("outputs", []))
            and n.get("configuration", {}).get("no_filter") is not True
            for n in nodes
        ),
        "severity": "tip",
        "title": "Consider Signal Filtering",
        "message": "Analog sensors detected. The pipeline will auto-insert MovingAverage filters, but you can also add LowPassFilter or Calibrator blocks for finer control.",
    },
    {
        "id": "i2c_no_mutex",
        "check": lambda nodes, edges: (
            sum(1 for n in nodes if "i2c_address" in n.get("configuration", {})) > 1
            and not any(n.get("id", "").startswith("rtos_semaphore") for n in nodes)
            and any(n.get("category") == "freertos" for n in nodes)
        ),
        "severity": "warning",
        "title": "Shared I2C Bus Without Mutex",
        "message": "Multiple I2C devices with FreeRTOS tasks but no semaphore. Add a FreeRTOS Semaphore block to protect the I2C bus. (Note: the FreeRTOS assembler handles this automatically.)",
        "suggested_block": "rtos_semaphore",
    },
    {
        "id": "high_memory",
        "check": lambda nodes, edges: (
            any(n.get("category") == "display" for n in nodes)
            and any(n.get("category") == "audio" for n in nodes)
        ),
        "severity": "warning",
        "title": "High Memory Usage Expected",
        "message": "Both display (LVGL) and audio (I2S) blocks detected. Combined SRAM usage may exceed 60%. Consider using PSRAM-equipped ESP32 (ESP32-WROVER).",
    },
    {
        "id": "no_error_handler",
        "check": lambda nodes, edges: not any(
            "error" in n.get("name", "").lower() or "fault" in n.get("name", "").lower()
            for n in nodes
        ),
        "severity": "info",
        "title": "No Error Handler",
        "message": "No error handling block detected. Consider adding error recovery logic for production firmware.",
    },
    {
        "id": "freertos_for_heavy",
        "check": lambda nodes, edges: (
            (any(n.get("category") == "audio" for n in nodes) or
             any(n.get("category") == "display" for n in nodes))
            and not any(n.get("category") == "freertos" for n in nodes)
        ),
        "severity": "tip",
        "title": "Consider FreeRTOS for Heavy Processing",
        "message": "Audio or display blocks detected without FreeRTOS tasks. These are computationally intensive -- using FreeRTOS tasks with core pinning will improve responsiveness. Add a FreeRTOS Task block.",
        "suggested_block": "rtos_task",
    },
]


@router.post("/suggest")
async def suggest(request: SuggestRequest):
    """
    Analyze the project graph and return actionable suggestions.
    Uses deterministic rules (no LLM needed for base suggestions).
    """
    canvas_data = pm.load_canvas(request.project_id)
    if canvas_data is None:
        raise HTTPException(status_code=404, detail="Project or canvas not found")
    canvas = CanvasGraph(**canvas_data)

    nodes = canvas.nodes
    edges = canvas.edges

    suggestions = []
    for rule in SAFETY_RULES:
        try:
            if rule["check"](nodes, edges):
                suggestion = {
                    "id": rule["id"],
                    "severity": rule["severity"],
                    "title": rule["title"],
                    "message": rule["message"],
                }
                if "suggested_block" in rule:
                    suggestion["suggested_block"] = rule["suggested_block"]
                suggestions.append(suggestion)
        except Exception:
            continue  # Skip rules that fail on unexpected graph shapes

    # Try LLM-powered suggestions if provider is available
    llm_suggestions = []
    try:
        from agents.llm_provider import get_provider
        llm = get_provider()
        if llm.is_available():
            # Build a compact graph summary for the LLM
            node_summary = [
                f"{n.get('name', n.get('id', '?'))} ({n.get('category', '?')})"
                for n in nodes
            ]
            prompt = (
                "You are an embedded systems architect reviewing an IoT device design.\n"
                f"The device has these blocks: {', '.join(node_summary)}.\n"
                "Give 1-3 brief, specific improvement suggestions focused on:\n"
                "- Reliability (error recovery, retries)\n"
                "- Power efficiency\n"
                "- Real-time performance\n"
                "Format: one suggestion per line, prefix with [TIP], [WARN], or [INFO].\n"
                "Keep each suggestion under 100 characters."
            )
            response = await llm.generate(prompt, max_tokens=300)
            if response:
                for line in response.strip().split("\n"):
                    line = line.strip()
                    if not line:
                        continue
                    severity = "tip"
                    if line.startswith("[WARN]"):
                        severity = "warning"
                        line = line[6:].strip()
                    elif line.startswith("[INFO]"):
                        severity = "info"
                        line = line[6:].strip()
                    elif line.startswith("[TIP]"):
                        severity = "tip"
                        line = line[5:].strip()
                    llm_suggestions.append({
                        "id": f"ai_{len(llm_suggestions)}",
                        "severity": severity,
                        "title": "AI Suggestion",
                        "message": line,
                        "source": "llm",
                    })
    except Exception:
        pass  # LLM suggestions are optional

    return {
        "status": "analyzed",
        "project_id": request.project_id,
        "rule_suggestions": suggestions,
        "ai_suggestions": llm_suggestions,
        "total": len(suggestions) + len(llm_suggestions),
    }
