"""
System models — intermediate representations for the AI system engineer pipeline.

Pipeline: CanvasGraph → SystemGraph → HardwareAllocation → AssembledFirmware
"""

from typing import Optional
from pydantic import BaseModel, Field


# ─── System Planner Output ───────────────────────────────────

class InferredNode(BaseModel):
    """A logic node auto-inserted by the System Planner."""
    id: str
    name: str
    category: str = "logic"
    inferred_type: str  # "threshold", "formatter", "debounce", "mapper"
    description: str = ""
    reason: str = ""  # Why this node was inferred
    source_node_id: str  # The upstream node that triggered inference
    target_node_id: str  # The downstream node this feeds into
    configuration: dict = Field(default_factory=dict)
    inputs: list[dict] = Field(default_factory=list)
    outputs: list[dict] = Field(default_factory=list)


class SystemEdge(BaseModel):
    """An edge in the system graph — may reference inferred nodes."""
    id: str
    source: str
    source_handle: str
    target: str
    target_handle: str
    data_type: str = "any"
    is_inferred: bool = False  # True if this edge was auto-generated


class SystemGraph(BaseModel):
    """
    Enriched graph produced by the System Planner.
    Contains original nodes + inferred logic nodes + resolved edges.
    """
    original_nodes: list[dict] = Field(default_factory=list)
    inferred_nodes: list[InferredNode] = Field(default_factory=list)
    edges: list[SystemEdge] = Field(default_factory=list)
    execution_order: list[str] = Field(default_factory=list)  # Topologically sorted node IDs
    warnings: list[str] = Field(default_factory=list)
    data_type_errors: list[str] = Field(default_factory=list)


# ─── Resource Manager Output ─────────────────────────────────

class PinAllocation(BaseModel):
    """A single GPIO pin assignment."""
    pin: int
    node_id: str
    function: str  # e.g., "dht22_data", "led_output", "servo_signal"
    mode: str = "digital"  # "digital", "analog", "pwm", "i2c", "spi", "uart"
    direction: str = "input"  # "input", "output", "bidirectional"


class BusAllocation(BaseModel):
    """An I2C or SPI bus assignment."""
    bus_id: int  # 0 or 1
    bus_type: str  # "i2c" or "spi"
    sda_pin: Optional[int] = None
    scl_pin: Optional[int] = None
    mosi_pin: Optional[int] = None
    miso_pin: Optional[int] = None
    sck_pin: Optional[int] = None
    cs_pin: Optional[int] = None
    devices: list[dict] = Field(default_factory=list)  # [{node_id, address}]


class InterruptAllocation(BaseModel):
    """An interrupt assignment."""
    pin: int
    node_id: str
    trigger: str = "RISING"  # "RISING", "FALLING", "CHANGE", "LOW", "HIGH"
    handler: str = ""  # ISR function name


class MemoryEstimate(BaseModel):
    """Estimated memory usage."""
    flash_bytes: int = 0
    sram_bytes: int = 0
    flash_percent: float = 0.0  # Of total flash
    sram_percent: float = 0.0   # Of total SRAM
    breakdown: dict = Field(default_factory=dict)  # {node_id: {flash, sram}}


class HardwareAllocation(BaseModel):
    """
    Complete hardware resource allocation map.
    Produced by the Resource Manager.
    """
    board: str = "esp32dev"
    pins: list[PinAllocation] = Field(default_factory=list)
    buses: list[BusAllocation] = Field(default_factory=list)
    interrupts: list[InterruptAllocation] = Field(default_factory=list)
    memory: MemoryEstimate = Field(default_factory=MemoryEstimate)
    pin_conflicts: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    available_pins: list[int] = Field(default_factory=list)  # Remaining free pins


# ─── Code Assembler Output ───────────────────────────────────

class TaskSchedule(BaseModel):
    """Timing schedule for a block's loop execution."""
    node_id: str
    function_name: str  # e.g., "dht22_sensor_loop"
    interval_ms: int = 100  # How often to execute
    priority: int = 0  # Lower = higher priority
    category: str = "default"  # "sensor", "control", "communication", "output"


class AssembledFirmware(BaseModel):
    """
    Final assembled firmware output.
    Contains all generated file paths and metadata.
    """
    project_id: str
    files: list[str] = Field(default_factory=list)
    main_cpp: str = ""  # Content of the generated main.cpp
    globals_h: str = ""  # Content of globals.h
    config_h: str = ""   # Content of config.h
    platformio_ini: str = ""
    schedule: list[TaskSchedule] = Field(default_factory=list)
    init_order: list[str] = Field(default_factory=list)
    library_deps: list[str] = Field(default_factory=list)
    allocation: Optional[HardwareAllocation] = None
    system_graph: Optional[SystemGraph] = None
