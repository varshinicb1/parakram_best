"""
Pipeline routes -- orchestrates the full AI system engineer pipeline.

Canvas Graph -> System Planner -> Logic Synthesizer -> Signal Processor
  -> Resource Manager -> Firmware Generator -> Code Assembler -> Build
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from models.graph_model import CanvasGraph
from services.system_planner import SystemPlanner
from services.logic_synthesizer import LogicSynthesizer
from services.signal_processor import SignalProcessor
from services.resource_manager import ResourceManager
from services.firmware_generator import FirmwareGenerator
from services.code_assembler import CodeAssembler
from services.freertos_assembler import FreeRTOSAssembler
from services.build_service import BuildService
from services.self_healing_compiler import SelfHealingCompiler
from services.firmware_verifier import FirmwareVerifier
from services.lib_resolver import resolve_and_update
from storage.project_manager import ProjectManager
from storage.version_manager import VersionManager

router = APIRouter()
pm = ProjectManager()
vm = VersionManager()
planner = SystemPlanner()
synthesizer = LogicSynthesizer()
signal_proc = SignalProcessor()
resource_mgr = ResourceManager()
firmware_gen = FirmwareGenerator()
assembler = CodeAssembler()
rtos_assembler = FreeRTOSAssembler()
build_svc = BuildService()
healer = SelfHealingCompiler(max_retries=3)
verifier = FirmwareVerifier(max_compile_retries=3)


# ─── Request/Response Models ─────────────────────────────────

class PipelineRequest(BaseModel):
    project_id: str
    board: str = "esp32dev"
    max_retries: int = 3
    skip_compile: bool = False


class PlanRequest(BaseModel):
    project_id: str


class AllocateRequest(BaseModel):
    project_id: str
    board: str = "esp32dev"


class SynthesizeRequest(BaseModel):
    project_id: str


class SignalRequest(BaseModel):
    project_id: str


# ─── Helper ──────────────────────────────────────────────────

def _load_canvas(project_id: str) -> CanvasGraph:
    """Load and parse canvas graph from project storage."""
    canvas_data = pm.load_canvas(project_id)
    if canvas_data is None:
        raise HTTPException(status_code=404, detail="Project or canvas not found")
    return CanvasGraph(**canvas_data)


def _inferred_summary(system_graph):
    """Build a summary of inferred nodes."""
    return [
        {
            "id": n.id,
            "name": n.name,
            "type": n.inferred_type,
            "reason": n.reason,
            "source": n.source_node_id,
            "target": n.target_node_id,
            "configuration": n.configuration,
        }
        for n in system_graph.inferred_nodes
    ]


# ─── Pipeline Endpoints ──────────────────────────────────────

@router.post("/run")
async def run_pipeline(request: PipelineRequest):
    """
    Full pipeline: plan -> synthesize -> signal -> allocate -> generate -> assemble -> compile.
    """
    canvas = _load_canvas(request.project_id)

    project_meta = pm.get_project(request.project_id)
    if not project_meta:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        # Step 1: System Planner -- basic inference
        system_graph = planner.plan(canvas)

        # Step 2: Logic Synthesizer -- AND/OR, hysteresis, PID
        system_graph = synthesizer.synthesize(system_graph)

        # Step 3: Signal Processor -- filters, calibration, unit conversion
        system_graph = signal_proc.process(system_graph)

        # Step 4: Resource Manager -- allocate hardware
        allocation = resource_mgr.allocate(system_graph, board=request.board)

        # Step 5: Firmware Generator -- generate per-block .cpp/.h
        firmware_files = await firmware_gen.generate(request.project_id, canvas)

        # Step 6: Code Assembler -- auto-switch millis() vs FreeRTOS
        import os
        project_dir = os.path.join(
            os.environ.get("PROJECTS_DIR", "../projects"),
            request.project_id,
        )
        use_rtos = rtos_assembler.has_freertos_blocks(system_graph)
        active_assembler = rtos_assembler if use_rtos else assembler
        assembled = active_assembler.assemble(
            project_id=request.project_id,
            system_graph=system_graph,
            allocation=allocation,
            project_dir=project_dir,
        )

        # Step 7: Auto-resolve lib_deps + Compile with self-healing + Wokwi verify
        compile_result = None
        verification_result = None
        if not request.skip_compile:
            # Resolve library dependencies first
            lib_result = await resolve_and_update(project_dir)

            # Compile with self-healing
            compile_result = await healer.compile_with_healing(
                project_dir=project_dir,
                board=request.board,
            )
            if compile_result.get("status") == "success":
                vm.create_snapshot(request.project_id, trigger="pipeline_success")
            elif compile_result.get("attempts", 0) > 1:
                compile_result["self_healed"] = True

            compile_result["lib_deps"] = lib_result.get("lib_deps", [])

        return {
            "status": "success",
            "pipeline": {
                "plan": {
                    "original_nodes": len(system_graph.original_nodes),
                    "inferred_nodes": len(system_graph.inferred_nodes),
                    "edges": len(system_graph.edges),
                    "execution_order": system_graph.execution_order,
                    "warnings": system_graph.warnings,
                    "data_type_errors": system_graph.data_type_errors,
                    "inferred_details": _inferred_summary(system_graph),
                },
                "allocation": {
                    "board": allocation.board,
                    "pins": [p.model_dump() for p in allocation.pins],
                    "buses": [b.model_dump() for b in allocation.buses],
                    "interrupts": [i.model_dump() for i in allocation.interrupts],
                    "memory": allocation.memory.model_dump(),
                    "pin_conflicts": allocation.pin_conflicts,
                    "available_pins": allocation.available_pins,
                    "warnings": allocation.warnings,
                },
                "assembly": {
                    "files": assembled.files,
                    "init_order": assembled.init_order,
                    "schedule": [s.model_dump() for s in assembled.schedule],
                    "library_deps": assembled.library_deps,
                },
                "compile": compile_result,
            },
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {str(e)}")


@router.post("/plan")
async def plan_only(request: PlanRequest):
    """
    System Planner only -- preview inferred nodes without building.
    """
    canvas = _load_canvas(request.project_id)
    system_graph = planner.plan(canvas)

    return {
        "status": "planned",
        "original_nodes": len(system_graph.original_nodes),
        "inferred_nodes": _inferred_summary(system_graph),
        "execution_order": system_graph.execution_order,
        "edges": len(system_graph.edges),
        "warnings": system_graph.warnings,
        "data_type_errors": system_graph.data_type_errors,
    }


@router.post("/synthesize")
async def synthesize_only(request: SynthesizeRequest):
    """
    System Planner + Logic Synthesizer -- preview all inferred control logic.
    Shows combinators, hysteresis upgrades, and PID insertions.
    """
    canvas = _load_canvas(request.project_id)
    system_graph = planner.plan(canvas)
    system_graph = synthesizer.synthesize(system_graph)

    return {
        "status": "synthesized",
        "original_nodes": len(system_graph.original_nodes),
        "inferred_nodes": _inferred_summary(system_graph),
        "execution_order": system_graph.execution_order,
        "edges": len(system_graph.edges),
        "warnings": system_graph.warnings,
    }


@router.post("/signals")
async def signals_only(request: SynthesizeRequest):
    """
    Full preprocessing preview: plan + synthesize + signal processing.
    Shows all auto-inserted filters, calibrators, and converters.
    """
    canvas = _load_canvas(request.project_id)
    system_graph = planner.plan(canvas)
    system_graph = synthesizer.synthesize(system_graph)
    system_graph = signal_proc.process(system_graph)

    return {
        "status": "processed",
        "original_nodes": len(system_graph.original_nodes),
        "inferred_nodes": _inferred_summary(system_graph),
        "execution_order": system_graph.execution_order,
        "edges": len(system_graph.edges),
        "warnings": system_graph.warnings,
    }


@router.post("/allocate")
async def allocate_only(request: AllocateRequest):
    """
    Resource Manager only -- preview hardware allocation without building.
    """
    canvas = _load_canvas(request.project_id)

    # Run full preprocessing pipeline before allocating
    system_graph = planner.plan(canvas)
    system_graph = synthesizer.synthesize(system_graph)
    system_graph = signal_proc.process(system_graph)
    allocation = resource_mgr.allocate(system_graph, board=request.board)

    return {
        "status": "allocated",
        "board": allocation.board,
        "pins": [p.model_dump() for p in allocation.pins],
        "buses": [b.model_dump() for b in allocation.buses],
        "interrupts": [i.model_dump() for i in allocation.interrupts],
        "memory": allocation.memory.model_dump(),
        "pin_conflicts": allocation.pin_conflicts,
        "available_pins": allocation.available_pins,
        "warnings": allocation.warnings,
    }


@router.get("/status/{project_id}")
async def pipeline_status(project_id: str):
    """Get the current pipeline/build status for a project."""
    status = build_svc.get_status(project_id)
    return {"project_id": project_id, "status": status}


class VerifyRequest(BaseModel):
    project_id: str
    board: str = "esp32dev"
    run_simulation: bool = True


@router.post("/verify")
async def verify_firmware(request: VerifyRequest):
    """
    Standalone firmware verification:
    1. Resolve library dependencies
    2. Compile with self-healing
    3. Generate Wokwi diagram
    4. Run Wokwi simulation and check for crashes
    """
    import os
    project_dir = os.path.join(
        os.environ.get("PROJECTS_DIR", "../projects"),
        request.project_id,
    )

    # Load canvas for diagram generation
    try:
        canvas_data = pm.load_canvas(request.project_id)
        nodes = canvas_data.get("nodes", []) if canvas_data else []
        edges = canvas_data.get("edges", []) if canvas_data else []
    except Exception:
        nodes, edges = [], []

    result = await verifier.verify(
        project_dir=project_dir,
        nodes=nodes,
        edges=edges,
        board=request.board,
        run_simulation=request.run_simulation,
    )

    return result.to_dict()
