"""
Analysis Routes — MISRA checker, protocol decoder, project planner, datasheet upload.
Consolidated endpoint for all Parakram OS intelligence tools.
"""

from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel
from typing import Optional
import os
import tempfile

router = APIRouter()


# ── Models ─────────────────────────────────────────────────

class CodeAnalysisRequest(BaseModel):
    code: str
    filename: str = "main.cpp"


class SerialAnalysisRequest(BaseModel):
    data: str
    protocol: Optional[str] = None  # auto-detect if None


class PlanRequest(BaseModel):
    prompt: str


# ── MISRA C Checker ────────────────────────────────────────

@router.post("/misra/check")
async def misra_check(req: CodeAnalysisRequest):
    """Run MISRA C:2012 static analysis on firmware code."""
    from agents.misra_checker import get_misra_checker
    checker = get_misra_checker()
    violations = checker.analyze(req.code, req.filename)
    score = checker.get_compliance_score(violations)
    return {"violations": violations, "compliance": score}


# ── Protocol Decoder ───────────────────────────────────────

@router.post("/protocol/decode")
async def decode_protocol(req: SerialAnalysisRequest):
    """Decode serial/protocol data into structured frames."""
    from services.protocol_decoder import get_protocol_analyzer
    analyzer = get_protocol_analyzer()
    frames = analyzer.analyze_bulk(req.data)
    stats = analyzer.get_statistics()
    return {"frames": frames, "statistics": stats}


@router.post("/protocol/i2c-scan")
async def i2c_scan(req: SerialAnalysisRequest):
    """Decode I2C scan output and identify known devices."""
    from services.protocol_decoder import get_protocol_analyzer
    analyzer = get_protocol_analyzer()
    devices = analyzer.i2c_scan(req.data)
    return {"devices": devices, "count": len(devices)}


# ── Project Planner ────────────────────────────────────────

@router.post("/planner/generate")
async def generate_plan(req: PlanRequest):
    """Generate full project plan from natural language description."""
    from services.project_planner import get_project_planner
    planner = get_project_planner()
    plan = planner.plan_from_prompt(req.prompt)
    return {"plan": plan}


# ── Datasheet Parser ───────────────────────────────────────

@router.post("/datasheet/upload")
async def upload_datasheet(file: UploadFile = File(...)):
    """Upload a PDF datasheet and extract hardware knowledge."""
    from agents.datasheet_parser import get_datasheet_parser
    parser = get_datasheet_parser()

    # Save uploaded file temporarily
    suffix = ".pdf" if file.filename and file.filename.endswith(".pdf") else ".pdf"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        knowledge = parser.parse_pdf(tmp_path)
        saved_path = parser.save_knowledge(knowledge)
        context = parser.knowledge_to_context(knowledge)
        return {
            "chip_name": knowledge.chip_name,
            "manufacturer": knowledge.manufacturer,
            "page_count": knowledge.page_count,
            "registers_found": len(knowledge.registers),
            "pins_found": len(knowledge.pins),
            "peripherals": knowledge.peripherals,
            "timing_specs": knowledge.timing_specs,
            "context_preview": context[:2000],
            "saved_to": saved_path,
        }
    finally:
        os.unlink(tmp_path)


@router.get("/datasheet/list")
async def list_datasheets():
    """List all parsed datasheets in storage."""
    from pathlib import Path
    import json
    storage = Path("./storage/datasheets")
    storage.mkdir(parents=True, exist_ok=True)
    datasheets = []
    for f in storage.glob("*_knowledge.json"):
        try:
            data = json.loads(f.read_text())
            datasheets.append({
                "chip_name": data.get("chip_name", ""),
                "manufacturer": data.get("manufacturer", ""),
                "registers": data.get("register_count", 0),
                "pins": data.get("pin_count", 0),
                "file": f.name,
            })
        except Exception:
            pass
    return {"datasheets": datasheets}
