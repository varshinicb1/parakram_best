"""
Advanced Agent Routes — API endpoints for all Phase 1-7 capabilities.

Provides endpoints for:
- Board registry and selection
- Code review (static analysis)
- Serial output debugging
- Project import from existing Arduino/PlatformIO
- Schematic parsing (KiCad / EasyEDA)
- Compile gate (per-block compile test)
"""

import os
import json
import tempfile
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from typing import Optional

router = APIRouter()


# ─── Board Registry ─────────────────────────────────────

@router.get("/boards")
async def list_boards():
    """List all supported boards with specs."""
    from agents.board_registry import list_boards
    return {"boards": list_boards()}


@router.get("/boards/{board_id}")
async def get_board(board_id: str):
    """Get full profile for a specific board."""
    from agents.board_registry import get_board, get_platformio_ini
    board = get_board(board_id)
    if not board:
        raise HTTPException(404, f"Board '{board_id}' not found")
    return {
        **board,
        "platformio_ini": get_platformio_ini(board_id),
    }


# ─── Code Review ────────────────────────────────────────

class ReviewRequest(BaseModel):
    source: str
    header: str = ""
    board: str = "esp32dev"


@router.post("/review")
async def review_code(request: ReviewRequest):
    """
    Static analysis of firmware code.
    Checks for memory safety, ISR bugs, blocking calls,
    FreeRTOS issues, and hardware conflicts.
    """
    from agents.code_reviewer import CodeReviewer
    reviewer = CodeReviewer()
    issues = reviewer.review(request.source, request.header, request.board)
    return {
        "total_issues": len(issues),
        "errors": sum(1 for i in issues if i.severity == "error"),
        "warnings": sum(1 for i in issues if i.severity == "warning"),
        "info": sum(1 for i in issues if i.severity == "info"),
        "issues": [
            {
                "severity": i.severity,
                "category": i.category,
                "line": i.line,
                "message": i.message,
                "suggestion": i.suggestion,
                "auto_fixable": i.auto_fixable,
            }
            for i in issues
        ],
        "report": reviewer.format_report(issues),
    }


# ─── Serial Debugger ────────────────────────────────────

class SerialDebugRequest(BaseModel):
    serial_output: str
    source_code: str = ""


@router.post("/debug/serial")
async def debug_serial(request: SerialDebugRequest):
    """
    Analyze serial output for crashes, sensor failures,
    connection issues, and resource exhaustion.
    """
    from agents.serial_debugger import SerialDebugger
    debugger = SerialDebugger()
    anomalies = debugger.analyze(request.serial_output)

    result = {
        "total_anomalies": len(anomalies),
        "crashes": sum(1 for a in anomalies if a.severity == "crash"),
        "errors": sum(1 for a in anomalies if a.severity == "error"),
        "warnings": sum(1 for a in anomalies if a.severity == "warning"),
        "anomalies": [
            {
                "severity": a.severity,
                "description": a.description,
                "likely_cause": a.likely_cause,
                "suggested_fix": a.suggested_fix,
                "line_number": a.line_number,
            }
            for a in anomalies
        ],
        "report": debugger.format_report(anomalies),
    }

    # If source code provided, generate fix prompt
    if request.source_code and anomalies:
        result["fix_prompt"] = debugger.build_fix_prompt(
            request.source_code, anomalies
        )

    return result


# ─── Project Import ──────────────────────────────────────

class ImportRequest(BaseModel):
    project_path: str


@router.post("/import")
async def import_project(request: ImportRequest):
    """
    Import an existing Arduino/PlatformIO project.
    Reverse-engineers blocks, libraries, and board from source code.
    """
    from services.project_importer import ProjectImporter

    if not os.path.isdir(request.project_path):
        raise HTTPException(404, f"Directory not found: {request.project_path}")

    importer = ProjectImporter()
    result = importer.import_project(request.project_path)

    if "error" in result:
        raise HTTPException(400, result["error"])

    return result


# ─── Schematic Parser ───────────────────────────────────

class SchematicRequest(BaseModel):
    file_path: str
    format: str = "kicad"  # "kicad" or "easyeda"


@router.post("/schematic/parse")
async def parse_schematic(request: SchematicRequest):
    """
    Parse a schematic file and generate a Parakram block graph.
    Supports KiCad (.kicad_sch) and EasyEDA (JSON).
    """
    from agents.schematic_parser import SchematicParser

    if not os.path.exists(request.file_path):
        raise HTTPException(404, f"Schematic file not found: {request.file_path}")

    parser = SchematicParser()

    if request.format == "kicad":
        result = parser.parse_kicad(request.file_path)
    elif request.format == "easyeda":
        result = parser.parse_easyeda(request.file_path)
    else:
        raise HTTPException(400, f"Unsupported format: {request.format}")

    return result


@router.post("/schematic/validate")
async def validate_hardware(request: SchematicRequest):
    """
    Validate schematic against firmware for electrical correctness.
    Checks I2C pull-ups, voltage levels, pin mismatches.
    """
    from agents.schematic_parser import SchematicParser, HardwareValidator

    if not os.path.exists(request.file_path):
        raise HTTPException(404, f"File not found: {request.file_path}")

    parser = SchematicParser()
    if request.format == "kicad":
        schematic = parser.parse_kicad(request.file_path)
    else:
        schematic = parser.parse_easyeda(request.file_path)

    validator = HardwareValidator()
    issues = validator.validate(schematic, "")

    return {
        "schematic": schematic,
        "validation_issues": issues,
    }


# ─── Compile Gate ────────────────────────────────────────

@router.get("/compile/scoreboard")
async def get_scoreboard():
    """Get the per-block compile success scoreboard."""
    from services.compile_gate import CompileGate
    gate = CompileGate()
    return gate.get_scoreboard()


class CompileTestRequest(BaseModel):
    block_id: str
    header: str
    source: str
    board: str = "esp32dev"


@router.post("/compile/test")
async def test_block_compile(request: CompileTestRequest):
    """
    Isolated compile test for a single block.
    Creates temp PlatformIO project, compiles, auto-heals if needed.
    """
    from services.compile_gate import CompileGate
    gate = CompileGate(board=request.board)
    result = await gate.test_block(
        request.block_id, request.header, request.source
    )
    return result


# ─── Header Parser ──────────────────────────────────────

@router.get("/libraries/scan")
async def scan_libraries():
    """Scan installed ESP32 framework libraries and extract APIs."""
    from agents.header_parser import scan_esp32_framework
    libs = scan_esp32_framework()
    summary = {}
    for name, info in libs.items():
        classes = info.get("classes", [])
        summary[name] = {
            "include": info.get("include", ""),
            "classes": [c["name"] for c in classes],
            "method_count": sum(len(c["methods"]) for c in classes),
            "function_count": len(info.get("functions", [])),
        }
    return {"library_count": len(libs), "libraries": summary}


# ─── NL → Block Graph ───────────────────────────────────

class NLGraphRequest(BaseModel):
    prompt: str
    use_llm: bool = False


@router.post("/nl/graph")
async def nl_to_graph(request: NLGraphRequest):
    """
    Convert natural language to a Parakram block graph.
    Example: "build me a weather station with MQTT"
    """
    from agents.nl_graph_agent import NLGraphAgent
    agent = NLGraphAgent()

    if request.use_llm:
        result = await agent.generate_with_llm(request.prompt)
    else:
        result = agent.build_graph(request.prompt)

    return result


# ─── Prompt → Firmware (end-to-end) ─────────────────────

class BuildRequest(BaseModel):
    prompt: str
    board: str = "esp32dev"
    verify: bool = True


@router.post("/build")
async def build_from_prompt(request: BuildRequest):
    """
    THE KILLER FEATURE.
    Natural language prompt → compiled, verified firmware project.
    Uses LLM for unknown blocks, golden templates for known ones.
    """
    from services.prompt_to_firmware import PromptToFirmware
    pipeline = PromptToFirmware(board=request.board)
    result = await pipeline.build(request.prompt, verify=request.verify)
    return result


# ─── Template-Only Build (100% Deterministic) ──────────

class TemplateBuildRequest(BaseModel):
    block_ids: list[str] = Field(default=[], description="List of golden block IDs to include")
    prompt: str = Field(default="", description="OR natural language prompt (mapped to blocks)")
    board: str = "esp32dev"
    project_name: str = ""


@router.post("/build/template")
async def build_from_template(request: TemplateBuildRequest):
    """
    100% DETERMINISTIC firmware generation.
    Uses ONLY verified golden block templates — zero LLM, zero hallucination.
    MISRA C:2012 compliance guaranteed.
    """
    from services.template_codegen import TemplateCodeGenerator
    gen = TemplateCodeGenerator(board=request.board)

    if request.block_ids:
        result = gen.build_from_blocks(
            request.block_ids,
            project_name=request.project_name or None,
        )
    elif request.prompt:
        result = gen.build_from_prompt(
            request.prompt,
            project_name=request.project_name or None,
        )
    else:
        return {"error": "Provide either block_ids or prompt"}

    return result


@router.post("/build/hybrid")
async def build_hybrid(request: BuildRequest):
    """
    HYBRID BUILD: Template-first for known blocks, LLM fallback for unknowns.
    Best of both worlds — reliability + flexibility.
    """
    from services.prompt_to_firmware import PromptToFirmware
    pipeline = PromptToFirmware(board=request.board)
    result = await pipeline.build(
        request.prompt, verify=request.verify, template_only=False,
    )
    return result


@router.get("/blocks/golden")
async def list_golden_blocks():
    """List all available golden blocks (verified, 100% deterministic)."""
    from services.template_codegen import TemplateCodeGenerator
    gen = TemplateCodeGenerator()
    blocks = gen.get_available_blocks()
    return {
        "total": len(blocks),
        "blocks": blocks,
        "categories": list(set(b["category"] for b in blocks)),
    }


# ─── Runtime Library Search ─────────────────────────────

class LibrarySearchRequest(BaseModel):
    query: str


@router.post("/library/search")
async def search_library(request: LibrarySearchRequest):
    """Search PlatformIO registry for a library and get its API."""
    from services.library_fetcher import search_pio_registry
    results = await search_pio_registry(request.query)
    return {"results": results}


# ─── Calibration API ────────────────────────────────────

class CalibrateRequest(BaseModel):
    sensor_id: str
    raw_value: float
    reference_value: float


@router.post("/calibrate")
async def calibrate_sensor(request: CalibrateRequest):
    """Add a calibration point to a sensor. Returns updated polynomial fit + R² + firmware code."""
    from services.calibration_engine import CalibrationEngine
    engine = CalibrationEngine()
    engine.load_all()
    result = engine.calibrate(request.sensor_id, request.raw_value, request.reference_value)
    return result


@router.get("/calibrate/recipe/{sensor_id}")
async def get_calibration_recipe(sensor_id: str):
    """Get the standard calibration procedure for a sensor (buffer solutions, known weights, etc.)."""
    from services.calibration_engine import CalibrationEngine
    engine = CalibrationEngine()
    recipe = engine.get_calibration_recipe(sensor_id)
    if not recipe:
        return {"error": f"No calibration recipe for '{sensor_id}'", "available": engine.list_calibratable_sensors()}
    return {"sensor_id": sensor_id, "recipe": recipe}


@router.get("/calibrate/sensors")
async def list_calibratable_sensors():
    """List all sensors that have pre-built calibration recipes."""
    from services.calibration_engine import CalibrationEngine
    engine = CalibrationEngine()
    return {"sensors": engine.list_calibratable_sensors()}


# ─── LLM Data Interpretation API ────────────────────────

class InterpretRequest(BaseModel):
    readings: dict
    context: str = ""
    use_llm: bool = False


@router.post("/interpret")
async def interpret_data(request: InterpretRequest):
    """Analyze sensor readings — uses rule-based engine by default, LLM if requested."""
    from services.data_interpreter import DataInterpreter
    llm = None
    if request.use_llm:
        try:
            from agents.llm_router import LLMRouter
            llm = LLMRouter()
        except ImportError:
            pass
    interpreter = DataInterpreter(llm_router=llm)
    result = await interpreter.interpret_readings(request.readings, request.context)
    return result


# ─── BlocklyDuino Import API ────────────────────────────

class BlocklyImportRequest(BaseModel):
    xml: str
    build: bool = False
    board: str = "esp32dev"


@router.post("/blockly/import")
async def import_blockly(request: BlocklyImportRequest):
    """Import BlocklyDuino XML workspace and map to golden blocks. Optionally build firmware."""
    from services.blockly_converter import BlocklyConverter
    converter = BlocklyConverter()
    parsed = converter.parse_xml(request.xml)

    result = {"parsed": parsed}

    if request.build and parsed.get("golden_blocks"):
        from services.template_codegen import TemplateCodeGenerator
        gen = TemplateCodeGenerator(board=request.board)
        build_result = gen.build_from_blocks(parsed["golden_blocks"])
        result["build"] = build_result

    return result


@router.get("/blockly/supported")
async def blockly_supported_types():
    """List all supported BlocklyDuino block types."""
    from services.blockly_converter import BlocklyConverter
    converter = BlocklyConverter()
    return {"supported_types": converter.get_supported_blockly_types()}


# ─── Multi-Board Support ────────────────────────────────

@router.get("/boards")
async def list_boards():
    """List all supported boards (ESP32, STM32, RP2040)."""
    from services.board_profiles import list_boards
    return {"boards": list_boards()}


@router.get("/boards/{board_id}")
async def get_board(board_id: str):
    """Get board profile with pin mapping and PlatformIO config."""
    from services.board_profiles import get_board_profile, generate_platformio_ini
    profile = get_board_profile(board_id)
    if not profile:
        return {"error": f"Unknown board '{board_id}'"}
    return {
        "board": profile,
        "platformio_ini": generate_platformio_ini(board_id),
    }


# ─── Auto-Documentation ─────────────────────────────────

class DocRequest(BaseModel):
    project_name: str
    block_ids: list[str]
    board: str = "esp32dev"


@router.post("/docs/generate")
async def generate_docs(request: DocRequest):
    """Generate README.md documentation for a project."""
    from services.doc_generator import DocGenerator
    from agents.golden_blocks import MASTER_BLOCKS

    # Collect block configs
    all_blocks = {b["id"]: b for cat_blocks in MASTER_BLOCKS.values() for b in cat_blocks}
    blocks = [all_blocks[bid] for bid in request.block_ids if bid in all_blocks]

    gen = DocGenerator()
    readme = gen.generate(request.project_name, blocks, request.board)
    return {"readme": readme, "blocks_found": len(blocks), "blocks_requested": len(request.block_ids)}


# ─── Serial Port Detection & Flash ──────────────────────

@router.get("/flash/devices")
async def list_serial_devices():
    """Scan for connected USB/serial devices with board identification."""
    from services.serial_service import scan_serial_ports
    devices = scan_serial_ports()
    return {"devices": devices, "count": len(devices)}


class FlashRequest(BaseModel):
    port: str
    firmware_path: str = ""
    chip: str = "esp32"


@router.post("/flash/upload")
async def flash_device(request: FlashRequest):
    """Flash firmware to a connected device via esptool."""
    from services.serial_service import flash_firmware
    result = await flash_firmware(request.port, request.firmware_path, request.chip)
    return result


class SerialReadRequest(BaseModel):
    port: str
    baud: int = 115200
    timeout: float = 5.0


@router.post("/serial/read")
async def read_serial_output(request: SerialReadRequest):
    """Read serial output from a device."""
    from services.serial_service import read_serial
    lines = await read_serial(request.port, request.baud, request.timeout)
    return {"lines": lines, "count": len(lines)}


# ─── OTA Updates ─────────────────────────────────────────

class OTARequest(BaseModel):
    device_ip: str
    firmware_path: str
    port: int = 3232


@router.post("/ota/push")
async def push_ota_update(request: OTARequest):
    """Push firmware OTA update to a WiFi-connected device."""
    from services.ota_service import OTAService
    ota = OTAService()
    result = await ota.push_ota(request.device_ip, request.firmware_path, request.port)
    return result


@router.get("/ota/code")
async def get_ota_code():
    """Get the ArduinoOTA setup code to include in firmware."""
    from services.ota_service import OTAService
    ota = OTAService()
    return {"code": ota.generate_ota_firmware_code()}


# ─── Firmware Export ─────────────────────────────────────

class ExportRequest(BaseModel):
    project_name: str
    main_cpp: str
    board: str = "esp32dev"
    lib_deps: list[str] | None = None


@router.post("/firmware/export")
async def export_firmware(request: ExportRequest):
    """Export firmware as a PlatformIO project ZIP."""
    from services.firmware_exporter import FirmwareExporter
    from fastapi.responses import Response

    exporter = FirmwareExporter()
    zip_bytes = exporter.export_project(
        request.project_name,
        request.main_cpp,
        request.board,
        request.lib_deps,
    )
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{request.project_name}.zip"'},
    )


# ─── Wokwi Simulator Deep Integration ───────────────────

class WokwiDiagramRequest(BaseModel):
    block_ids: list[str]
    board: str = "esp32dev"


@router.post("/wokwi/diagram")
async def generate_wokwi_diagram(request: WokwiDiagramRequest):
    """Generate Wokwi diagram.json from golden block IDs."""
    from services.wokwi_simulator import WokwiSimulator
    sim = WokwiSimulator()
    diagram = sim.generate_diagram(request.block_ids, request.board)
    url = sim.get_simulation_url(diagram)
    toml = sim.generate_wokwi_toml(request.board)
    return {"diagram": diagram, "simulation_url": url, "wokwi_toml": toml,
            "parts_count": len(diagram["parts"]), "connections_count": len(diagram["connections"])}


# ─── CI/CD Pipeline ──────────────────────────────────────

class CIPipelineRequest(BaseModel):
    board: str = "esp32dev"
    platform: str = "espressif32"
    run_tests: bool = True
    ota_deploy: bool = False
    device_ip: str = ""


@router.post("/cicd/generate")
async def generate_pipeline(request: CIPipelineRequest):
    """Generate GitHub Actions CI/CD workflow for firmware project."""
    from services.ci_pipeline import CIPipelineGenerator
    gen = CIPipelineGenerator()
    workflow = gen.generate_github_actions(
        request.board, request.platform, request.run_tests, request.ota_deploy, request.device_ip)
    pre_commit = gen.generate_pre_commit_config()
    test_cpp = gen.generate_platformio_test(request.board)
    return {"workflow_yaml": workflow, "pre_commit_yaml": pre_commit,
            "test_template": test_cpp}


# ─── Community Template Gallery ──────────────────────────

@router.get("/gallery/templates")
async def list_gallery_templates(
    category: str = None, difficulty: str = None,
    board: str = None, search: str = None,
):
    """List community project templates with optional filtering."""
    from services.template_gallery import TemplateGallery
    gallery = TemplateGallery()
    templates = gallery.list_templates(category, difficulty, board, search)
    stats = gallery.get_stats()
    return {"templates": templates, "stats": stats}


@router.get("/gallery/templates/{template_id}")
async def get_gallery_template(template_id: str):
    """Get a specific project template by ID."""
    from services.template_gallery import TemplateGallery
    gallery = TemplateGallery()
    template = gallery.get_template(template_id)
    if not template:
        return {"error": f"Template '{template_id}' not found"}
    return {"template": template}


@router.get("/gallery/categories")
async def get_gallery_categories():
    """Get available template categories with counts."""
    from services.template_gallery import TemplateGallery
    gallery = TemplateGallery()
    return {"categories": gallery.get_categories()}
